<!--
Copyright (c) 2025, elk-MCP Project.
All rights reserved.
-->

# Backend

- 目标：兼容 Elasticsearch 6.5.4，提供 Dify 标准接口，支持多租户、权限控制、告警与统计。
- 语言：后端 Python (FastAPI + Pydantic)，前端校验提供 TypeScript zod schema。

## 特性概览

- 完全兼容 ES 6.5.4 API（包含 `doc_type`/聚合与查询差异适配）
- 日志采集标准化、缓存优化、权限与多租户隔离
- Dify 集成接口：日志查询、告警检索、统计分析
- 告警触发、上下文提取、AI预处理模块
- 监控指标暴露（Prometheus）、安全审计日志

## 依赖与许可说明

- Python 依赖：
  - `fastapi`（高性能API框架，~3.5MB，Apache-2.0）
  - `uvicorn[standard]`（ASGI服务器，~4.5MB，BSD/MIT混合）
  - `pydantic`（输入校验，~5.0MB，MIT）
  - `httpx`（HTTP客户端，支持连接池与超时，~1.5MB，BSD-3-Clause）
  - `prometheus_client`（指标暴露，~0.5MB，Apache-2.0）

- 不引入 GPL/LGPL；所有依赖均为宽松许可（Apache/MIT/BSD）。

## 性能目标与策略

- 冷启动 ≤ 2s：延迟初始化 ES 客户端、精简依赖、按需加载。
- 查询 P99 < 500ms：缓存命中、连接池、尽量使用 `filter` 语义并避免脚本。
- 100+ 并发查询：ASGI（async）+ 连接池 + 无共享锁设计。

## 安全与国际化

- 所有输入经 Pydantic 校验；提供 zod schema 供前端二次校验。
- 不在前端泄露 `OPENAI_API_KEY` 等敏感信息。
- 错误与文案使用 i18n key，不硬编码中文。

## 快速开始

1. 安装依赖：`pip install -r backend/requirements.txt`
2. 配置环境：复制 `.env.example` 为 `.env` 并填写 ES 信息。
3. 启动服务：`uvicorn app.main:app --host 0.0.0.0 --port 8080`
4. 访问文档：`http://localhost:8080/docs`
5. 指标：`/metrics`；健康检查：`/healthz`

## 目录结构

```
backend/
  app/
    main.py
    config.py
    utils/
      i18n.py
      error_codes.py
    es/
      client.py
      query_adapter.py
    models/
      schemas.py
    security/
      auth.py
    tenancy/
      middleware.py
    logs/
      normalizer.py
    alerts/
      engine.py
    metrics/
      metrics.py
    routes/
      logs.py
      health.py
  docs/
    API.md
    DEPLOYMENT.md
    BENCHMARK.md
  requirements.txt
  .env.example
```

## Dify 集成

- 标准接口：
  - `POST /api/logs/query`（分页/过滤/时间范围）
  - `POST /api/logs/alerts`（告警日志检索）
  - `POST /api/logs/stats`（统计分析）

详见 `docs/API.md` 与 `schemas-ts/src/schemas.ts`。

## 版本适配说明

- 通过 HTTP 适配层在首次请求时检测 ES 版本（`GET /`），自动选择 6.x 路径（包含 `doc_type`）或 7.x/8.x 路径（省略 `doc_type`）。
- 最低支持 6.5.4，最高版本不限；适配层仅使用通用 REST 端点（`_search`/`_doc`），不影响低版本操作。

## Author & Release
- Author: Chenzc
- Release Date: 2025-11-16
- Contact: 910445306@qq.com

## License
- MIT License (see root `LICENSE`)