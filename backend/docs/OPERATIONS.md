<!--
Copyright (c) 2025, elk-MCP Project.
All rights reserved.
-->

# 操作手册（MVP 验收版）

## 安装与启动

- 依赖环境：`Python 3.11+`、可访问的 Elasticsearch（建议 ES 6.5.x 兼容）。
- 安装依赖：
  - `pip install -r backend/requirements.txt`
- 配置环境（`backend/.env`）：
  - `ES_HOSTS`: 例如 `http://localhost:9200`
  - `ES_USERNAME`, `ES_PASSWORD`: 后端连接 ES 的账户（非用户登录）
  - `LOG_INDEXES`: 默认基础索引前缀，示例 `logs-*`
  - `LOG_DOC_TYPE`: ES 6.x 的 `_type`（默认 `_doc`）
  - 索引自动发现相关：`INDEX_DISCOVERY_ENABLED`、`INDEX_DISCOVERY_INTERVAL_SECONDS`、`INDEX_INCLUDE_PATTERNS`、`INDEX_EXCLUDE_PATTERNS`
- 启动服务：
  - `uvicorn app.main:app --host 127.0.0.1 --port 8080`

## 认证与权限

- 所有业务接口需要请求头：
  - `Authorization: Bearer <token>`（示例：`admin-test`、`viewer-test`）
  - `X-Tenant-Id: default`
- 角色说明：
  - `admin-*`：管理与读取权限（索引配置、刷新、查询）
  - `viewer-*`：读取权限（索引列表、查询）

## 核心功能使用流程

1. 健康检查
   - `GET /healthz`
   - 期望返回：`i18n_key=info.health.ok`

2. 索引管理
   - 列表：`GET /api/indices/list`
     - 返回：`i18n_key=info.indices.ok`，`data.items`为缓存索引，`data.status`含 `last_refresh_ts`、`enabled`
   - 更新配置：`POST /api/indices/config`
     - 入参：`enabled`、`interval_seconds`、`include_patterns`、`exclude_patterns`
     - 返回：`i18n_key=info.indices.config.ok`
   - 手动刷新：`POST /api/indices/refresh`
     - 返回：`i18n_key=info.indices.refresh.ok`

3. 日志查询（动态索引选择）
   - `POST /api/logs/query`
   - 关键入参：
     - `tenant_id`、`pagination`、`time_range`、`filters`、`sort`
     - 动态索引选择：`index_keyword`（可配合`use_regex`）或 `override_indexes`
   - 期望返回：`i18n_key=info.query.ok`，`data.total`、`data.items`

## 异常与边界测试建议

- 无认证头：返回 `error.auth.invalid_token`（HTTP 401）
- 无租户头：返回 `error.tenant.missing`（HTTP 400）
- 参数错误（Pydantic 校验失败）：返回 HTTP 422
- 后端 ES 连接失败：返回 `error.es.connection`
- 索引过多：自动限制至 200，失败降级至 50 重试

## 流程图（ASCII）

```
Client -> API (FastAPI)
  -> AuthZ (Bearer + Tenant) -> RBAC
  -> Route: /api/logs/query
     -> IndexDiscovery (cache & match by keyword/regex)
     -> ES Client (single or multi-host)
     -> Normalize hits -> Response (i18n key)

Route: /api/indices/*
  -> AuthZ + RBAC
  -> list/config/refresh -> IndexDiscovery cache & status
```

## 常见问题排查

- 收到 `error.auth.invalid_token`：确认带 `Authorization: Bearer <token>` 且前缀大小写正确。
- 收到 `error.tenant.missing`：补充 `X-Tenant-Id`。
- 查询无结果但无报错：检查 `index_keyword` 是否命中真实索引；可尝试 `use_regex=true` 或提供 `override_indexes`。
- 索引列表为空：检查 ES 权限是否允许 `/_cat/indices`；适当放宽 `include_patterns`。
- 性能观测：访问 `/metrics`，关注 `mcp_request_latency_ms` 与 `mcp_es_backend_latency_ms`。

## 验收说明

- p95 延迟 ≤ 800 ms（接口与后端指标联合观测）。
- 无严重缺陷：异常路径均可返回规范化 i18n 错误码；失败具备降级与重试。

