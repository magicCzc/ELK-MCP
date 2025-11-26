"""
Copyright (c) 2025, elk-MCP Project.
All rights reserved.
"""

from fastapi import APIRouter, Depends, HTTPException

from ..utils.error_codes import ErrorCode
from ..utils.i18n import I18NKeys
from ..security.auth import authz, rbac
from ..indexes.service import index_discovery
from ..models.schemas import QueryResponse, IndexDiscoveryConfig


router = APIRouter()


@router.get("/list", response_model=QueryResponse)
def list_indices(ctx=Depends(authz)):
    token, tenant_id = ctx
    if not rbac.allow(token=token, tenant_id=tenant_id, action="indices_read"):
        return {
            "code": ErrorCode.RBAC_DENIED,
            "i18n_key": I18NKeys.ERROR_RBAC_DENY,
            "data": {},
        }
    return {
        "code": ErrorCode.OK,
        "i18n_key": I18NKeys.INFO_INDICES_OK,
        "data": {"items": index_discovery.get_indices(), "status": index_discovery.get_status()},
    }


@router.post("/config", response_model=QueryResponse)
def update_config(payload: IndexDiscoveryConfig, ctx=Depends(authz)):
    token, tenant_id = ctx
    if not rbac.allow(token=token, tenant_id=tenant_id, action="indices_config"):
        return {
            "code": ErrorCode.RBAC_DENIED,
            "i18n_key": I18NKeys.ERROR_RBAC_DENY,
            "data": {},
        }
    try:
        index_discovery.update_config(
            enabled=payload.enabled,
            interval_seconds=payload.interval_seconds,
            include_patterns=payload.include_patterns,
            exclude_patterns=payload.exclude_patterns,
        )
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={"code": ErrorCode.BAD_INPUT, "i18n_key": I18NKeys.ERROR_INDICES_BAD_CONFIG},
        ) from e
    return {
        "code": ErrorCode.OK,
        "i18n_key": I18NKeys.INFO_INDICES_CONFIG_OK,
        "data": {"status": index_discovery.get_status()},
    }


@router.post("/refresh", response_model=QueryResponse)
def refresh(ctx=Depends(authz)):
    token, tenant_id = ctx
    if not rbac.allow(token=token, tenant_id=tenant_id, action="indices_refresh"):
        return {
            "code": ErrorCode.RBAC_DENIED,
            "i18n_key": I18NKeys.ERROR_RBAC_DENY,
            "data": {},
        }
    index_discovery.refresh_once()
    return {
        "code": ErrorCode.OK,
        "i18n_key": I18NKeys.INFO_INDICES_REFRESH_OK,
        "data": {"items": index_discovery.get_indices(), "status": index_discovery.get_status()},
    }

