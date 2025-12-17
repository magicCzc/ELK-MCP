"""
Copyright (c) 2025, elk-MCP Project.
All rights reserved.
"""

from time import perf_counter
from fastapi import APIRouter, Depends
import httpx

from ..utils.error_codes import ErrorCode
from ..utils.i18n import I18NKeys
from ..models.schemas import (
    LogQueryRequest,
    QueryResponse,
    AlertsQueryRequest,
    StatsRequest,
)
from ..security.auth import authz, rbac
from ..config import settings
from ..es.client import es_client, multi_es_client
from ..indexes.service import index_discovery
from ..es.query_adapter import adapt_query_to_es6, build_aggregation_es6
from ..logs.normalizer import normalize
from ..metrics.metrics import REQUESTS_TOTAL, REQUEST_LATENCY, ES_BACKEND_LATENCY
from ..alerts.engine import evaluate_alerts


router = APIRouter()


@router.post("/query", response_model=QueryResponse)
def query_logs(payload: LogQueryRequest, ctx=Depends(authz)):
    token, tenant_id = ctx
    if not rbac.allow(token=token, tenant_id=tenant_id, action="query"):
        return {"code": ErrorCode.RBAC_DENIED, "i18n_key": I18NKeys.ERROR_RBAC_DENY, "data": {}}

    REQUESTS_TOTAL.labels(endpoint="query").inc()
    t0 = perf_counter()
    body = adapt_query_to_es6(
        tenant_id=payload.tenant_id,
        pagination=payload.pagination.model_dump(),
        time_range=payload.time_range.model_dump(),
        filters=payload.filters.model_dump(),
        sort=payload.sort.model_dump(),
    )
    # Dynamic target indices
    target_indexes = (
        payload.override_indexes
        if payload.override_indexes
        else (
            index_discovery.find_indices(
                keyword=(payload.index_keyword or ""),
                use_regex=bool(payload.use_regex),
                fuzzy=True,
            )
            if payload.index_keyword is not None
            else settings.LOG_INDEXES
        )
    )

    # Debug: print indices and DSL when DEBUG_QUERY_LOGS is enabled
    _dbg = bool(getattr(settings, "DEBUG_QUERY_LOGS", False))
    if _dbg:
        try:
            indices_dbg = target_indexes or settings.LOG_INDEXES
            print("[DEBUG][query] indices =", indices_dbg)
            print(
                "[DEBUG][query] from/size/sort =",
                body.get("from"),
                body.get("size"),
                body.get("sort"),
            )
            print("[DEBUG][query] dsl =", str(body.get("query"))[:2000])
        except Exception:
            pass

    es_t0 = perf_counter()
    try:
        # Degrade if too many indices
        indices = target_indexes or settings.LOG_INDEXES
        if len(indices) > 200:
            indices = indices[:200]
        if len(settings.ES_HOSTS) > 1:
            res = multi_es_client.search_logs_all(
                index=indices, body=body, doc_type=(settings.LOG_DOC_TYPE or None)
            )
        else:
            res = es_client.search_logs(index=indices, body=body, doc_type=(settings.LOG_DOC_TYPE or None))
    except httpx.HTTPError:
        # Fallback: try with fewer indices if possible
        try:
            indices = (target_indexes or settings.LOG_INDEXES)[:50]
            if len(settings.ES_HOSTS) > 1:
                res = multi_es_client.search_logs_all(
                    index=indices, body=body, doc_type=(settings.LOG_DOC_TYPE or None)
                )
            else:
                res = es_client.search_logs(index=indices, body=body, doc_type=(settings.LOG_DOC_TYPE or None))
        except httpx.HTTPError:
            return {
                "code": ErrorCode.ES_CONNECTION,
                "i18n_key": I18NKeys.ERROR_ES_CONNECTION,
                "data": {},
            }
    es_t1 = perf_counter()
    ES_BACKEND_LATENCY.labels(endpoint="query").observe((es_t1 - es_t0) * 1000)
    hits = res.get("hits", {}).get("hits", [])
    total_raw = res.get("hits", {}).get("total")
    total = total_raw.get("value") if isinstance(total_raw, dict) else total_raw

    if _dbg:
        try:
            sample = hits[0] if hits else {}
            src = sample.get("_source", {})
            print("[DEBUG][res] total/hits_len =", total, len(hits))
            print("[DEBUG][res] sample.keys =", list(src.keys())[:25])
            print(
                "[DEBUG][res] sample.type/loglevel/service =",
                src.get("type"),
                src.get("loglevel"),
                src.get("service"),
            )
            fields_service = (src.get("fields", {}) or {}).get("service")
            print("[DEBUG][res] sample.fields.service =", fields_service)
        except Exception:
            pass

    data = {
        "total": total,
        "items": [normalize(h) for h in hits],
    }
    # Cursor mode: expose next_cursor_after for client to continue
    try:
        if getattr(payload, "mode", "page") == "cursor":
            last = hits[-1] if hits else None
            next_after = last.get("sort") if isinstance(last, dict) else None
            data["next_cursor_after"] = next_after
            data["page_size"] = payload.pagination.page_size
    except Exception:
        pass
    t1 = perf_counter()
    REQUEST_LATENCY.labels(endpoint="query").observe((t1 - t0) * 1000)
    return {"code": ErrorCode.OK, "i18n_key": I18NKeys.INFO_QUERY_OK, "data": data}


