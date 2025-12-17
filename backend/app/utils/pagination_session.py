"""
文件功能：分页会话管理工具
主要类/函数：
- PaginationSessionManager: 分页会话管理类
- PaginationSession: 分页会话数据类
作者：
创建时间：2025-05-16
最后修改：2025-05-16
"""

import uuid
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict

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
        """检查会话是否已过期"""
        return time.time() > self.expires_at
    
    def is_valid_page(self, page: int) -> bool:
        """检查页码是否有效"""
        return 1 <= page <= self.total_pages


class PaginationSessionManager:
    """
    分页会话管理类
    
    功能描述：
    - 创建和管理分页会话
    - 存储会话信息在内存中
    - 提供会话查找和过期清理功能
    """
    
    def __init__(self, ttl: int = DEFAULT_SESSION_TTL):
        """
        初始化分页会话管理器
        
        参数说明：
        - ttl: 会话过期时间（秒）
        """
        self._sessions: Dict[str, PaginationSession] = {}
        self._ttl = ttl
    
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
        # 清理过期会话
        self._clean_expired()
        
        # 生成唯一会话ID
        session_id = str(uuid.uuid4())
        
        # 计算总页数
        total_pages = (total_items + page_size - 1) // page_size
        
        # 创建会话
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
        
        # 存储会话
        self._sessions[session_id] = session
        
        return session
    
    def get_session(self, session_id: str) -> Optional[PaginationSession]:
        """
        获取分页会话
        
        参数说明：
        - session_id: 分页会话ID
        
        返回说明：
        - Optional[PaginationSession]: 分页会话对象，如果不存在或已过期返回None
        """
        # 清理过期会话
        self._clean_expired()
        
        # 查找会话
        session = self._sessions.get(session_id)
        
        # 检查会话是否存在且未过期
        if session and not session.is_expired():
            return session
        
        # 如果会话已过期，从存储中移除
        if session:
            del self._sessions[session_id]
        
        return None
    
    def _clean_expired(self):
        """清理过期会话"""
        expired_ids = [
            session_id for session_id, session in self._sessions.items() 
            if session.is_expired()
        ]
        
        for session_id in expired_ids:
            del self._sessions[session_id]


# 创建全局分页会话管理器实例
pagination_session_manager = PaginationSessionManager()