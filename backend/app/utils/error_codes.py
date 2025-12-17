"""
Copyright (c) 2025, elk-MCP Project.
All rights reserved.
"""

from enum import IntEnum


class ErrorCode(IntEnum):
    OK = 0
    AUTH_INVALID_TOKEN = 1001
    TENANT_MISSING = 1002
    RBAC_DENIED = 1003
    ES_CONNECTION = 2001
    BAD_INPUT = 3001
    INVALID_PARAM = 3002
    SESSION_EXPIRED = 3003
    INVALID_PAGE = 3004
    INTERNAL_ERROR = 9000

