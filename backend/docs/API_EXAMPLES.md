<!--
Copyright (c) 2025, elk-MCP Project.
All rights reserved.
-->

# API 请求示例大全

本文档提供所有 API 接口的完整请求示例，可直接复制使用。

**基础信息：**
- 基础 URL: `http://localhost:8000`
- 认证 Header: `Authorization: Bearer admin-test`
- 租户 Header: `X-Tenant-Id: center`
- Content-Type: `application/json`

---

## 目录

1. [日志查询接口](#1-日志查询接口)
2. [告警查询接口](#2-告警查询接口)
3. [统计分析接口](#3-统计分析接口)
4. [分页会话接口](#4-分页会话接口)
5. [索引管理接口](#5-索引管理接口)
6. [健康检查接口](#6-健康检查接口)

---

## 1. 日志查询接口

### 1.1 基础查询（模糊匹配 - contains）

```bash
curl -X POST http://localhost:8000/api/logs/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer admin-test" \
  -H "X-Tenant-Id: center" \
  -d '{
    "pagination": {"page": 1, "page_size": 20},
    "time_range": {"start": "2026-03-03T02:00:00Z", "end": "2026-03-03T03:00:00Z"},
    "filters": {
      "level": ["ERROR"],
      "service": ["center_web_wechat"],
      "keyword": "Unable to delete",
      "fuzzy_type": "contains"
    },
    "sort": {"field": "@timestamp", "order": "desc"},
    "index_keyword": "center",
    "override_indexes": ["kst-logs-center_web_wechat-2026.03.03"]
  }'
```

### 1.2 前缀匹配（prefix）

```bash
curl -X POST http://localhost:8000/api/logs/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer admin-test" \
  -H "X-Tenant-Id: center" \
  -d '{
    "pagination": {"page": 1, "page_size": 20},
    "time_range": {"start": "2026-03-03T02:00:00Z", "end": "2026-03-03T03:00:00Z"},
    "filters": {
      "level": ["ERROR"],
      "keyword": "Unable",
      "fuzzy_type": "prefix"
    },
    "sort": {"field": "@timestamp", "order": "desc"},
    "index_keyword": "center",
    "override_indexes": ["kst-logs-center_web_wechat-2026.03.03"]
  }'
```

### 1.3 模糊匹配（fuzzy - 容错拼写）

```bash
curl -X POST http://localhost:8000/api/logs/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer admin-test" \
  -H "X-Tenant-Id: center" \
  -d '{
    "pagination": {"page": 1, "page_size": 20},
    "time_range": {"start": "2026-03-03T02:00:00Z", "end": "2026-03-03T03:00:00Z"},
    "filters": {
      "level": ["ERROR"],
      "keyword": "Unabel",
      "fuzzy_type": "fuzzy",
      "fuzzy_options": {
        "fuzziness": "AUTO",
        "prefix_length": 2,
        "max_expansions": 50
      }
    },
    "sort": {"field": "@timestamp", "order": "desc"},
    "index_keyword": "center",
    "override_indexes": ["kst-logs-center_web_wechat-2026.03.03"]
  }'
```

### 1.4 通配符匹配（wildcard）

```bash
curl -X POST http://localhost:8000/api/logs/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer admin-test" \
  -H "X-Tenant-Id: center" \
  -d '{
    "pagination": {"page": 1, "page_size": 20},
    "time_range": {"start": "2026-03-03T02:00:00Z", "end": "2026-03-03T03:00:00Z"},
    "filters": {
      "level": ["ERROR"],
      "keyword": "Unable*delete*",
      "fuzzy_type": "wildcard",
      "fuzzy_options": {
        "case_insensitive": true
      }
    },
    "sort": {"field": "@timestamp", "order": "desc"},
    "index_keyword": "center",
    "override_indexes": ["kst-logs-center_web_wechat-2026.03.03"]
  }'
```

### 1.5 正则表达式匹配（regexp）

```bash
curl -X POST http://localhost:8000/api/logs/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer admin-test" \
  -H "X-Tenant-Id: center" \
  -d '{
    "pagination": {"page": 1, "page_size": 20},
    "time_range": {"start": "2026-03-03T02:00:00Z", "end": "2026-03-03T03:00:00Z"},
    "filters": {
      "level": ["ERROR"],
      "keyword": "Unable.*delete.*jpg",
      "fuzzy_type": "regexp",
      "fuzzy_options": {
        "case_insensitive": true
      }
    },
    "sort": {"field": "@timestamp", "order": "desc"},
    "index_keyword": "center",
    "override_indexes": ["kst-logs-center_web_wechat-2026.03.03"]
  }'
```

### 1.6 Lucene Query String 查询

```bash
curl -X POST http://localhost:8000/api/logs/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer admin-test" \
  -H "X-Tenant-Id: center" \
  -d '{
    "pagination": {"page": 1, "page_size": 20},
    "time_range": {"start": "2026-03-03T02:00:00Z", "end": "2026-03-03T03:00:00Z"},
    "query_string": "loglevel:ERROR AND logmessage:\"Unable to delete\"",
    "sort": {"field": "@timestamp", "order": "desc"},
    "index_keyword": "center",
    "override_indexes": ["kst-logs-center_web_wechat-2026.03.03"]
  }'
```

### 1.7 复杂 Lucene 查询

```bash
curl -X POST http://localhost:8000/api/logs/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer admin-test" \
  -H "X-Tenant-Id: center" \
  -d '{
    "pagination": {"page": 1, "page_size": 20},
    "time_range": {"start": "2026-03-03T02:00:00Z", "end": "2026-03-03T03:00:00Z"},
    "query_string": "loglevel:(ERROR OR WARN) AND (logmessage:\"Unable to delete\" OR logmessage:IOException) AND NOT logmessage:timeout",
    "sort": {"field": "@timestamp", "order": "desc"},
    "index_keyword": "center",
    "override_indexes": ["kst-logs-center_web_wechat-2026.03.03"]
  }'
```

### 1.8 游标分页（大数据量）

**第一页：**
```bash
curl -X POST http://localhost:8000/api/logs/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer admin-test" \
  -H "X-Tenant-Id: center" \
  -d '{
    "pagination": {"page": 1, "page_size": 50},
    "time_range": {"start": "2026-03-03T00:00:00Z", "end": "2026-03-03T23:59:59Z"},
    "filters": {
      "level": ["ERROR"]
    },
    "sort": {"field": "@timestamp", "order": "desc"},
    "mode": "cursor",
    "index_keyword": "center",
    "override_indexes": ["kst-logs-center_web_wechat-2026.03.03"]
  }'
```

**第二页（使用返回的 next_cursor_after）：**
```bash
curl -X POST http://localhost:8000/api/logs/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer admin-test" \
  -H "X-Tenant-Id: center" \
  -d '{
    "pagination": {"page": 1, "page_size": 50},
    "time_range": {"start": "2026-03-03T00:00:00Z", "end": "2026-03-03T23:59:59Z"},
    "filters": {
      "level": ["ERROR"]
    },
    "sort": {"field": "@timestamp", "order": "desc"},
    "mode": "cursor",
    "cursor_after": ["2026-03-03T02:20:18.438Z", "abc123"],
    "index_keyword": "center",
    "override_indexes": ["kst-logs-center_web_wechat-2026.03.03"]
  }'
```

---

## 2. 告警查询接口

### 2.1 基础告警查询

```bash
curl -X POST http://localhost:8000/api/logs/alerts \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer admin-test" \
  -H "X-Tenant-Id: center" \
  -d '{
    "time_range": {"start": "2026-03-03T00:00:00Z", "end": "2026-03-03T23:59:59Z"},
    "severity": ["high", "medium"],
    "query": "Unable to delete",
    "index_keyword": "center",
    "override_indexes": ["kst-logs-center_web_wechat-2026.03.03"]
  }'
```

### 2.2 按规则查询

```bash
curl -X POST http://localhost:8000/api/logs/alerts \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer admin-test" \
  -H "X-Tenant-Id: center" \
  -d '{
    "time_range": {"start": "2026-03-03T00:00:00Z", "end": "2026-03-03T23:59:59Z"},
    "severity": ["high"],
    "rules": [
      {"id": "rule-001", "severity": "high"},
      {"id": "rule-002", "severity": "medium"}
    ],
    "query": "IOException",
    "index_keyword": "center",
    "override_indexes": ["kst-logs-center_web_wechat-2026.03.03"]
  }'
```

---

## 3. 统计分析接口

### 3.1 按级别统计

```bash
curl -X POST http://localhost:8000/api/logs/stats \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer admin-test" \
  -H "X-Tenant-Id: center" \
  -d '{
    "time_range": {"start": "2026-03-03T00:00:00Z", "end": "2026-03-03T23:59:59Z"},
    "group_by": "level",
    "index_keyword": "center",
    "override_indexes": ["kst-logs-center_web_wechat-2026.03.03"]
  }'
```

### 3.2 按服务统计

```bash
curl -X POST http://localhost:8000/api/logs/stats \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer admin-test" \
  -H "X-Tenant-Id: center" \
  -d '{
    "time_range": {"start": "2026-03-03T00:00:00Z", "end": "2026-03-03T23:59:59Z"},
    "group_by": "service",
    "index_keyword": "center",
    "override_indexes": ["kst-logs-center_web_wechat-2026.03.03"]
  }'
```

### 3.3 按主机统计

```bash
curl -X POST http://localhost:8000/api/logs/stats \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer admin-test" \
  -H "X-Tenant-Id: center" \
  -d '{
    "time_range": {"start": "2026-03-03T00:00:00Z", "end": "2026-03-03T23:59:59Z"},
    "group_by": "host",
    "index_keyword": "center",
    "override_indexes": ["kst-logs-center_web_wechat-2026.03.03"]
  }'
```

---

## 4. 分页会话接口

### 4.1 初始化分页会话

```bash
curl -X POST http://localhost:8000/api/logs/paginate/init \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer admin-test" \
  -H "X-Tenant-Id: center" \
  -d '{
    "pagination": {"page": 1, "page_size": 50},
    "time_range": {"start": "2026-03-03T00:00:00Z", "end": "2026-03-03T23:59:59Z"},
    "filters": {
      "level": ["ERROR"],
      "service": ["center_web_wechat"]
    },
    "sort": {"field": "@timestamp", "order": "desc"},
    "index_keyword": "center",
    "override_indexes": ["kst-logs-center_web_wechat-2026.03.03"]
  }'
```

**响应示例：**
```json
{
  "code": 0,
  "i18n_key": "info.query.ok",
  "data": {
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "total_pages": 10,
    "total_items": 481,
    "page_size": 50
  }
}
```

### 4.2 获取分页数据

```bash
curl -X POST http://localhost:8000/api/logs/paginate/get \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer admin-test" \
  -H "X-Tenant-Id: center" \
  -d '{
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "page": 1
  }'
```

### 4.3 获取第二页数据

```bash
curl -X POST http://localhost:8000/api/logs/paginate/get \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer admin-test" \
  -H "X-Tenant-Id: center" \
  -d '{
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "page": 2
  }'
```

---

## 5. 索引管理接口

### 5.1 获取索引列表

```bash
curl -X GET http://localhost:8000/api/indices/list \
  -H "Authorization: Bearer admin-test" \
  -H "X-Tenant-Id: center"
```

### 5.2 更新索引发现配置

```bash
curl -X POST http://localhost:8000/api/indices/config \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer admin-test" \
  -H "X-Tenant-Id: center" \
  -d '{
    "enabled": true,
    "interval_seconds": 300,
    "include_patterns": ["^kst-logs-.*", "^logs-.*"],
    "exclude_patterns": ["^\.kibana.*"]
  }'
```

### 5.3 手动刷新索引列表

```bash
curl -X POST http://localhost:8000/api/indices/refresh \
  -H "Authorization: Bearer admin-test" \
  -H "X-Tenant-Id: center"
```

---

## 6. 健康检查接口

### 6.1 健康检查

```bash
curl -X GET http://localhost:8000/healthz

# 或

curl -X GET http://localhost:8000/health
```

### 6.2 Prometheus 指标

```bash
curl -X GET http://localhost:8000/metrics
```

---

## 附录：常用 Lucene Query String 语法

| 语法 | 说明 | 示例 |
|------|------|------|
| `field:value` | 字段精确匹配 | `loglevel:ERROR` |
| `field:"value"` | 字段短语匹配 | `logmessage:"Unable to delete"` |
| `AND` | 与操作 | `loglevel:ERROR AND service:web` |
| `OR` | 或操作 | `loglevel:ERROR OR loglevel:WARN` |
| `NOT` / `!` | 非操作 | `loglevel:ERROR NOT logmessage:timeout` |
| `*` | 通配符（0或多个字符） | `logmessage:Unable*` |
| `?` | 通配符（单个字符） | `logmessage:err?r` |
| `~` | 模糊匹配 | `logmessage:delete~` |
| `>`, `<`, `>=`, `<=` | 范围比较 | `@timestamp:>2026-03-01` |
| `[a TO b]` | 范围查询 | `@timestamp:[2026-03-01 TO 2026-03-03]` |
| `(a OR b) AND c` | 分组 | `(loglevel:ERROR OR loglevel:WARN) AND service:web` |

---

## 附录：模糊匹配类型说明

| 类型 | 适用场景 | 性能 |
|------|---------|------|
| `contains` | 包含关键词（默认） | ⭐⭐⭐⭐⭐ |
| `prefix` | 前缀匹配 | ⭐⭐⭐⭐⭐ |
| `fuzzy` | 容错拼写错误 | ⭐⭐⭐ |
| `wildcard` | 通配符匹配 | ⭐⭐ |
| `regexp` | 正则表达式 | ⭐ |

---

**文档版本**: 1.2.0  
**最后更新**: 2026-03-03
