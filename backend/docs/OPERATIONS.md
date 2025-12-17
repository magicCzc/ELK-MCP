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

## 游标分页工作流示例（search_after）

- 场景：深分页或大数据量遍历，避免 `from + size` 带来的性能与一致性问题。
- 关键点：排序字段保持稳定（推荐时间字段，如 `timestamp/@timestamp`），且整个循环参数不变。

### 步骤
- 初始化：`cursor_after = null`，`page_size = 20`，`all_items = []`
- 循环：
  - `POST /api/logs/query`，携带 `mode = "cursor"`；若 `cursor_after` 有值则一并传入。
  - 累加返回的 `items` 到 `all_items`。
  - 读取 `data.next_cursor_after`，若为空则结束；否则更新 `cursor_after` 继续下一轮。

### 示例请求（第一页）

```json
{
  "tenant_id": "sctv",
  "pagination": { "page": 1, "page_size": 20 },
  "mode": "cursor",
  "time_range": { "start": "2025-11-15T00:00:00Z", "end": "2025-11-16T00:00:00Z" },
  "filters": { "service": ["order-service"], "level": ["ERROR"] },
  "sort": { "field": "timestamp", "order": "desc" }
}
```

### 示例响应（节选）

```json
{
  "code": 0,
  "i18n_key": "info.query.ok",
  "data": {
    "total": 142,
    "items": [ /* 标准化日志 */ ],
    "next_cursor_after": ["2025-11-15T08:43:10Z", "abc123"],
    "page_size": 20
  }
}
```

### 第二页请求（携带上一页的游标）

```json
{
  "tenant_id": "sctv",
  "pagination": { "page": 1, "page_size": 20 },
  "mode": "cursor",
  "cursor_after": ["2025-11-15T08:43:10Z", "abc123"],
  "time_range": { "start": "2025-11-15T00:00:00Z", "end": "2025-11-16T00:00:00Z" },
  "filters": { "service": ["order-service"], "level": ["ERROR"] },
  "sort": { "field": "timestamp", "order": "desc" }
}
```

### 注意事项
- 排序字段：后端始终加入 `"_id"` 作为第二排序键，保证游标稳定性；建议主排序用时间字段。
- 参数一致性：游标分页仅支持“向后遍历”，循环中应保持 `tenant_id/time_range/filters/sort/page_size` 不变。
- 响应体大小：仍受 `MAX_PAGE_SIZE` 与字段精简控制，避免超过 1MB 限制。

### 伪码（JavaScript/TypeScript）

```ts
let cursorAfter: (string | number)[] | null = null;
const pageSize = 20;
const allItems: any[] = [];

while (true) {
  const req = {
    tenant_id: "sctv",
    pagination: { page: 1, page_size: pageSize },
    mode: "cursor",
    time_range: { start: "2025-11-15T00:00:00Z", end: "2025-11-16T00:00:00Z" },
    filters: { service: ["order-service"], level: ["ERROR"] },
    sort: { field: "timestamp", order: "desc" },
    ...(cursorAfter ? { cursor_after: cursorAfter } : {}),
  };

  const resp = await httpPost("/api/logs/query", req);
  if (resp.code !== 0) throw new Error(resp.i18n_key);

  allItems.push(...resp.data.items);
  const next = resp.data.next_cursor_after;
  if (!next || next.length === 0) break;
  cursorAfter = next;
}

// allItems 即为完整结果集（可按需分批处理或写入存储）
```

## 分页会话管理工作流示例

- 场景：需要稳定的分页体验，或前端需要简化逻辑，只维护会话ID和当前页码。
- 关键点：会话有效期内，查询条件保持不变，分页结果更稳定。

### 步骤
1. 初始化分页会话，获取总页数和会话ID
2. 循环获取每页数据，直到获取完所有页数
3. 根据需要清理会话（可选）

### 示例请求 1：初始化分页会话

```json
{
  "tenant_id": "sctv",
  "pagination": { "page": 1, "page_size": 20 },
  "time_range": { "start": "2025-11-15T00:00:00Z", "end": "2025-11-16T00:00:00Z" },
  "filters": { "service": ["order-service"], "level": ["ERROR"] },
  "sort": { "field": "timestamp", "order": "desc" }
}
```

### 示例响应 1：分页会话初始化成功

```json
{
  "code": 0,
  "i18n_key": "info.query.ok",
  "data": {
    "session_id": "uuid-1234-5678-90ab-cdef",
    "total_pages": 8,
    "total_items": 142,
    "page_size": 20
  }
}
```

### 示例请求 2：获取第一页数据

```json
{
  "session_id": "uuid-1234-5678-90ab-cdef",
  "page": 1
}
```

### 示例响应 2：第一页数据

```json
{
  "code": 0,
  "i18n_key": "info.query.ok",
  "data": {
    "items": [ /* 标准化日志 */ ],
    "current_page": 1,
    "total_pages": 8
  }
}
```

### 示例请求 3：获取第二页数据

```json
{
  "session_id": "uuid-1234-5678-90ab-cdef",
  "page": 2
}
```

### 注意事项
- 会话有效期：默认1小时过期，过期后需重新初始化
- 页码范围：页码必须在1到总页数之间，否则返回错误
- 查询条件：会话有效期内，查询条件保持不变，无法修改
- 会话清理：过期会话会自动清理，无需手动处理

### 伪码（JavaScript/TypeScript）

```ts
// 初始化分页会话
const initReq = {
  tenant_id: "sctv",
  pagination: { page: 1, page_size: 20 },
  time_range: { start: "2025-11-15T00:00:00Z", end: "2025-11-16T00:00:00Z" },
  filters: { service: ["order-service"], level: ["ERROR"] },
  sort: { field: "timestamp", order: "desc" }
};

const initResp = await httpPost("/api/logs/paginate/init", initReq);
if (initResp.code !== 0) throw new Error(initResp.i18n_key);

const { session_id, total_pages } = initResp.data;
const allItems: any[] = [];

// 循环获取所有页数据
for (let page = 1; page <= total_pages; page++) {
  const pageReq = {
    session_id,
    page
  };

  const pageResp = await httpPost("/api/logs/paginate/get", pageReq);
  if (pageResp.code !== 0) throw new Error(pageResp.i18n_key);

  allItems.push(...pageResp.data.items);
}

// allItems 即为完整结果集
```

## 分页方式选择建议

| 分页方式 | 适用场景 | 优点 | 缺点 |
|---------|---------|------|------|
| 普通分页（page） | 小数据量，需要跳转到任意页码 | 简单易用，支持任意页码跳转 | 大数据量时性能下降，深分页可能不准确 |
| 游标分页（cursor） | 大数据量，只需要顺序遍历 | 性能好，结果准确，支持深分页 | 不支持跳转到任意页码，只支持向后遍历 |
| 分页会话管理 | 需要稳定的分页体验，前端逻辑简化 | 会话有效期内结果稳定，前端逻辑简单 | 会话有有效期，需要额外的初始化步骤 |

### 选择建议
1. 对于数据量较小（<1000条）的查询，推荐使用普通分页
2. 对于数据量较大（>1000条）的查询，推荐使用游标分页或分页会话管理
3. 如果前端需要简化逻辑，只维护会话ID和当前页码，推荐使用分页会话管理
4. 如果需要稳定的分页体验，会话有效期内结果不变，推荐使用分页会话管理

