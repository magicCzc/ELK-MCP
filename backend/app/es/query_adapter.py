"""
Copyright (c) 2025, elk-MCP Project.
All rights reserved.
"""

from typing import Any, Dict, List, Optional
from ..config import settings


def adapt_query_to_es6(payload: dict = None, **kwargs):
    """Build ES 6.x compatible search DSL.

    - Use bool/filter for structured filters to leverage caching and speed.
    - Keep sort on 'timestamp' or '_score'.
    - Apply tenant_id as a must filter.
    """
    # Normalize inputs: support dict payload and keyword-args safely
    query = payload if (payload is not None and isinstance(payload, dict)) else kwargs

    tenant_id = query.get("tenant_id")
    pagination = query.get("pagination") or {}
    time_range = query.get("time_range") or {}
    filters = query.get("filters") or {}
    sort = query.get("sort") or {}
    mode = str(query.get("mode") or "page")
    cursor_after = query.get("cursor_after")

    page = max(1, int(pagination.get("page", 1)))
    size = max(
        1,
        min(int(pagination.get("page_size", 50)), settings.MAX_PAGE_SIZE, 200),
    )
    from_ = (page - 1) * size

    must_filters: List[Dict[str, Any]] = []
    filter_filters: List[Dict[str, Any]] = []

    # tenant filter: only apply when not "all"
    if tenant_id and str(tenant_id).lower() != "all":
        filter_filters.append({"term": {"tenant_id": tenant_id}})

    # time range filter: support both TIMESTAMP_FIELD and "@timestamp"
    ts_start = time_range.get("start")
    ts_end = time_range.get("end")
    if ts_start and ts_end:
        ts_fields: List[str] = [settings.TIMESTAMP_FIELD]
        if "@timestamp" not in ts_fields:
            ts_fields.append("@timestamp")
        filter_filters.append(
            {
                "bool": {
                    "should": [
                        {"range": {f: {"gte": ts_start, "lte": ts_end}}} for f in ts_fields
                    ],
                    "minimum_should_match": 1,
                }
            }
        )

    # level filter: support "level" and "loglevel"
    # level filter: prefer keyword subfields, fallback to raw
    levels = filters.get("level") or filters.get("loglevel") or []
    if levels:
        filter_filters.append(
            {
                "bool": {
                    "should": [
                        {"terms": {"loglevel.keyword": levels}},
                        {"terms": {"level.keyword": levels}},
                        {"terms": {"loglevel": levels}},
                        {"terms": {"level": levels}},
                    ],
                    "minimum_should_match": 1,
                }
            }
        )

    # service filter: support multiple fields + underscore/hyphen variants
    services = filters.get("service") or []
    if services:
        variants: List[str] = []
        for s in services:
            s = str(s).strip()
            if not s:
                continue
            variants.extend([s, s.replace("-", "_"), s.replace("_", "-")])
        variants = sorted(set(variants))
        filter_filters.append(
            {
                "bool": {
                    "should": [
                        {"terms": {"type.keyword": variants}},
                        {"terms": {"type": variants}},
                        {"terms": {"service.keyword": variants}},
                        {"terms": {"service": variants}},
                        {"terms": {"fields.service.keyword": variants}},
                        {"terms": {"fields.service": variants}},
                    ],
                    "minimum_should_match": 1,
                }
            }
        )

    # keyword search: restrict to message/logmessage
    keyword = filters.get("keyword")
    if isinstance(keyword, str) and keyword.strip():
        must_filters.append(
            {
                "multi_match": {
                    "query": keyword.strip(),
                    "fields": ["message", "logmessage"],
                    "type": "best_fields",
                }
            }
        )

    sort_field = str(sort.get("field") or settings.TIMESTAMP_FIELD)
    sort_order = str(sort.get("order") or "desc")
    # Always include a stable tie-breaker to make search_after deterministic
    es_sort = [{sort_field: {"order": sort_order}}, {"_id": {"order": "asc"}}]

    body: Dict[str, Any] = {
        "size": size,
        "sort": es_sort,
        "query": {"bool": {"must": must_filters, "filter": filter_filters}},
    }
    # Offset pagination vs cursor pagination
    if mode == "cursor":
        # Cursor mode: do not set "from"; optionally set search_after
        if isinstance(cursor_after, list) and len(cursor_after) > 0:
            body["search_after"] = cursor_after
    else:
        # Default: page mode
        body["from"] = from_
    # 仅返回必要字段，降低响应体大小
    includes: List[str] = [
        settings.TIMESTAMP_FIELD,
        "@timestamp",
        "timestamp",
        "level",
        "loglevel",
        "message",
        "log",
        "service",
        "tenant_id",
        "host",
        "fields.service",
    ]
    body["_source"] = {"includes": sorted(set(includes))}

    # Aggregations for stats will be built in another function.
    return body


def build_aggregation_es6(*, field: str) -> Dict[str, Any]:
    return {
        "aggs": {
            "group_stats": {
                "terms": {"field": field, "size": 1000},
            }
        }
    }
