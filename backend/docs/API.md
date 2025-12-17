<!--
Copyright (c) 2025, elk-MCP Project.
All rights reserved.
-->

# API

## /api/logs/query
  - 入参（见 zod 与 Pydantic）：
    - `tenant_id` string
    - `pagination`: `{ page: number, page_size: number }`
    - `mode`: `'page' | 'cursor'`（默认 `'page'`）
    - `cursor_after?`: `Array<string|number>`（游标模式下，传上一页最后一条的 `sort` 值）
    - `time_range`: `{ start: string(ISO), end: string(ISO) }`
    - `filters`: `{ level?: string[], service?: string[], keyword?: string }`
    - `sort`: `{ field: "timestamp" | "_score", order: "asc" | "desc" }`
    - 动态索引选择：
      - `index_keyword?: string` 用于按索引名关键字动态匹配（如 "sctv"）
      - `use_regex?: boolean` 关键字作为正则表达式处理（不区分大小写）
      - `override_indexes?: string[]` 手动指定索引列表，优先级最高
  - 出参：标准化日志列表与分页元数据。
    - 游标模式附加：`next_cursor_after?: Array<string|number>`，`page_size: number`

### 示例：游标分页（search_after）

请求（第一页，未携带游标）：

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

响应（节选）：

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

第二页请求（携带上一页游标）：

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

## 告警日志检索

- `POST /api/logs/alerts`
  - 入参：
    - `tenant_id`
    - `time_range`
    - `severity?: ("low"|"medium"|"high")[]`
    - `rules?: RuleRef[]`
  - 出参：触发告警的日志与告警元数据。

## 统计分析

- `POST /api/logs/stats`
  - 入参：
    - `tenant_id`
    - `time_range`
    - `group_by`: `"service" | "level" | "host"`
  - 出参：聚合桶与计数。

## 分页会话管理

### 初始化分页会话

- `POST /api/logs/paginate/init`
  - 功能：创建分页会话，返回分页ID和总页数，不返回实际数据
  - 入参：与普通查询相同
    - `tenant_id`
    - `pagination`: `{ page: number, page_size: number }`
    - `time_range`: `{ start: string(ISO), end: string(ISO) }`
    - `filters`: `{ level?: string[], service?: string[], keyword?: string }`
    - `sort`: `{ field: "timestamp" | "_score", order: "asc" | "desc" }`
    - 动态索引选择：`index_keyword`, `use_regex`, `override_indexes`
  - 出参：
    ```json
    {
      "code": 0,
      "i18n_key": "info.query.ok",
      "data": {
        "session_id": "string",
        "total_pages": number,
        "total_items": number,
        "page_size": number
      }
    }
    ```

### 获取分页数据

- `POST /api/logs/paginate/get`
  - 功能：通过分页ID和页码获取对应页的详细数据
  - 入参：
    ```json
    {
      "session_id": "string",
      "page": number
    }
    ```
  - 出参：
    ```json
    {
      "code": 0,
      "i18n_key": "info.query.ok",
      "data": {
        "items": [ /* 标准化日志 */ ],
        "current_page": number,
        "total_pages": number
      }
    }
    ```
  - 会话过期：默认1小时过期，过期后需重新初始化
  - 容错：页码超出范围时返回错误码

### 使用场景

1. **大量数据查询**：当查询结果非常大时，使用分页会话可以避免一次性加载过多数据
2. **稳定的分页体验**：会话有效期内，查询条件保持不变，分页结果更稳定
3. **降低ES负载**：通过会话缓存查询条件，减少重复构建ES DSL的开销
4. **简化前端逻辑**：前端只需维护会话ID和当前页码，无需重复传递复杂查询条件

## 健康与指标

- `GET /healthz`: 返回服务健康状态与依赖连通性。
- `GET /metrics`: Prometheus 指标暴露。

## 索引自动发现与管理

- `GET /api/indices/list`
  - 返回：`{ items: string[], status: { last_refresh_ts: number, enabled: boolean } }`

- `POST /api/indices/config`
  - 入参：`{ enabled?: boolean, interval_seconds?: number(5-3600), include_patterns?: string[], exclude_patterns?: string[] }`
  - 说明：无需修改 `.env`，动态调整索引发现配置。

- `POST /api/indices/refresh`
  - 说明：手动触发一次全量刷新。

### 运行时行为与容错

- 实时扫描：通过后台线程按 `interval_seconds` 周期拉取 `/_cat/indices` 并缓存。
- 匹配机制：支持正则与关键字匹配；无命中时自动进行模糊匹配（大小写不敏感）。
- 并行与降级：多集群并发查询；当索引过多或查询超时，自动缩减索引列表并重试。
- 监控与指标：
  - `mcp_index_refresh_total` 刷新次数
  - `mcp_index_count` 当前缓存索引数
  - `mcp_index_match_ratio` 索引匹配成功率（匹配数/缓存数）
  - `mcp_es_backend_latency_ms` ES后端延迟
  - `mcp_request_latency_ms` API延迟

### 变更记录（操作留痕）

- 新增：索引发现服务（后台刷新、缓存、命名校验、容错与日志）。
- 新增：`/api/indices` 路由（list/config/refresh）。
- 新增：日志查询动态索引选择字段（`index_keyword/use_regex/override_indexes`）。
- 新增：Prometheus 指标（索引刷新次数、索引总数、匹配成功率）。
- 修改：`/api/logs/query` 支持索引过多时自动降级查询与重试。

## 错误码与 i18n keys

- 认证失败：`error.auth.invalid_token`（HTTP 401）
- 租户缺失：`error.tenant.missing`（HTTP 400）
- RBAC 拒绝：`error.rbac.denied`（HTTP 200，`code` 非 0）
- ES 连接异常：`error.es.connection`
- 输入不合法：`error.input.bad` 或 HTTP 422（Pydantic 校验失败）
- 索引配置错误：`error.indices.bad_config`

## 认证与权限

- 通过 `Authorization: Bearer <token>` 与 `X-Tenant-Id` 控制访问。
- RBAC 基于配置文件与请求上下文进行资源与动作校验。

## ES 6.5.4 适配说明

- 支持 `doc_type` 与旧版 endpoint 参数；查询 DSL 在转换层进行差异处理。
- 聚合与查询语法适配详见 `app/es/query_adapter.py`。

## 响应体大小与分页建议
- The node has ~1MB text cap; keep single response lightweight.
- Backend returns only necessary fields via `_source.includes`.
- Recommended `page_size=20`; iterate pages `page=1..N` for a day.
- Long messages are truncated server-side (`MAX_MESSAGE_LEN`, default 4096).
- For heavy volumes, slice time windows (hourly) then paginate.
