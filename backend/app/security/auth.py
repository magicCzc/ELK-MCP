"""
Copyright (c) 2025, elk-MCP Project.
All rights reserved.
"""

from typing import Dict, Optional
from fastapi import Header, HTTPException

from ..utils.error_codes import ErrorCode
from ..utils.i18n import I18NKeys


class RBAC:
    def __init__(self, rules: Optional[Dict] = None) -> None:
        self.rules = rules or {}

    def allow(self, *, token: str, tenant_id: str, action: str) -> bool:
        # Minimal in-memory RBAC; replace with file-backed if provided.
        if not token:
            return False
        # Example: token prefix maps to tenant role
        role = "viewer"
        if token.startswith("admin-"):
            role = "admin"
        if action in ("query", "alerts", "stats", "indices_read"):
            return True if role in ("admin", "viewer") else False
        if action in ("indices_config", "indices_refresh"):
            return True if role in ("admin",) else False
        return False


rbac = RBAC()


def authz(
    authorization: Optional[str] = Header(None),
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-Id"),
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail={
                "code": ErrorCode.AUTH_INVALID_TOKEN,
                "i18n_key": I18NKeys.ERROR_AUTH_INVALID_TOKEN,
            },
        )
    token = authorization.split(" ", 1)[1]
    if not x_tenant_id:
        raise HTTPException(
            status_code=400,
            detail={
                "code": ErrorCode.TENANT_MISSING,
                "i18n_key": I18NKeys.ERROR_TENANT_MISSING,
            },
        )
    return token, x_tenant_id
