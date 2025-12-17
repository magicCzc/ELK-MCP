<!--
Copyright (c) 2025, elk-MCP Project.
All rights reserved.
-->

# 系统架构说明（MVP）

## 组件概览

- **FastAPI 应用**：路由与控制层，提供 RESTful API（`/api/logs`, `/api/indices`, `/healthz`, `/metrics`）
- **认证与权限**：
  - `authz`：基于 HTTP 头的认证校验
  - `RBAC`：基于令牌前缀的角色访问控制
- **索引自动发现**：`IndexDiscoveryService`，负责定时拉取 ES 索引列表、缓存和匹配
- **ES 客户端**：
  - 单机/多机 HTTP 客户端
  - 支持连接池、认证、超时配置
  - 支持 ES 6.5.4 兼容查询
- **分页会话管理**：`PaginationSessionManager`，负责创建和管理分页会话
- **日志处理**：
  - `query_adapter`：构建 ES 6.x 兼容的查询 DSL
  - `normalizer`：标准化 ES 查询结果
- **告警引擎**：`evaluate_alerts`，基于规则评估告警
- **监控指标**：Prometheus 指标暴露，包括请求计数、延迟、索引刷新与匹配

## 数据流与流程图（ASCII）

### 1. 日志查询流程

```
[Client]
  -> HTTP (Bearer token + X-Tenant-Id)
  -> FastAPI Router
      -> authz (headers) -> RBAC (role by token prefix)
      -> logs.query
          -> build ES6 DSL (query_adapter.py)
          -> IndexDiscoveryService.find_indices(keyword/regex/fuzzy)
          -> ESHttpClient.search_logs (single or multi)
          -> normalizer.normalize (logs/normalizer.py)
          -> return { code, i18n_key, data }
```

### 2. 分页会话流程

```
[Client]
  -> POST /api/logs/paginate/init
      -> build ES6 DSL with size=0 (only get total)
      -> IndexDiscoveryService.find_indices()
      -> ESHttpClient.search_logs()
      -> calculate total_pages
      -> PaginationSessionManager.create_session()
      -> return session metadata
  
  -> POST /api/logs/paginate/get
      -> PaginationSessionManager.get_session()
      -> validate session and page
      -> build ES6 DSL with cached query_params
      -> IndexDiscoveryService.find_indices()
      -> ESHttpClient.search_logs()
      -> normalizer.normalize()
      -> return paginated data
```

### 3. 索引管理流程

```
[Client]
  -> GET /api/indices/list
      -> IndexDiscoveryService.get_indices()
      -> return cache + status
  
  -> POST /api/indices/config
      -> IndexDiscoveryService.update_config()
      -> return updated config
  
  -> POST /api/indices/refresh
      -> IndexDiscoveryService.refresh_indices()
      -> return refresh status
```

### 4. 后台索引发现流程

```
[Background Thread]
  ->定时执行（interval_seconds）
  -> IndexDiscoveryService.refresh_indices()
      -> HTTP GET /_cat/indices
      -> parse indices list
      -> apply include/exclude patterns
      -> update cache
      -> update metrics
```

[Metrics]
  -> REQUESTS_TOTAL, REQUEST_LATENCY, ES_BACKEND_LATENCY
  -> INDEX_REFRESH_TOTAL, INDEX_COUNT_GAUGE, INDEX_MATCH_RATIO
  -> ES_BACKEND_LATENCY (ES 查询延迟)

## 容错与降级策略

- 多 ES 主机：并发查询聚合；单主机：直接查询。
- 索引数量过多：限制最多 200；失败重试降级至 50。
- ES 连接异常：返回 `error.es.connection`；不中断其他路由。
- 审计写入失败：不影响 API 响应（best-effort）。

## 安全策略（MVP）

- 不支持用户名/密码登录换令牌；令牌为约定前缀字符串（`admin-*`/`viewer-*`）。
- 禁止将 `OPENAI_API_KEY` 暴露到前端；此项目不涉及前端密钥。
- 所有用户输入经 Pydantic 校验（后端）；前端使用 zod（预留）。

