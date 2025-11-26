"""
Copyright (c) 2025, elk-MCP Project.
All rights reserved.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, constr


class Pagination(BaseModel):
    page: int = Field(1, ge=1, le=100000)
    page_size: int = Field(50, ge=1, le=200)


class TimeRange(BaseModel):
    start: constr(strip_whitespace=True)
    end: constr(strip_whitespace=True)


class LogQueryFilters(BaseModel):
    level: Optional[List[str]] = None
    service: Optional[List[str]] = None
    keyword: Optional[str] = None


class SortSpec(BaseModel):
    field: str = Field("timestamp")
    order: str = Field("desc")


class LogQueryRequest(BaseModel):
    tenant_id: str
    pagination: Pagination
    time_range: TimeRange
    filters: LogQueryFilters = Field(default_factory=LogQueryFilters)
    sort: SortSpec = Field(default_factory=SortSpec)
    # Dynamic index selection
    index_keyword: Optional[str] = None
    use_regex: Optional[bool] = False
    override_indexes: Optional[List[str]] = None


class AlertRuleRef(BaseModel):
    id: str
    severity: Optional[str] = None


class AlertsQueryRequest(BaseModel):
    tenant_id: str
    time_range: TimeRange
    severity: Optional[List[str]] = None
    rules: Optional[List[AlertRuleRef]] = None


class StatsRequest(BaseModel):
    tenant_id: str
    time_range: TimeRange
    group_by: str = Field(..., pattern=r"^(service|level|host)$")


class StandardLog(BaseModel):
    timestamp: str
    level: Optional[str]
    message: str
    service: Optional[str]
    tenant_id: str
    host: Optional[str]
    extra: Dict[str, Any] = Field(default_factory=dict)


class QueryResponse(BaseModel):
    code: int
    i18n_key: str
    data: Dict[str, Any]


class IndexDiscoveryConfig(BaseModel):
    enabled: Optional[bool] = None
    interval_seconds: Optional[int] = Field(default=None, ge=5, le=3600)
    include_patterns: Optional[List[str]] = None
    exclude_patterns: Optional[List[str]] = None
