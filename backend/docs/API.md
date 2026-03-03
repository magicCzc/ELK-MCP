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
    - `filters`: `{ level?: string[], service?: string[], keyword?: string, fuzzy_type?: string, fuzzy_options?: object }`
      - `keyword`: 搜索关键词
      - `fuzzy_type`: 模糊匹配类型，可选值：
        - `"contains"` (默认): 包含匹配，使用最佳字段匹配
        - `"prefix"`: 前缀匹配，匹配以关键词开头的日志
        - `"fuzzy"`: 模糊匹配，容忍拼写错误（如 "erorr" 能匹配 "error"）
        - `"wildcard"`: 通配符匹配，支持 `*`（任意字符）和 `?`（单个字符）
        - `"regexp"`: 正则表达式匹配，功能最强但性能最差
      - `fuzzy_options`: 额外配置选项
        - `fuzziness`: 编辑距离（仅 fuzzy 类型），默认 `"AUTO"`
        - `prefix_length`: 前缀长度（仅 fuzzy 类型），默认 `2`
        - `max_expansions`: 最大扩展数（仅 fuzzy 类型），默认 `50`
        - `case_insensitive`: 是否忽略大小写（wildcard/regexp 类型），默认 `true`
    - `sort`: `{ field: "timestamp" | "_score", order: "asc" | "desc" }`
    - `query_string?: string` - Lucene 查询语法支持（可选，与 filters.keyword 互斥）
      - 优先级：query_string > filters.keyword（如果提供 query_string，keyword 被忽略）
      - 支持完整 Lucene 语法：字段过滤、布尔逻辑、范围查询、通配符等
      - 示例：
        - `service:order-service AND level:ERROR`
        - `message:exception AND NOT message:timeout`
        - `status_code:[400 TO 599]`
        - `response_time:>1000 AND service:(order-service OR payment-service)`
    - 动态索引选择与集群精准路由：
      - `index_keyword?: string` 用于按项目/索引名关键字路由到特定 ES 集群（如 "KF1"）。系统会根据 `.env` 中的 `ES_PROJECT_MAP` 配置进行毫秒级精准路由，大幅减少跨集群扫描。
      - `use_regex?: boolean` 关键字作为正则表达式处理（不区分大小写）。
      - `override_indexes?: string[]` 手动指定索引列表。若 `index_keyword` 为空，系统会自动从该列表的首个索引名中识别所属集群，实现自动精准路由。
  - 出参：标准化日志列表与分页元数据。
    - 游标模式附加：`next_cursor_after?: Array<string|number>`，`page_size: number`

### 示例：游标分页（search_after）

**⚠️ 安全提示**：必须提供 `index_keyword` 或 `override_indexes` 明确指定索引，禁止查询所有索引

请求（第一页，未携带游标）：

```json
{
  "tenant_id": "sctv",
  "pagination": { "page": 1, "page_size": 20 },
  "mode": "cursor",
  "time_range": { "start": "2025-11-15T00:00:00Z", "end": "2025-11-16T00:00:00Z" },
  "filters": { "service": ["order-service"], "level": ["ERROR"] },
  "sort": { "field": "timestamp", "order": "desc" },
  "index_keyword": "order",
  "override_indexes": ["kst-logs-order-service-2025.11.15"]
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
  "sort": { "field": "timestamp", "order": "desc" },
  "index_keyword": "order",
  "override_indexes": ["kst-logs-order-service-2025.11.15"]
}
```

### 模糊匹配查询示例

#### 1. 模糊匹配（容忍拼写错误）
适合用户输入可能有错别字的情况：

```json
{
  "tenant_id": "sctv",
  "pagination": { "page": 1, "page_size": 20 },
  "time_range": { "start": "2025-11-15T00:00:00Z", "end": "2025-11-16T00:00:00Z" },
  "filters": {
    "keyword": "erorr",
    "fuzzy_type": "fuzzy",
    "fuzzy_options": { "fuzziness": "AUTO" }
  },
  "index_keyword": "order",
  "override_indexes": ["kst-logs-order-service-2025.11.15"]
}
```

#### 2. 通配符匹配
适合知道部分内容但不确定完整词的情况：

**⚠️ 注意**：前导通配符（如 `*exception`）已被禁止，会自动移除

```json
{
  "tenant_id": "sctv",
  "pagination": { "page": 1, "page_size": 20 },
  "time_range": { "start": "2025-11-15T00:00:00Z", "end": "2025-11-16T00:00:00Z" },
  "filters": {
    "keyword": "exception*",
    "fuzzy_type": "wildcard"
  },
  "index_keyword": "order",
  "override_indexes": ["kst-logs-order-service-2025.11.15"]
}
```

#### 3. 前缀匹配
适合搜索以特定字符串开头的日志：

```json
{
  "tenant_id": "sctv",
  "pagination": { "page": 1, "page_size": 20 },
  "time_range": { "start": "2025-11-15T00:00:00Z", "end": "2025-11-16T00:00:00Z" },
  "filters": {
    "keyword": "connection",
    "fuzzy_type": "prefix"
  },
  "index_keyword": "order",
  "override_indexes": ["kst-logs-order-service-2025.11.15"]
}
```

