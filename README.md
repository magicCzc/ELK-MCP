<!--
Copyright (c) 2025, elk-MCP Project.
All rights reserved.
-->

# elk-MCP

- 开发者（Author）：Chenzc
- 发布时间（Release Date）：2025-11-16
- 联系方式（Contact）：910445306@qq.com
- 许可证（License）：MIT License（见 `LICENSE`）
- 最新版本（Latest Version）：1.1.0

## 简介
elk-MCP 是日志查询与工作流集成的后端服务，支持基于 Elasticsearch 的多索引查询、字段精简、分页与国际化预留。完全兼容 ES 6.5.4，解决了市面上大多数日志服务最低支持 7.x 的痛点。

## 关键特性
- **ES 6.5.4 兼容性**：兼容 Elasticsearch 6.5.4 查询 DSL，提供 ES6 语法适配器。
- **响应优化**：精简 `_source` 字段返回，避免超长响应导致调用失败；对超长 `message` 进行截断（默认 `MAX_MESSAGE_LEN=4096`）。
- **多种分页方式**：
  - 普通分页（支持任意页码跳转）
  - 游标分页（search_after，支持大数据量深分页）
  - 分页会话管理（稳定的分页体验，简化前端逻辑）
- **Dify 工作流友好**：提供分页循环与时间切片的调用建议，便于集成到工作流中。
- **索引自动发现与管理**：定时扫描 ES 索引，支持正则匹配、关键字匹配和模糊匹配，可动态调整配置。
- **告警与统计功能**：支持告警日志检索、统计分析（按服务、级别、主机分组）。
- **多租户与权限控制**：基于 RBAC 的权限控制，支持多租户隔离；文案采用 i18n key（国际化预留）。
- **监控与指标**：暴露 Prometheus 指标，支持请求计数、延迟监控、索引刷新与匹配等指标。
- **严格安全与性能约束**：不硬编码敏感信息，冷启动 ≤ 2s，单次推理接口 p95 ≤ 800ms。

## 快速开始
1) 安装依赖（后端 Python）
- 使用 `backend/requirements.txt` 安装依赖（请在虚拟环境中执行）：
  - 示例：`pip install -r backend/requirements.txt`
2) 配置环境
- 复制并编辑 `backend/.env.example` 为 `backend/.env`，至少设置：
  - `ES_HOSTS`、`DEFAULT_INDEX`、`TIMESTAMP_FIELD`
  - 响应控制：`MAX_PAGE_SIZE`、`MAX_MESSAGE_LEN`
3) 启动服务
- 运行后端应用（示例）：
  - `python backend/app/main.py`
4) 验证接口
- 访问 `GET /health` 或使用 `POST /api/logs/query` 进行查询。

## 配置项说明（节选）
- `ES_HOSTS`：Elasticsearch 地址（例如 `http://localhost:9200`）。
- `DEFAULT_INDEX`：默认索引或索引模式（如 `logs-*`）。
- `TIMESTAMP_FIELD`：时间字段名（例如 `@timestamp`）。
- `MAX_PAGE_SIZE`：单页最大条数（建议 20，避免响应超 1MB）。
- `MAX_MESSAGE_LEN`：单条消息最大长度（建议 4096 字符）。
- `LOG_DOC_TYPE`：文档类型（ES6 环境通常可留空）。
- 注意：请勿提交 `backend/.env` 到仓库，使用 `.env.example` 作为模板。

## API 用法概览

### 日志查询相关
- `POST /api/logs/query`：查询日志，支持多种过滤条件和排序
  - 请求体关键字段：
    - 时间范围：`time_range`（包含 `start` 和 `end`）
    - 过滤条件：`level`, `service`, `keyword`
    - 分页：`pagination`（包含 `page` 和 `page_size`）
    - 分页模式：`mode`（可选 `page` 或 `cursor`）
  - 响应字段：
    - `total`：匹配总数
    - `items`：日志数组，包含标准化的日志字段
    - `next_cursor_after`：游标分页时的下一页游标

