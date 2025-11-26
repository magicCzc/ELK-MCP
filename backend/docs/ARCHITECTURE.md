<!--
Copyright (c) 2025, elk-MCP Project.
All rights reserved.
-->

# 系统架构说明（MVP）

## 组件概览

- `FastAPI` 应用：路由与控制层（`/api/logs`, `/api/indices`, `/healthz`）
- 认证与权限：`authz`（头校验）、`RBAC`（内存规则，按令牌前缀）
- 索引自动发现：`IndexDiscoveryService`（定时`/_cat/indices`、缓存、匹配）
- ES 客户端：单机/多机 HTTP 客户端（连接池、认证、超时）
- 监控指标：Prometheus（请求总量、延迟、索引刷新与匹配）

## 数据流与流程图（ASCII）

```
[Client]
  -> HTTP (Bearer token + X-Tenant-Id)
  -> FastAPI Router
      -> authz (headers) -> RBAC (role by token prefix)
      -> logs.query
          -> build ES6 DSL
          -> IndexDiscoveryService.find_indices(keyword/regex/fuzzy)
          -> ESHttpClient.search_logs (single or multi)
          -> normalize hits -> return { code, i18n_key, data }

      -> indices.list/config/refresh
          -> IndexDiscoveryService.get/update/refresh
          -> return cache + status

[Metrics]
  -> REQUESTS_TOTAL, REQUEST_LATENCY, ES_BACKEND_LATENCY
  -> INDEX_REFRESH_TOTAL, INDEX_COUNT_GAUGE, INDEX_MATCH_RATIO
```

## 容错与降级策略

- 多 ES 主机：并发查询聚合；单主机：直接查询。
- 索引数量过多：限制最多 200；失败重试降级至 50。
- ES 连接异常：返回 `error.es.connection`；不中断其他路由。
- 审计写入失败：不影响 API 响应（best-effort）。

## 安全策略（MVP）

- 不支持用户名/密码登录换令牌；令牌为约定前缀字符串（`admin-*`/`viewer-*`）。
- 禁止将 `OPENAI_API_KEY` 暴露到前端；此项目不涉及前端密钥。
- 所有用户输入经 Pydantic 校验（后端）；前端使用 zod（预留）。

