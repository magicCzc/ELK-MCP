"""
Copyright (c) 2025, elk-MCP Project.
All rights reserved.

文件功能：分页会话管理工具 (基于 Redis 存储)
主要类/函数：
- PaginationSessionManager: 分页会话管理类
- PaginationSession: 分页会话数据类
"""

import uuid
import time
import json
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict

import redis
from ..config import settings

logger = logging.getLogger(__name__)

# 分页会话的默认过期时间（秒）
DEFAULT_SESSION_TTL = 3600  # 1小时


@dataclass
class PaginationSession:
    """
    分页会话数据类
    
    参数说明：
    - session_id: 分页会话ID
    - tenant_id: 租户ID
    - query_params: 查询参数
    - total_items: 总数据条数
    - page_size: 每页大小
    - total_pages: 总页数
    - created_at: 创建时间
    - expires_at: 过期时间
    """
    session_id: str
    tenant_id: str
    query_params: Dict[str, Any]
    total_items: int
    page_size: int
    total_pages: int
    created_at: float
    expires_at: float
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return asdict(self)
    
    def is_expired(self) -> bool:
        """检查会话是否已过期 (Redis 自动过期，此方法作为冗余校验)"""
        return time.time() > self.expires_at
    
    def is_valid_page(self, page: int) -> bool:
        """检查页码是否有效"""
        return 1 <= page <= self.total_pages


class PaginationSessionManager:
    """
    分页会话管理类
    
    功能描述：
    - 创建和管理分页会话
    - 使用 Redis 存储会话信息，支持分布式/多进程共享
    - 利用 Redis TTL 自动清理过期会话
    """
    
    def __init__(self, ttl: int = DEFAULT_SESSION_TTL):
        """
        初始化分页会话管理器
        
        参数说明：
        - ttl: 会话过期时间（秒）
        """
        self._ttl = ttl
        self._prefix = "mcp:session:"
        
        # 初始化 Redis 连接
        try:
            if settings.REDIS_URL:
                self._redis = redis.from_url(
                    settings.REDIS_URL, 
                    decode_responses=True
                )
            else:
                self._redis = redis.Redis(
                    host=settings.REDIS_HOST,
                    port=settings.REDIS_PORT,
                    db=settings.REDIS_DB,
                    password=settings.REDIS_PASSWORD,
                    ssl=settings.REDIS_USE_SSL,
                    decode_responses=True,
                    socket_timeout=2.0,
                    socket_connect_timeout=2.0
                )
            # 测试连接
            self._redis.ping()
            logger.info("Successfully connected to Redis for pagination sessions.")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}. Pagination sessions will not work correctly.")
            # 在生产环境下，如果 Redis 是必须的，这里可能需要抛出异常
            # 为了保证代码健壮性，这里仅记录错误
            self._redis = None

    def create_session(self, tenant_id: str, query_params: Dict[str, Any], total_items: int, page_size: int) -> PaginationSession:
        """
        创建新的分页会话
        
        参数说明：
        - tenant_id: 租户ID
        - query_params: 查询参数
        - total_items: 总数据条数
        - page_size: 每页大小
        
        返回说明：
        - PaginationSession: 分页会话对象
        """
        # 生成唯一会话ID
        session_id = str(uuid.uuid4())
        
        # 计算总页数
        total_pages = max(1, (total_items + page_size - 1) // page_size)
        
        # 创建会话对象
        now = time.time()
        session = PaginationSession(
            session_id=session_id,
            tenant_id=tenant_id,
            query_params=query_params,
            total_items=total_items,
            page_size=page_size,
            total_pages=total_pages,
            created_at=now,
            expires_at=now + self._ttl
        )
        
        # 存储到 Redis
        if self._redis:
            try:
                key = f"{self._prefix}{session_id}"
                self._redis.setex(
                    key,
                    self._ttl,
                    json.dumps(session.to_dict())
                )
            except Exception as e:
                logger.error(f"Failed to save session to Redis: {e}")
        
        return session
    
    def get_session(self, session_id: str) -> Optional[PaginationSession]:
        """
        获取分页会话
        
        参数说明：
        - session_id: 分页会话ID
        
        返回说明：
        - Optional[PaginationSession]: 分页会话对象，如果不存在或已过期返回None
        """
        if not self._redis:
            return None
            
        try:
            key = f"{self._prefix}{session_id}"
            data = self._redis.get(key)
            
            if not data:
                return None
            
            # 反序列化
            session_dict = json.loads(data)
            return PaginationSession(**session_dict)
        except Exception as e:
            logger.error(f"Failed to get session from Redis: {e}")
            return None
    
    def _clean_expired(self):
        """清理过期会话 - Redis 会自动处理，此方法保持空实现以兼容旧调用"""
        pass


# 创建全局分页会话管理器实例
pagination_session_manager = PaginationSessionManager()