#### 4. 正则表达式匹配（谨慎使用）
适合复杂模式匹配，但性能较差：

**⚠️ 警告**：正则表达式查询性能最差，建议仅在必要时使用，并严格限制时间范围

```json
{
  "tenant_id": "sctv",
  "pagination": { "page": 1, "page_size": 20 },
  "time_range": { "start": "2025-11-15T00:00:00Z", "end": "2025-11-16T00:00:00Z" },
  "filters": {
    "keyword": "err.*or[0-9]+",
    "fuzzy_type": "regexp",
    "fuzzy_options": { "case_insensitive": true }
  },
  "index_keyword": "order",
  "override_indexes": ["kst-logs-order-service-2025.11.15"]
}
```

### Lucene Query String 查询示例

**⚠️ 安全提示**：所有示例都必须包含 `index_keyword` 或 `override_indexes` 明确指定索引

#### 1. 基本字段过滤
```json
{
  "tenant_id": "sctv",
  "pagination": { "page": 1, "page_size": 20 },
  "time_range": { "start": "2025-11-15T00:00:00Z", "end": "2025-11-16T00:00:00Z" },
  "query_string": "service:order-service AND level:ERROR",
  "index_keyword": "order",
  "override_indexes": ["kst-logs-order-service-2025.11.15"]
}
```

#### 2. 布尔逻辑组合
```json
{
  "tenant_id": "sctv",
  "pagination": { "page": 1, "page_size": 20 },
  "time_range": { "start": "2025-11-15T00:00:00Z", "end": "2025-11-16T00:00:00Z" },
  "query_string": "service:(order-service OR payment-service) AND level:ERROR AND NOT message:timeout",
  "index_keyword": "order",
  "override_indexes": ["kst-logs-order-service-2025.11.15"]
}
```

#### 3. 范围查询
```json
{
  "tenant_id": "sctv",
  "pagination": { "page": 1, "page_size": 20 },
  "time_range": { "start": "2025-11-15T00:00:00Z", "end": "2025-11-16T00:00:00Z" },
  "query_string": "status_code:[400 TO 599] AND response_time:>1000",
  "index_keyword": "order",
  "override_indexes": ["kst-logs-order-service-2025.11.15"]
}
```

#### 4. 通配符和模糊匹配

**⚠️ 注意**：前导通配符（如 `*connect`）已被禁止，会自动移除

```json
{
  "tenant_id": "sctv",
  "pagination": { "page": 1, "page_size": 20 },
  "time_range": { "start": "2025-11-15T00:00:00Z", "end": "2025-11-16T00:00:00Z" },
  "query_string": "message:connect* AND message:erorr~",
  "index_keyword": "order",
  "override_indexes": ["kst-logs-order-service-2025.11.15"]
}
```

#### 5. 字段存在性检查
```json
{
  "tenant_id": "sctv",
  "pagination": { "page": 1, "page_size": 20 },
  "time_range": { "start": "2025-11-15T00:00:00Z", "end": "2025-11-16T00:00:00Z" },
  "query_string": "_exists_:trace_id AND level:ERROR",
  "index_keyword": "order",
  "override_indexes": ["kst-logs-order-service-2025.11.15"]
}
```

## 安全查询规范

### 必须遵守的规则

1. **必须指定索引**：每次查询必须提供 `index_keyword` 或 `override_indexes`，禁止查询所有索引
2. **索引数量限制**：单次查询最多支持 10 个索引，超出部分会被自动截断
3. **禁止前导通配符**：`*keyword` 形式的查询会被自动移除前导通配符
4. **建议时间范围**：建议将时间范围限制在 24 小时内，减少扫描数据量
5. **并发限制**：多集群并发查询最多 3 个线程，防止压垮 ES

### 错误码说明

- `3002` (INVALID_PARAM)：未指定索引或索引无效
- `2001` (ES_CONNECTION)：ES 连接失败或查询超时

## 告警日志检索

- `POST /api/logs/alerts`
  - 入参：
    - `tenant_id`
    - `time_range`
    - `severity?: ("low"|"medium"|"high")[]`
    - `rules?: RuleRef[]`
    - `index_keyword?: string` (用于集群精准路由，**必需**)
    - `override_indexes?: string[]` (明确指定索引列表，**推荐**)
  - 出参：触发告警的日志与告警元数据。
  - **注意**：未指定索引将返回错误

## 统计分析

- `POST /api/logs/stats`
  - 入参：
    - `tenant_id`
    - `time_range`
    - `group_by`: `"service" | "level" | "host"`
    - `index_keyword?: string` (用于集群精准路由)
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
  - 技术实现：采用 Redis 分布式存储（私有端口 63799），支持多进程（Uvicorn multi-workers）状态共享，彻底解决 `error.pagination.session_expired` 问题。
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