@router.post("/alerts", response_model=QueryResponse)
def alerts(payload: AlertsQueryRequest, ctx=Depends(authz)):
    token, tenant_id = ctx
    if not rbac.allow(token=token, tenant_id=tenant_id, action="alerts"):
        return {"code": ErrorCode.RBAC_DENIED, "i18n_key": I18NKeys.ERROR_RBAC_DENY, "data": {}}

    REQUESTS_TOTAL.labels(endpoint="alerts").inc()
    body = adapt_query_to_es6(
        tenant_id=payload.tenant_id,
        pagination={"page": 1, "page_size": 100},
        time_range=payload.time_range.model_dump(),
        filters={},
        sort={"field": settings.TIMESTAMP_FIELD, "order": "desc"},
    )
    es_t0 = perf_counter()
    try:
        if len(settings.ES_HOSTS) > 1:
            res = multi_es_client.search_logs_all(
                index=settings.LOG_INDEXES, body=body, doc_type=(settings.LOG_DOC_TYPE or None)
            )
        else:
            res = es_client.search_logs(
                index=settings.LOG_INDEXES, body=body, doc_type=(settings.LOG_DOC_TYPE or None)
            )
    except httpx.HTTPError:
        return {"code": ErrorCode.ES_CONNECTION, "i18n_key": I18NKeys.ERROR_ES_CONNECTION, "data": {}}
    es_t1 = perf_counter()
    ES_BACKEND_LATENCY.labels(endpoint="alerts").observe((es_t1 - es_t0) * 1000)
    hits = res.get("hits", {}).get("hits", [])
    evaluated = evaluate_alerts(hits, payload.severity or [])
    items = [normalize(e["hit"]) | {"severity": e["severity"]} for e in evaluated]
    return {"code": ErrorCode.OK, "i18n_key": I18NKeys.INFO_ALERTS_OK, "data": {"items": items}}


