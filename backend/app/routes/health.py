"""
Copyright (c) 2025, elk-MCP Project.
All rights reserved.
"""

from fastapi import APIRouter
from ..utils.error_codes import ErrorCode

router = APIRouter()


@router.get("/healthz")
def healthz():
    # Basic health response; ES connectivity could be checked on demand.
    return {"code": ErrorCode.OK, "i18n_key": "info.health.ok", "data": {"status": "ok"}}

