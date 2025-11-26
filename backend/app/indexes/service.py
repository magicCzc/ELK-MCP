"""
Copyright (c) 2025, elk-MCP Project.
All rights reserved.
"""

from typing import Dict, List, Optional, Set
import threading
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx

from ..config import settings
from ..es.client import ESHttpClient


logger = logging.getLogger("index_discovery")


class IndexDiscoveryService:
    """Index auto-discovery with in-memory cache and periodic refresh.

    - Connects to configured ES hosts with connection pooling.
    - Periodically fetches latest indices via `/_cat/indices`.
    - Caches valid indices in memory and supports hot updates.
    - Fault-tolerant: skips unavailable hosts and logs warnings.
    """

    def __init__(self) -> None:
        self._clients: List[ESHttpClient] = [ESHttpClient(h) for h in settings.ES_HOSTS]
        self._interval_seconds: int = getattr(settings, "INDEX_DISCOVERY_INTERVAL_SECONDS", 60)
        self._include_patterns: List[str] = getattr(
            settings,
            "INDEX_INCLUDE_PATTERNS",
            [r"^kst-logs-[A-Za-z0-9_-].*"],
        )
        self._exclude_patterns: List[str] = getattr(settings, "INDEX_EXCLUDE_PATTERNS", [])
        self._enabled: bool = getattr(settings, "INDEX_DISCOVERY_ENABLED", True)

        self._cache: Set[str] = set()
        self._last_refresh_ts: Optional[float] = None
        self._last_added_count: int = 0
        self._last_removed_count: int = 0
        self._stop_evt = threading.Event()
        self._thread: Optional[threading.Thread] = None

    # Public API
    def get_indices(self) -> List[str]:
        return sorted(self._cache)

    def get_status(self) -> Dict[str, Optional[float]]:
        return {"last_refresh_ts": self._last_refresh_ts, "enabled": self._enabled}

    def update_config(
        self,
        *,
        enabled: Optional[bool] = None,
        interval_seconds: Optional[int] = None,
        include_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
    ) -> None:
        if enabled is not None:
            self._enabled = bool(enabled)
        if interval_seconds is not None and interval_seconds > 0:
            self._interval_seconds = int(interval_seconds)
        if include_patterns is not None:
            self._include_patterns = list(include_patterns)
        if exclude_patterns is not None:
            self._exclude_patterns = list(exclude_patterns)
        logger.info("index.discovery.config.updated")

    # Lifecycle hooks
    def startup(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_evt.clear()
        self._thread = threading.Thread(target=self._run_loop, name="IndexDiscovery", daemon=True)
        self._thread.start()
        logger.info("index.discovery.started")

    def shutdown(self) -> None:
        self._stop_evt.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        logger.info("index.discovery.stopped")

    # Core logic
    def _run_loop(self) -> None:
        while not self._stop_evt.is_set():
            if self._enabled:
                try:
                    self.refresh_once()
                except Exception:
                    logger.exception("index.discovery.refresh.error")
            # Sleep in short steps to allow quick shutdown
            remaining = self._interval_seconds
            while remaining > 0 and not self._stop_evt.is_set():
                time.sleep(min(1.0, remaining))
                remaining -= 1

    def refresh_once(self) -> None:
        """Fetch indices from all hosts concurrently and update cache."""
        discovered: Set[str] = set()

        def fetch_indices(client: ESHttpClient) -> List[str]:
            # Use cat indices with minimal fields for speed
            url = f"{client._base_url}/_cat/indices?h=index&s=index&format=json"
            try:
                resp = client.client().get(url, timeout=5.0)
                resp.raise_for_status()
                data = resp.json()
                return [row.get("index", "") for row in data if row.get("index")]
            except httpx.HTTPError:
                logger.warning("index.discovery.host.unavailable", extra={"host": client._base_url})
                return []

        with ThreadPoolExecutor(max_workers=len(self._clients) or 1) as pool:
            futures = {pool.submit(fetch_indices, c): c for c in self._clients}
            for fut in as_completed(futures):
                for name in fut.result():
                    if self._is_valid(name):
                        discovered.add(name)

        # incremental diff
        prev = set(self._cache)
        added = discovered - prev
        removed = prev - discovered
        self._cache = discovered
        self._last_refresh_ts = time.time()
        self._last_added_count = len(added)
        self._last_removed_count = len(removed)
        # metrics
        try:
            from ..metrics.metrics import INDEX_REFRESH_TOTAL, INDEX_COUNT_GAUGE

            INDEX_REFRESH_TOTAL.inc()
            INDEX_COUNT_GAUGE.set(len(discovered))
        except Exception:
            pass
        logger.info(
            "index.discovery.refresh.ok",
            extra={
                "count": len(discovered),
                "added": self._last_added_count,
                "removed": self._last_removed_count,
            },
        )

    # Validation
    def _is_valid(self, name: str) -> bool:
        import re

        if not name:
            return False
        for p in self._exclude_patterns:
            if re.search(p, name):
                return False
        if not self._include_patterns:
            return True
        return any(re.search(p, name) for p in self._include_patterns)

    # Matching
    def find_indices(self, *, keyword: str, use_regex: bool = False, fuzzy: bool = True) -> List[str]:
        """Return indices whose names match keyword.

        - regex: treat keyword as regular expression (case-insensitive).
        - fuzzy: when no match, fallback to case-insensitive containment.
        """
        if not keyword:
            return sorted(self._cache)
        candidates = sorted(self._cache)
        matches: List[str] = []
        if use_regex:
            import re

            pat = re.compile(keyword, re.IGNORECASE)
            matches = [idx for idx in candidates if pat.search(idx)]
        else:
            k = keyword.lower()
            matches = [idx for idx in candidates if k in idx.lower()]
        if not matches and fuzzy and not use_regex:
            # Fallback: split by non-alnum and try parts
            import re

            parts = [p for p in re.split(r"[^A-Za-z0-9]+", keyword) if p]
            for idx in candidates:
                low = idx.lower()
                if any(p.lower() in low for p in parts):
                    matches.append(idx)
        # Optional: update a match ratio gauge if available
        try:
            from ..metrics.metrics import INDEX_MATCH_RATIO

            total = len(candidates) or 1
            INDEX_MATCH_RATIO.set(len(matches) / total)
        except Exception:
            pass
        logger.info("index.discovery.match", extra={"keyword": keyword, "matches": len(matches)})
        return matches


# Singleton service
index_discovery = IndexDiscoveryService()
