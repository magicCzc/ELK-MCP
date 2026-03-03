"""
Copyright (c) 2025, elk-MCP Project.
All rights reserved.
"""

"""
文件功能：query_string 查询功能的单元测试
主要类/函数：测试 Lucene query_string 语法支持
作者：系统自动生成
创建时间：2026-02-25
最后修改：2026-02-25
"""

import pytest
from app.es.query_adapter import adapt_query_to_es6


class TestQueryStringSupport:
    """测试 query_string 查询支持"""

    def test_query_string_basic(self):
        """测试基本的 query_string 查询"""
        payload = {
            "tenant_id": "test",
            "pagination": {"page": 1, "page_size": 10},
            "time_range": {"start": "2025-01-01T00:00:00Z", "end": "2025-01-02T00:00:00Z"},
            "query_string": "service:order-service AND level:ERROR"
        }
        
        result = adapt_query_to_es6(payload)
        
        # 验证 query_string 被正确添加到 must 中
        assert "query" in result
        assert "bool" in result["query"]
        assert "must" in result["query"]["bool"]
        
        must_clauses = result["query"]["bool"]["must"]
        query_string_clause = None
        for clause in must_clauses:
            if "query_string" in clause:
                query_string_clause = clause
                break
        
        assert query_string_clause is not None
        assert query_string_clause["query_string"]["query"] == "service:order-service AND level:ERROR"
        assert query_string_clause["query_string"]["default_operator"] == "AND"

    def test_query_string_with_filters(self):
        """测试 query_string 与 filters 共存时，query_string 优先级更高"""
        payload = {
            "tenant_id": "test",
            "pagination": {"page": 1, "page_size": 10},
            "time_range": {"start": "2025-01-01T00:00:00Z", "end": "2025-01-02T00:00:00Z"},
            "filters": {
                "keyword": "this_should_be_ignored",
                "level": ["ERROR"]
            },
            "query_string": "service:payment-service"
        }
        
        result = adapt_query_to_es6(payload)
        
        must_clauses = result["query"]["bool"]["must"]
        
        # 应该只有 query_string，没有 keyword 的 multi_match
        query_string_found = False
        keyword_found = False
        
        for clause in must_clauses:
            if "query_string" in clause:
                query_string_found = True
            if "multi_match" in clause:
                keyword_found = True
        
        assert query_string_found is True
        assert keyword_found is False  # keyword 应该被忽略

    def test_query_string_empty_uses_keyword(self):
        """测试 query_string 为空时使用 keyword"""
        payload = {
            "tenant_id": "test",
            "pagination": {"page": 1, "page_size": 10},
            "time_range": {"start": "2025-01-01T00:00:00Z", "end": "2025-01-02T00:00:00Z"},
            "filters": {
                "keyword": "error"
            },
            "query_string": None  # 空值
        }
        
        result = adapt_query_to_es6(payload)
        
        must_clauses = result["query"]["bool"]["must"]
        
        # 应该有 keyword 的 multi_match
        keyword_found = False
        for clause in must_clauses:
            if "multi_match" in clause and clause["multi_match"].get("query") == "error":
                keyword_found = True
                break
        
        assert keyword_found is True

    def test_query_string_complex_lucene_syntax(self):
        """测试复杂的 Lucene 语法"""
        test_cases = [
            # OR 逻辑
            "service:(order-service OR payment-service)",
            # NOT 逻辑
            "level:ERROR AND NOT message:timeout",
            # 范围查询
            "status_code:[400 TO 599]",
            # 通配符
            "message:connect*",
            # 模糊匹配
            "message:erorr~",
            # 字段存在性
            "_exists_:trace_id",
        ]
        
        for query in test_cases:
            payload = {
                "tenant_id": "test",
                "pagination": {"page": 1, "page_size": 10},
                "time_range": {"start": "2025-01-01T00:00:00Z", "end": "2025-01-02T00:00:00Z"},
                "query_string": query
            }
            
            result = adapt_query_to_es6(payload)
            
            must_clauses = result["query"]["bool"]["must"]
            query_string_clause = None
            for clause in must_clauses:
                if "query_string" in clause:
                    query_string_clause = clause
                    break
            
            assert query_string_clause is not None, f"Query '{query}' should generate query_string clause"
            assert query_string_clause["query_string"]["query"] == query

    def test_query_string_whitespace_only(self):
        """测试 query_string 只有空白字符时回退到 keyword"""
        payload = {
            "tenant_id": "test",
            "pagination": {"page": 1, "page_size": 10},
            "time_range": {"start": "2025-01-01T00:00:00Z", "end": "2025-01-02T00:00:00Z"},
            "filters": {
                "keyword": "error"
            },
            "query_string": "   "  # 只有空白
        }
        
        result = adapt_query_to_es6(payload)
        
        must_clauses = result["query"]["bool"]["must"]
        
        # 应该使用 keyword
        keyword_found = False
        for clause in must_clauses:
            if "multi_match" in clause:
                keyword_found = True
                break
        
        assert keyword_found is True

    def test_backward_compatibility_without_query_string(self):
        """测试完全不提供 query_string 时的向后兼容性"""
        payload = {
            "tenant_id": "test",
            "pagination": {"page": 1, "page_size": 10},
            "time_range": {"start": "2025-01-01T00:00:00Z", "end": "2025-01-02T00:00:00Z"},
            "filters": {
                "keyword": "connection failed",
                "level": ["ERROR", "WARN"],
                "service": ["order-service"]
            }
        }
        
        result = adapt_query_to_es6(payload)
        
        # 验证基本结构正确
        assert "query" in result
        assert "bool" in result["query"]
        assert "must" in result["query"]["bool"]
        assert "filter" in result["query"]["bool"]
        
        # 验证 keyword 正常工作
        must_clauses = result["query"]["bool"]["must"]
        keyword_found = False
        for clause in must_clauses:
            if "multi_match" in clause and clause["multi_match"].get("query") == "connection failed":
                keyword_found = True
                break
        
        assert keyword_found is True
        
        # 验证 filter 正常工作
        filter_clauses = result["query"]["bool"]["filter"]
        assert len(filter_clauses) > 0  # 至少应该有 tenant_id 和 time_range


