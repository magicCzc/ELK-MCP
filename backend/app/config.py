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

    RBAC_CONFIG_PATH: str = Field(default="")
    METRICS_ENABLED: bool = Field(default=True)

    # Index discovery configuration (can be changed at runtime via API)
    INDEX_DISCOVERY_ENABLED: bool = Field(default=True)
    INDEX_DISCOVERY_INTERVAL_SECONDS: int = Field(default=60)
    INDEX_INCLUDE_PATTERNS: List[str] = Field(default=[r"^kst-logs-[A-Za-z0-9_-].*"])
    INDEX_EXCLUDE_PATTERNS: List[str] = Field(default=[])
    # 开发调试开关（用于打印查询 DSL 与索引）
    DEBUG_QUERY_LOGS: bool = Field(default=False)
    # 响应体控制：分页上限与消息最大长度（避免 Dify 1MB 限制）
    MAX_PAGE_SIZE: int = Field(default=20, ge=1, le=200)
    MAX_MESSAGE_LEN: int = Field(default=4096, ge=256, le=65536)

    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()