@router.post("/stats", response_model=QueryResponse)
def stats(payload: StatsRequest, ctx=Depends(authz)):
    token, tenant_id = ctx
    if not rbac.allow(token=token, tenant_id=tenant_id, action="stats"):
        return {"code": ErrorCode.RBAC_DENIED, "i18n_key": I18NKeys.ERROR_RBAC_DENY, "data": {}}

    REQUESTS_TOTAL.labels(endpoint="stats").inc()
    base = adapt_query_to_es6(
        tenant_id=payload.tenant_id,
        pagination={"page": 1, "page_size": 0},
        time_range=payload.time_range.model_dump(),
        filters={},
        sort={"field": "timestamp", "order": "desc"},
    )
    base.update(build_aggregation_es6(field=payload.group_by))
    try:
        res = es_client.search_logs(index=settings.LOG_INDEXES, body=base, doc_type=(settings.LOG_DOC_TYPE or None))
    except httpx.HTTPError:
        return {"code": ErrorCode.ES_CONNECTION, "i18n_key": I18NKeys.ERROR_ES_CONNECTION, "data": {}}
    buckets = res.get("aggregations", {}).get("group_stats", {}).get("buckets", [])
    data = {"buckets": buckets}
    return {"code": ErrorCode.OK, "i18n_key": I18NKeys.INFO_STATS_OK, "data": data}


# 分页会话初始化接口
@router.post("/paginate/init", response_model=QueryResponse)
def init_pagination(payload: LogQueryRequest, ctx=Depends(authz)):
    """
    初始化分页会话
    
    功能描述：
    - 创建分页会话，返回分页ID和总页数
    - 不返回实际数据，仅返回分页元数据
    
    参数说明：
    - payload: 日志查询请求参数（与普通查询相同）
    
    返回说明：
    - session_id: 分页会话ID
    - total_pages: 总页数
    - total_items: 总数据条数
    - page_size: 每页大小
    """
    token, tenant_id = ctx
    if not rbac.allow(token=token, tenant_id=tenant_id, action="query"):
        return {"code": ErrorCode.RBAC_DENIED, "i18n_key": I18NKeys.ERROR_RBAC_DENY, "data": {}}

    REQUESTS_TOTAL.labels(endpoint="paginate_init").inc()
    
    # 构建查询参数，设置page_size=0仅获取总数
    query_params = {
        "tenant_id": payload.tenant_id,
        "pagination": payload.pagination.model_dump(),
        "time_range": payload.time_range.model_dump(),
        "filters": payload.filters.model_dump(),
        "sort": payload.sort.model_dump(),
        "mode": "page",  # 分页模式固定为page
        "index_keyword": payload.index_keyword,
        "use_regex": payload.use_regex,
        "override_indexes": payload.override_indexes
    }
    
    # 构建ES查询DSL，仅获取总数
    body = adapt_query_to_es6(**query_params)
    body["size"] = 0  # 不返回实际数据，仅获取总数
    
    # 获取目标索引
    target_indexes = (
        payload.override_indexes
        if payload.override_indexes
        else (
            index_discovery.find_indices(
                keyword=(payload.index_keyword or ""),
                use_regex=bool(payload.use_regex),
                fuzzy=True,
            )
            if payload.index_keyword is not None
            else settings.LOG_INDEXES
        )
    )
    
    # 执行ES查询，仅获取总数
    try:
        indices = target_indexes or settings.LOG_INDEXES
        if len(indices) > 200:
            indices = indices[:200]
        
        if len(settings.ES_HOSTS) > 1:
            res = multi_es_client.search_logs_all(
                index=indices, body=body, doc_type=(settings.LOG_DOC_TYPE or None)
            )
        else:
            res = es_client.search_logs(index=indices, body=body, doc_type=(settings.LOG_DOC_TYPE or None))
    except httpx.HTTPError:
        return {"code": ErrorCode.ES_CONNECTION, "i18n_key": I18NKeys.ERROR_ES_CONNECTION, "data": {}}
    
    # 解析总数
    total_raw = res.get("hits", {}).get("total")
    total_items = total_raw.get("value") if isinstance(total_raw, dict) else total_raw
    
    # 计算总页数
    page_size = payload.pagination.page_size
    total_pages = (total_items + page_size - 1) // page_size
    
    # 创建分页会话
    from ..utils.pagination_session import pagination_session_manager
    session = pagination_session_manager.create_session(
        tenant_id=payload.tenant_id,
        query_params=query_params,
        total_items=total_items,
        page_size=page_size
    )
    
    # 返回分页元数据
    data = {
        "session_id": session.session_id,
        "total_pages": session.total_pages,
        "total_items": session.total_items,
        "page_size": session.page_size
    }
    
    return {"code": ErrorCode.OK, "i18n_key": I18NKeys.INFO_QUERY_OK, "data": data}