- `POST /api/logs/alerts`：告警日志检索
  - 支持按严重级别和规则过滤

- `POST /api/logs/stats`：统计分析
  - 支持按服务、级别、主机分组

- `POST /api/logs/paginate/init`：初始化分页会话
  - 返回会话ID和总页数

- `POST /api/logs/paginate/get`：获取分页数据
  - 通过会话ID和页码获取数据

### 索引管理相关
- `GET /api/indices/list`：获取索引列表
- `POST /api/indices/config`：更新索引发现配置
- `POST /api/indices/refresh`：手动刷新索引列表

### 监控与健康检查
- `GET /health`：健康检查
- `GET /metrics`：Prometheus 指标暴露

## Dify 工作流集成建议
- 单页测试：先用 `page=1`, `page_size=20` 验证命中与响应大小。
- 分页循环：在工作流中维护 `current_page`，循环请求直到 `current_page * page_size >= total`。
- 时间切片：按小时或固定窗口拆分一天查询，逐片分页遍历，聚合到数组输出。
- 防止超限：如消息较长，保持 `MAX_MESSAGE_LEN=4096`；必要时在工作流里进一步截断展示字符串。

## 分页与响应体控制
- 后端在 ES DSL 中使用 `_source.includes` 仅返回必要字段，减少 JSON 大小。
- 强制分页上限（`MAX_PAGE_SIZE`），并对超长 `message` 进行截断。
- 目标：单次响应远低于 1MB，避免“Text size is too large”。

## 性能与安全约束
- 冷启动 ≤ 2s；单次推理接口 p95 ≤ 800ms。
- 禁止在前端硬编码敏感信息（例如 `OPENAI_API_KEY`）。
- 所有用户输入进行二次校验（后端 `Pydantic`，前端 `zod` 预留）。
- 许可证选择避免 GPL/LGPL 依赖；新增库需说明理由与包大小估算。

## 目录结构（节选）
- `backend/`：后端应用代码
  - `app/`：
    - `alerts/`：告警引擎，用于评估告警规则
    - `es/`：ES 查询适配器、DSL 构造
    - `indexes/`：索引自动发现服务
    - `logs/`：日志归一化与字段截断
    - `metrics/`：Prometheus 指标暴露
    - `models/`：Pydantic 模型与校验
    - `routes/`：HTTP 路由与接口
      - `health.py`：健康检查接口
      - `indices.py`：索引管理接口
      - `logs.py`：日志查询接口
    - `security/`：认证与权限控制
    - `tenancy/`：多租户中间件
    - `utils/`：工具函数
      - `i18n.py`：国际化支持
      - `pagination_session.py`：分页会话管理
    - `config.py`：配置管理
    - `main.py`：应用入口
  - `docs/`：API、部署、架构与运维文档
  - `tests/`：测试文件
- `schemas-ts/`：TypeScript 侧的 schema（Airbnb ESLint 规范）

## 版本更新记录

### 1.1.0 (2025-12-17)
- 新增分页会话管理功能
- 完善 API 文档和架构文档
- 新增操作手册中的分页方式选择建议
- 优化 README.md 项目介绍

### 1.0.0 (2025-11-16)
- 初始版本发布
- 支持 ES 6.5.4 兼容查询
- 提供多种分页方式
- 支持索引自动发现与管理
- 提供告警与统计功能

## 常见问题
- 推送代码失败（认证/网络）：优先使用 SSH 密钥认证；或 HTTPS + PAT。
- 响应过大：减小 `page_size`，保持字段精简，开启消息截断。
- ES 版本差异：本项目针对 ES 6.5.4 做适配，更新 ES 版本时需复核 DSL。
- 索引列表为空：检查 ES 权限是否允许 `/_cat/indices`；适当放宽 `include_patterns`。

## 贡献与联系
- 提交 PR 前请确保不包含私密配置（例如 `backend/.env`）。
- 问题与建议请通过 Issue 或邮件联系：`910445306@qq.com`。

## 许可证
本项目使用 MIT License，详见根目录 `LICENSE` 文件。
