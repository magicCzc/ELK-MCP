"""
Copyright (c) 2025, elk-MCP Project.
All rights reserved.
"""

from typing import Any, Dict


def normalize(hit: Dict[str, Any]) -> Dict[str, Any]:
    from ..config import settings
    src = hit.get("_source", {})
    msg = src.get("message") or src.get("log")
    if msg is not None:
        msg = str(msg)
        if len(msg) > settings.MAX_MESSAGE_LEN:
            msg = msg[: settings.MAX_MESSAGE_LEN]
    return {
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