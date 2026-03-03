"""
Copyright (c) 2025, elk-MCP Project.
All rights reserved.
"""

from typing import Any, Dict, List, Optional
from ..config import settings


# 支持的模糊匹配类型
FUZZY_MATCH_TYPES = {"contains", "prefix", "fuzzy", "wildcard", "regexp"}


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
                        {"terms": {"service_name.keyword": variants}},
                        {"terms": {"service_name": variants}},
                        {"terms": {"app_name.keyword": variants}},
                        {"terms": {"app_name": variants}},
                        {"terms": {"application.keyword": variants}},
                        {"terms": {"application": variants}},
                        {"terms": {"component.keyword": variants}},
                        {"terms": {"component": variants}},
                    ],
                    "minimum_should_match": 1,
                }
            }
        )

    # Lucene query_string syntax support
    # Priority: query_string > filters.keyword (if query_string provided, keyword is ignored)
    query_string = query.get("query_string")
    if isinstance(query_string, str) and query_string.strip():
        # 安全检查：禁止前导通配符，防止全表扫描
        cleaned_query = query_string.strip()
        # 移除危险的前导通配符（如 *error, ?test）
        import re
        # 检测并警告前导通配符
        if re.search(r'(^|\s)[\*\?]', cleaned_query):
            # 自动移除前导通配符，保留其余部分
            cleaned_query = re.sub(r'(^|\s)[\*\?]+', r'\1', cleaned_query).strip()
        
        must_filters.append(
            {
                "query_string": {
                    "query": cleaned_query,
                    "default_operator": "AND",
                    "default_field": "message",
                    "fields": ["message", "logmessage", "log", "msg"],
                    "analyze_wildcard": False,  # 禁用通配符分析，提升性能
                    "allow_leading_wildcard": False,  # 禁止前导通配符，防止全表扫描
                    "lenient": True,
                    "max_determinized_states": 10000,  # 限制正则复杂度
                }
            }
        )
    else:
        # keyword search: restrict to message/logmessage with fuzzy match support
        keyword = filters.get("keyword")
        if isinstance(keyword, str) and keyword.strip():
            fuzzy_type = filters.get("fuzzy_type") or "contains"
            fuzzy_options = filters.get("fuzzy_options") or {}
            keyword_query = _build_keyword_query(
                keyword=keyword.strip(),
                fuzzy_type=fuzzy_type,
                fuzzy_options=fuzzy_options,
            )
            must_filters.append(keyword_query)

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


def _build_keyword_query(
    keyword: str,
    fuzzy_type: str = "contains",
    fuzzy_options: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """构建关键字查询的 ES DSL

    功能描述：根据指定的模糊匹配类型，构建对应的 Elasticsearch 查询语句

    参数说明：
    - keyword: [str] 搜索关键词，必需
    - fuzzy_type: [str] 模糊匹配类型，可选值：
        - "contains": 包含匹配（默认），使用 multi_match 最佳字段匹配
        - "prefix": 前缀匹配，匹配以关键词开头的日志
        - "fuzzy": 模糊匹配，容忍拼写错误，编辑距离由 fuzzy_options 控制
        - "wildcard": 通配符匹配，支持 * 和 ?
        - "regexp": 正则表达式匹配，功能最强但性能最差
    - fuzzy_options: [dict] 额外配置选项
        - fuzziness: [str/int] 编辑距离，默认 "AUTO"
        - prefix_length: [int] 前缀长度，默认 2
        - max_expansions: [int] 最大扩展数，默认 50
        - case_insensitive: [bool] 是否忽略大小写，默认 True

    返回说明：
    - [dict] Elasticsearch 查询 DSL

    使用示例：
    >>> # 包含匹配（默认）
    >>> q = _build_keyword_query("error", "contains")
    >>> # 前缀匹配
    >>> q = _build_keyword_query("connect", "prefix")
    >>> # 模糊匹配（容忍拼写错误）
    >>> q = _build_keyword_query("erorr", "fuzzy", {"fuzziness": "AUTO"})
    >>> # 通配符匹配
    >>> q = _build_keyword_query("*exception*", "wildcard")

    异常情况：
    - 如果 fuzzy_type 不支持，自动回退到 "contains" 类型
    - 如果 wildcard/regexp 格式错误，ES 会返回查询错误
    """
    fuzzy_options = fuzzy_options or {}
    match_type = fuzzy_type if fuzzy_type in FUZZY_MATCH_TYPES else "contains"

    # 定义搜索字段（按优先级排序）
    search_fields = ["message", "logmessage", "log", "msg"]

    if match_type == "contains":
        # 默认：最佳字段匹配
        return {
            "multi_match": {
                "query": keyword,
                "fields": search_fields,
                "type": "best_fields",
                "operator": "or",
            }
        }

    elif match_type == "prefix":
        # 前缀匹配：匹配以关键词开头的字段
        return {
            "bool": {
                "should": [
                    {"prefix": {field: {"value": keyword}}}
                    for field in search_fields
                ],
                "minimum_should_match": 1,
            }
        }

    elif match_type == "fuzzy":
        # 模糊匹配：容忍拼写错误
        fuzziness = fuzzy_options.get("fuzziness", "AUTO")
        prefix_length = fuzzy_options.get("prefix_length", 2)
        max_expansions = fuzzy_options.get("max_expansions", 50)

        return {
            "multi_match": {
                "query": keyword,
                "fields": search_fields,
                "type": "best_fields",
                "fuzziness": fuzziness,
                "prefix_length": prefix_length,
                "max_expansions": max_expansions,
                "operator": "or",
            }
        }

    elif match_type == "wildcard":
        # 通配符匹配：支持 *（任意字符）和 ?（单个字符）
        case_insensitive = fuzzy_options.get("case_insensitive", True)
        wildcard_queries = []
        for field in search_fields:
            q = {"wildcard": {field: {"value": keyword}}}
            if case_insensitive:
                q["wildcard"][field]["case_insensitive"] = True
            wildcard_queries.append(q)

        return {
            "bool": {
                "should": wildcard_queries,
                "minimum_should_match": 1,
            }
        }

    elif match_type == "regexp":
        # 正则匹配：功能最强但性能最差，谨慎使用
        case_insensitive = fuzzy_options.get("case_insensitive", True)
        flags = "ALL" if case_insensitive else None
        regexp_queries = []
        for field in search_fields:
            q = {"regexp": {field: {"value": keyword}}}
            if flags:
                q["regexp"][field]["flags"] = flags
            regexp_queries.append(q)

        return {
            "bool": {
                "should": regexp_queries,
                "minimum_should_match": 1,
            }
        }

    # 默认回退
    return {
        "multi_match": {
            "query": keyword,
            "fields": search_fields,
            "type": "best_fields",
        }
    }
