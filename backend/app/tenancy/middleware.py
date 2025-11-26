"""
Copyright (c) 2025, elk-MCP Project.
All rights reserved.
"""

from typing import Optional, Tuple
from fastapi import Request, HTTPException

from ..utils.error_codes import ErrorCode
from ..utils.i18n import I18NKeys


def extract_tenant(request: Request) -> Tuple[str, str]:
    auth_header: Optional[str] = request.headers.get("Authorization")
    tenant_id: Optional[str] = request.headers.get("X-Tenant-Id")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail={
                "code": ErrorCode.AUTH_INVALID_TOKEN,
                "i18n_key": I18NKeys.ERROR_AUTH_INVALID_TOKEN,
            },
        )
    if not tenant_id:
        raise HTTPException(
            status_code=400,
            detail={
                "code": ErrorCode.TENANT_MISSING,
                "i18n_key": I18NKeys.ERROR_TENANT_MISSING,
            },
        )
    return auth_header.split(" ", 1)[1], tenant_id