# 分页数据获取接口
@router.post("/paginate/get", response_model=QueryResponse)
def get_paginated_data(payload: dict, ctx=Depends(authz)):
    """
    获取分页数据
    
    功能描述：
    - 通过分页ID和页码获取对应页的详细数据
    - 使用已创建的分页会话进行查询
    
    参数说明：
    - session_id: 分页会话ID
    - page: 页码
    
    返回说明：
    - items: 当前页的数据列表
    - current_page: 当前页码
    - total_pages: 总页数
    """
    token, tenant_id = ctx
    if not rbac.allow(token=token, tenant_id=tenant_id, action="query"):
        return {"code": ErrorCode.RBAC_DENIED, "i18n_key": I18NKeys.ERROR_RBAC_DENY, "data": {}}

    REQUESTS_TOTAL.labels(endpoint="paginate_get").inc()
    
    # 验证请求参数
    session_id = payload.get("session_id")
    page = payload.get("page")
    
    if not session_id or not page:
        return {"code": ErrorCode.INVALID_PARAM, "i18n_key": I18NKeys.ERROR_INVALID_PARAM, "data": {}}
    
    # 获取分页会话
    from ..utils.pagination_session import pagination_session_manager
    session = pagination_session_manager.get_session(session_id)
    
    # 检查会话是否有效
    if not session:
        return {"code": ErrorCode.SESSION_EXPIRED, "i18n_key": I18NKeys.ERROR_SESSION_EXPIRED, "data": {}}
    
    # 检查页码是否有效
    if not session.is_valid_page(page):
        return {"code": ErrorCode.INVALID_PAGE, "i18n_key": I18NKeys.ERROR_INVALID_PAGE, "data": {}}
    
    # 获取目标索引
    index_keyword = session.query_params.get("index_keyword")
    use_regex = session.query_params.get("use_regex", False)
    override_indexes = session.query_params.get("override_indexes")
    
    target_indexes = (
        override_indexes
        if override_indexes
        else (
            index_discovery.find_indices(
                keyword=(index_keyword or ""),
                use_regex=bool(use_regex),
                fuzzy=True,
            )
            if index_keyword is not None
            else settings.LOG_INDEXES
        )
    )
    
    # 构建查询参数，更新页码
    query_params = session.query_params.copy()
    query_params["pagination"]["page"] = page
    
    # 构建ES查询DSL
    body = adapt_query_to_es6(**query_params)
    
    # 执行ES查询
    try:
        indices = target_indexes or settings.LOG_INDEXES
        if len(indices) > 200:
            indices = indices[:200]
        
        if len(settings.ES_HOSTS) > 1:
            res = multi_es_client.search_logs_all(
                index=indices, body=body, doc_type=(settings.LOG_DOC_TYPE or None)
            )
        else:
            res = es_client.search_logs(index=indices, body=body, doc_type=(settings.LOG_DOC_TYPE or None))
    except httpx.HTTPError:
        return {"code": ErrorCode.ES_CONNECTION, "i18n_key": I18NKeys.ERROR_ES_CONNECTION, "data": {}}
    
    # 解析结果
    hits = res.get("hits", {}).get("hits", [])
    items = [normalize(h) for h in hits]
    
    # 返回分页数据
    data = {
        "items": items,
        "current_page": page,
        "total_pages": session.total_pages
    }
    
    return {"code": ErrorCode.OK, "i18n_key": I18NKeys.INFO_QUERY_OK, "data": data}
