<!--
Copyright (c) 2025, elk-MCP Project.
All rights reserved.
-->

# elk-MCP

- 开发者（Author）：Chenzc
- 发布时间（Release Date）：2025-11-16
- 联系方式（Contact）：910445306@qq.com
- 许可证（License）：MIT License（见 `LICENSE`）

## 简介
elk-MCP 是日志查询与工作流集成的后端服务，支持基于 Elasticsearch 的多索引查询、字段精简、分页与国际化预留。完全兼容 ES 6.5.4.市面上的版本都是最低支持7.x

## 关键特性
- 兼容 Elasticsearch 6.5.4 查询 DSL（ES6 语法适配器）。
- 精简 `_source` 字段返回，避免超长响应导致调用失败。
- 分页上限与消息长度截断（默认 `MAX_PAGE_SIZE=20`, `MAX_MESSAGE_LEN=4096`）。
- Dify 工作流友好：提供分页循环与时间切片的调用建议。
- 多租户与权限控制预留；文案采用 i18n key（国际化预留）。
- 严格安全与性能约束（不硬编码敏感信息，冷启动与 p95 时延目标）。

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
- 路由：`POST /api/logs/query`
- 请求体（关键字段）：
  - 时间范围：`start_time`, `end_time`
  - 过滤条件：`level`, `service`, `query_string`
  - 分页：`page`, `page_size`（会被后端上限保护为 `MAX_PAGE_SIZE`）
- 响应字段（精简版）：
  - `hits`：数组，包含 `_id`, `@timestamp`, `level`, `service`, `message`（可能被截断）
  - `total`：匹配总数
  - `page`, `page_size`：分页信息

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
- `backend/app/`：后端应用代码
  - `es/`：ES 查询适配器、DSL 构造
  - `logs/`：日志归一化与字段截断
  - `routes/`：HTTP 路由与接口
  - `models/`：Pydantic 模型与校验
- `backend/docs/`：API、部署、架构与运维文档
- `schemas-ts/`：TypeScript 侧的 schema（Airbnb ESLint 规范）

## 常见问题
- 推送代码失败（认证/网络）：优先使用 SSH 密钥认证；或 HTTPS + PAT。
- 响应过大：减小 `page_size`，保持字段精简，开启消息截断。
- ES 版本差异：本项目针对 ES 6.5.4 做适配，更新 ES 版本时需复核 DSL。

## 许可证
本项目使用 MIT License，详见根目录 `LICENSE` 文件。
<<<<<<< HEAD
=======

## 贡献与联系
- 提交 PR 前请确保不包含私密配置（例如 `backend/.env`）。
- 问题与建议请通过 Issue 或邮件联系：`910445306@qq.com`。
>>>>>>> 4584537 (docs: 更新README文档以包含详细配置和使用说明)