class TestQueryStringIntegration:
    """测试 query_string 与现有功能的集成"""

    def test_query_string_with_tenant_filter(self):
        """测试 query_string 与租户过滤共存"""
        payload = {
            "tenant_id": "sctv",
            "pagination": {"page": 1, "page_size": 10},
            "time_range": {"start": "2025-01-01T00:00:00Z", "end": "2025-01-02T00:00:00Z"},
            "query_string": "level:ERROR"
        }
        
        result = adapt_query_to_es6(payload)
        
        # 验证 filter 中有 tenant_id
        filter_clauses = result["query"]["bool"]["filter"]
        tenant_found = False
        for clause in filter_clauses:
            if "term" in clause and "tenant_id" in clause["term"]:
                tenant_found = True
                break
        
        assert tenant_found is True
        
        # 验证 must 中有 query_string
        must_clauses = result["query"]["bool"]["must"]
        query_string_found = False
        for clause in must_clauses:
            if "query_string" in clause:
                query_string_found = True
                break
        
        assert query_string_found is True

    def test_query_string_with_time_range(self):
        """测试 query_string 与时间范围过滤共存"""
        payload = {
            "tenant_id": "test",
            "pagination": {"page": 1, "page_size": 10},
            "time_range": {"start": "2025-01-01T00:00:00Z", "end": "2025-01-02T00:00:00Z"},
            "query_string": "service:order-service"
        }
        
        result = adapt_query_to_es6(payload)
        
        # 验证 filter 中有时间范围
        filter_clauses = result["query"]["bool"]["filter"]
        time_range_found = False
        for clause in filter_clauses:
            if "bool" in clause and "should" in clause["bool"]:
                # 时间范围查询的结构
                time_range_found = True
                break
        
        assert time_range_found is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
