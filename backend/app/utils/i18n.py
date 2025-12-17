"""
Copyright (c) 2025, elk-MCP Project.
All rights reserved.
"""

# i18n keys registry. Do not hardcode texts; use keys instead.


class I18NKeys:
    ERROR_AUTH_INVALID_TOKEN = "error.auth.invalid_token"
    ERROR_TENANT_MISSING = "error.tenant.missing"
    ERROR_RBAC_DENY = "error.rbac.denied"
    ERROR_ES_CONNECTION = "error.es.connection"
    ERROR_BAD_INPUT = "error.input.bad"
    ERROR_INVALID_PARAM = "error.input.invalid_param"
    ERROR_SESSION_EXPIRED = "error.pagination.session_expired"
    ERROR_INVALID_PAGE = "error.pagination.invalid_page"
    ERROR_INTERNAL = "error.internal"
    ERROR_INDICES_BAD_CONFIG = "error.indices.bad_config"

    INFO_QUERY_OK = "info.query.ok"
    INFO_ALERTS_OK = "info.alerts.ok"
    INFO_STATS_OK = "info.stats.ok"
    INFO_INDICES_OK = "info.indices.ok"
    INFO_INDICES_CONFIG_OK = "info.indices.config.ok"
    INFO_INDICES_REFRESH_OK = "info.indices.refresh.ok"
