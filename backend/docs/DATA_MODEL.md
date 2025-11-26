<!--
Copyright (c) 2025, elk-MCP Project.
All rights reserved.
-->

# 数据模型说明（ES 索引规范）

## 索引命名建议

- 统一前缀：`logs-<tenant>-<service>-<date>` 或与现网保持一致（如 `kst-logs-*`）。
- 关键字族：例如 `kicp` 相关索引需遵循稳定命名，以支持自动匹配。

## 关键字段（建议/常见）

- 时间：`@timestamp`（`date`）
- 级别：`level`（`keyword`，枚举：`debug/info/warn/error`）
- 消息：`message`（`text` + `keyword`）
- 服务/应用：`service`、`app`（`keyword`）
- 环境：`env`（`keyword`，如 `prod/pre/dev`）
- 租户：`tenant_id`（`keyword`）
- 追踪：`trace_id`、`span_id`（`keyword`）
- 主机/模块：`host`、`module`、`logger`、`thread`（`keyword`）
- 异常：`exception`、`stack`、`code`（类型视实际而定）

## 映射建议（ES 6.x）

- 文档类型：`_doc`
- 文本字段双映射：`text` + `keyword`，兼顾搜索与聚合。
- 时间字段：启用 `doc_values`，确保排序与聚合性能。

## 兼容说明

- 本服务构建 ES6 DSL 并适配 `_doc` 类型；更高版本需适配 `_type` 移除与查询语法差异。

## 数据质量与验收

- 完整性：关键字段必须存在；异常字段原样保留以利排障。
- 分布：提供跨索引、跨租户/服务的样本，便于性能与覆盖验证。

