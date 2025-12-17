"""
Copyright (c) 2025, elk-MCP Project.
All rights reserved.
"""

from typing import Any, Dict


def normalize(hit: Dict[str, Any]) -> Dict[str, Any]:
    from ..config import settings
    # 导入脱敏器
    from .desensitizer import log_desensitizer
    
    src = hit.get("_source", {})
    msg = src.get("message") or src.get("log")
    if msg is not None:
        msg = str(msg)
        if len(msg) > settings.MAX_MESSAGE_LEN:
            msg = msg[: settings.MAX_MESSAGE_LEN]
    
    # 构建原始日志数据
    raw_log = {
        "timestamp": src.get("@timestamp")
        or src.get("timestamp")
        or hit.get("sort", [None])[0],
        "level": src.get("level"),
        "message": msg,
        "service": src.get("service"),
        "tenant_id": src.get("tenant_id"),
        "host": src.get("host"),
        "extra": {
            k: v
            for k, v in src.items()
            if k
            not in {
                "@timestamp",
                "timestamp",
                "level",
                "message",
                "log",
                "service",
                "tenant_id",
                "host",
            }
        },
    }
    
    # 对日志数据进行脱敏处理
    return log_desensitizer.desensitize_log(raw_log)