<!--
Copyright (c) 2025, elk-MCP Project.
All rights reserved.
-->

# 安装部署指南

## 前置条件

- Python 3.10+
- 可访问的 Elasticsearch 6.5.4 集群
- 可选：Prometheus 用于指标采集

## 安装

1. `pip install -r backend/requirements.txt`
2. 复制 `.env.example` 为 `.env`，填写 ES 地址与认证信息。
3. 启动服务：
   - `uvicorn app.main:app --host 0.0.0.0 --port 8080`

## 配置项（.env）
- `TIMESTAMP_FIELD`：时间戳字段，建议 `@timestamp`。
- `LOG_DOC_TYPE`：留空表示不按类型路径搜索（与 `/{index}/_search` 一致）。
- `MAX_PAGE_SIZE`：单页最大条数，默认 20。
- `MAX_MESSAGE_LEN`：单条日志消息最大长度，默认 4096。
- `DEBUG_QUERY_LOGS`：开发调试开关。

- `ES_HOSTS`: 逗号分隔的 ES 地址
- `ES_USERNAME`/`ES_PASSWORD`: 基本认证
- `LOG_INDEXES`: 查询索引通配（如 `logs-*`）
- `LOG_DOC_TYPE`: ES6 类型（默认 `_doc`）
- `CACHE_*`: 缓存开关、TTL、最大容量
- `RBAC_CONFIG_PATH`: RBAC 配置文件路径
- `METRICS_ENABLED`: 是否启用 `/metrics`

## 运行与监控

- 健康检查：`GET /healthz`
- 指标暴露：`GET /metrics`

## 常见问题

- 如果索引存在不同类型（`type`），需在 `.env` 中设置对应 `LOG_DOC_TYPE`。
- 若 ES 连接超时，请检查网络与认证配置，或调大客户端超时。