"""
Copyright (c) 2025, elk-MCP Project.
All rights reserved.
"""

from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    ES_HOSTS: List[str] = Field(default=["http://localhost:9200"])
    ES_VERIFY_SSL: bool = Field(default=True)
    TIMESTAMP_FIELD: str = Field(default="timestamp")
    ES_USERNAME: str = Field(default="")
    ES_PASSWORD: str = Field(default="")
    LOG_INDEXES: List[str] = Field(default=["logs-*"])
    LOG_DOC_TYPE: Optional[str] = Field(default=None)

    CACHE_ENABLED: bool = Field(default=True)
    CACHE_TTL_SECONDS: int = Field(default=30)
    CACHE_MAX_SIZE: int = Field(default=1000)

    # Redis configuration for session management
    REDIS_HOST: str = Field(default="127.0.0.1")
    REDIS_PORT: int = Field(default=63799)
    REDIS_DB: int = Field(default=0)
    REDIS_PASSWORD: Optional[str] = Field(default=None)
    REDIS_URL: Optional[str] = Field(default=None)
    REDIS_USE_SSL: bool = Field(default=False)

    RBAC_CONFIG_PATH: str = Field(default="")
    METRICS_ENABLED: bool = Field(default=True)

    # Index discovery configuration (can be changed at runtime via API)
    INDEX_DISCOVERY_ENABLED: bool = Field(default=True)
    INDEX_DISCOVERY_INTERVAL_SECONDS: int = Field(default=300)
    INDEX_INCLUDE_PATTERNS: List[str] = Field(default=[r"^logs-[A-Za-z0-9_-].*", r"^microservice-logs-[A-Za-z0-9_-].*", r"^app-logs-[A-Za-z0-9_-].*"])
    INDEX_EXCLUDE_PATTERNS: List[str] = Field(default=[])

    # Project to ES cluster mapping
    ES_PROJECT_MAP: str = Field(default="{}")

    # 开发调试开关（用于打印查询 DSL 与索引）
    DEBUG_QUERY_LOGS: bool = Field(default=False)
    # 响应体控制：分页上限与消息最大长度（避免 Dify 1MB 限制�?    MAX_PAGE_SIZE: int = Field(default=20, ge=1, le=200)
    MAX_MESSAGE_LEN: int = Field(default=4096, ge=256, le=65536)
    
    # 租户过滤配置
    # 如果设置�?True，当请求�?tenant_id 为空�?"all" 时，会自动使�?X-Tenant-Id header 的�?    # 如果设置�?False，当 tenant_id �?"all" 时，会跳�?tenant 过滤（适用于数据中没有 tenant_id 字段的场景）
    TENANT_FILTER_STRICT: bool = Field(default=False)

    class Config:
        env_file = ".env"
        case_sensitive = False

    _route_cache: Optional[dict] = None

    def _get_route_map(self) -> dict:
        """Helper to parse and cache the project map."""
        if self._route_cache is not None:
            return self._route_cache
        
        import json
        try:
            raw_map = self.ES_PROJECT_MAP.strip("'").strip('"')
            self._route_cache = json.loads(raw_map)
        except Exception:
            self._route_cache = {}
        return self._route_cache

    def get_project_route(self, keyword: str) -> Optional[str]:
        """Return the ES host for a given project keyword or index name."""
        mapping = self._get_route_map()
        if not mapping:
            return None
            
        k = keyword.upper()
        # 1. First try exact/contains match in projects list
        for host, projects in mapping.items():
            if any(p.upper() in k for p in projects):
                return host
                
        # 2. If no match, try reverse: see if any project name is part of the keyword
        # (Useful when keyword is a full index name like 'logs-center-2026.01.04')
        for host, projects in mapping.items():
            for p in projects:
                if p.upper() in k:
                    return host
        return None


settings = Settings()
