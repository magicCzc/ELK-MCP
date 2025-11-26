"""
Copyright (c) 2025, elk-MCP Project.
All rights reserved.
"""

from typing import Any, Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import httpx

from ..config import settings


class ESHttpClient:
    """Version-adaptive HTTP client for Elasticsearch 6.5.4 and above.

    - Detects server version on first use (GET /) and adapts paths.
    - Supports doc_type for 6.x and omits for 7.x/8.x.
    - Uses keep-alive connection pooling, small timeout for performance.
    """

    def __init__(self, base_url: Optional[str] = None) -> None:
        self._client: Optional[httpx.Client] = None
        self._version_major: Optional[int] = None
        self._base_url: str = (base_url or settings.ES_HOSTS[0]).rstrip("/")

    def client(self) -> httpx.Client:
        if self._client is None:
            auth: Optional[Tuple[str, str]] = None
            if settings.ES_USERNAME and settings.ES_PASSWORD:
                auth = httpx.BasicAuth(settings.ES_USERNAME, settings.ES_PASSWORD)
            self._client = httpx.Client(
                timeout=5.0,
                auth=auth,
                verify=settings.ES_VERIFY_SSL,
                headers={"Content-Type": "application/json"},
            )
        return self._client

    def _detect_version(self) -> int:
        if self._version_major is not None:
            return self._version_major
        try:
            resp = self.client().get(f"{self._base_url}/")
            resp.raise_for_status()
            info = resp.json()
            ver = info.get("version", {}).get("number", "6.5.4")
            major = int(ver.split(".")[0])
        except Exception:
            # Be tolerant: default to ES 6.x behavior if detection fails
            major = 6
        self._version_major = major
        return major

    def _search_path(self, index: List[str], doc_type: Optional[str]) -> str:
        idx = ",".join(index)
        major = self._detect_version()
        if major <= 6 and doc_type:
            return f"{self._base_url}/{idx}/{doc_type}/_search"
        return f"{self._base_url}/{idx}/_search"

    def _get_path(self, index: str, doc_id: str, doc_type: Optional[str]) -> str:
        major = self._detect_version()
        if major <= 6 and doc_type:
            return f"{self._base_url}/{index}/{doc_type}/{doc_id}"
        return f"{self._base_url}/{index}/_doc/{doc_id}"

    def _index_path(self, index: str, doc_type: Optional[str]) -> str:
        major = self._detect_version()
        if major <= 6 and doc_type:
            return f"{self._base_url}/{index}/{doc_type}"
        return f"{self._base_url}/{index}/_doc"

    def search_logs(
        self,
        index: List[str],
        body: Dict[str, Any],
        doc_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        path = self._search_path(index, doc_type)
        # 调试输出：打印实际请求的 ES 路径与主机
        from ..config import settings as _settings  # 局部导入避免循环
        if bool(getattr(_settings, "DEBUG_QUERY_LOGS", False)):
            try:
                print("[DEBUG][es] post path =", path)
                print("[DEBUG][es] target host =", self._base_url)
                print("[DEBUG][es] body.query =", str(body.get("query"))[:800])
            except Exception:
                pass
        try:
            resp = self.client().post(path, json=body)
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            if bool(getattr(_settings, "DEBUG_QUERY_LOGS", False)):
                try:
                    print(
                        "[ERROR][es] status =",
                        e.response.status_code,
                        "text =",
                        (e.response.text or "")[:200],
                    )
                except Exception:
                    pass
            raise
        return resp.json()

    def get_doc(
        self,
        index: str,
        doc_id: str,
        doc_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        path = self._get_path(index, doc_id, doc_type)
        resp = self.client().get(path)
        resp.raise_for_status()
        return resp.json()

    def index_audit(self, index: str, doc: Dict[str, Any], doc_type: Optional[str]) -> None:
        path = self._index_path(index, doc_type)
        resp = self.client().post(path, json=doc)
        resp.raise_for_status()


def _extract_total(res: Dict[str, Any]) -> int:
    total_raw = res.get("hits", {}).get("total")
    if isinstance(total_raw, dict):
        return int(total_raw.get("value", 0))
    if isinstance(total_raw, int):
        return total_raw
    return 0


class MultiESClient:
    """Fan-out queries to multiple ES clusters and merge results.

    - Executes searches concurrently for performance.
    - Adapts doc_type per-cluster via ESHttpClient.
    - Merges totals and sorts hits by configured timestamp field.
    """

    def __init__(self) -> None:
        self.clients: List[ESHttpClient] = [ESHttpClient(h) for h in settings.ES_HOSTS]

    def search_logs_all(
        self,
        index: List[str],
        body: Dict[str, Any],
        doc_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        results: List[Dict[str, Any]] = []
        # 调试输出：并发请求的所有目标主机
        from ..config import settings as _settings
        if bool(getattr(_settings, "DEBUG_QUERY_LOGS", False)):
            try:
                print("[DEBUG][es] fan-out to hosts =", [c._base_url for c in self.clients])
                print("[DEBUG][es] indices =", index)
            except Exception:
                pass
        # Run requests concurrently; limit workers to number of clusters.
        with ThreadPoolExecutor(max_workers=len(self.clients)) as pool:
            futures = {
                pool.submit(c.search_logs, index=index, body=body, doc_type=doc_type): c
                for c in self.clients
            }
            for fut in as_completed(futures):
                try:
                    results.append(fut.result())
                except Exception as e:
                    if bool(getattr(_settings, "DEBUG_QUERY_LOGS", False)):
                        try:
                            client = futures.get(fut)
                            host = getattr(client, "_base_url", "?")
                            print("[WARN][es] cluster failed =", host, "err =", repr(e))
                        except Exception:
                            pass
                    # Skip failed clusters to be resilient during outages
                    pass
        # Merge totals
        total = sum(_extract_total(r) for r in results)
        # Merge hits and sort by timestamp
        all_hits: List[Dict[str, Any]] = []
        for r in results:
            all_hits.extend(r.get("hits", {}).get("hits", []))
        ts_field = settings.TIMESTAMP_FIELD
        def ts_key(hit: Dict[str, Any]) -> str:
            src = hit.get("_source", {})
            return (
                src.get(ts_field)
                or src.get("@timestamp")
                or src.get("timestamp")
                or (hit.get("sort", [None])[0] or "")
            )
        # Descending by timestamp; ISO-8601 strings sort correctly lexicographically
        all_hits.sort(key=ts_key, reverse=True)
        # Respect requested page size
        size = int(body.get("size", 50))
        merged_hits = all_hits[:size]
        return {
            "hits": {
                "total": {"value": total, "relation": "eq"},
                "hits": merged_hits,
            }
        }


es_client = ESHttpClient()
multi_es_client = MultiESClient()