"""
Copyright (c) 2025, elk-MCP Project.
All rights reserved.
"""

"""
文件功能：模糊匹配查询功能的单元测试
主要类/函数：测试 _build_keyword_query 的各种匹配类型
作者：系统自动生成
创建时间：2026-02-25
最后修改：2026-02-25
"""

import pytest
from app.es.query_adapter import _build_keyword_query, FUZZY_MATCH_TYPES


class TestBuildKeywordQuery:
    """测试 _build_keyword_query 函数的各种匹配类型"""

    def test_contains_match(self):
        """测试默认的包含匹配"""
        result = _build_keyword_query("error", "contains")
        
        # 验证返回的是 multi_match 查询
        assert "multi_match" in result
        assert result["multi_match"]["query"] == "error"
        assert result["multi_match"]["type"] == "best_fields"
        assert "message" in result["multi_match"]["fields"]
        assert "logmessage" in result["multi_match"]["fields"]

    def test_prefix_match(self):
        """测试前缀匹配"""
        result = _build_keyword_query("connect", "prefix")
        
        # 验证返回的是 bool + should + prefix 查询
        assert "bool" in result
        assert "should" in result["bool"]
        assert result["bool"]["minimum_should_match"] == 1
        
        # 验证每个字段都有 prefix 查询
        should_clauses = result["bool"]["should"]
        assert len(should_clauses) > 0
        for clause in should_clauses:
            assert "prefix" in clause

    def test_fuzzy_match(self):
        """测试模糊匹配（容忍拼写错误）"""
        result = _build_keyword_query("erorr", "fuzzy", {"fuzziness": "AUTO"})
        
        # 验证返回的是带 fuzziness 参数的 multi_match
        assert "multi_match" in result
        assert result["multi_match"]["query"] == "erorr"
        assert result["multi_match"]["fuzziness"] == "AUTO"
        assert result["multi_match"]["prefix_length"] == 2  # 默认值
        assert result["multi_match"]["max_expansions"] == 50  # 默认值

    def test_fuzzy_match_with_custom_options(self):
        """测试带自定义参数的模糊匹配"""
        options = {
            "fuzziness": 2,
            "prefix_length": 3,
            "max_expansions": 100
        }
        result = _build_keyword_query("test", "fuzzy", options)
        
        assert result["multi_match"]["fuzziness"] == 2
        assert result["multi_match"]["prefix_length"] == 3
        assert result["multi_match"]["max_expansions"] == 100

    def test_wildcard_match(self):
        """测试通配符匹配"""
        result = _build_keyword_query("*exception*", "wildcard")
        
        # 验证返回的是 bool + should + wildcard 查询
        assert "bool" in result
        assert "should" in result["bool"]
        
        should_clauses = result["bool"]["should"]
        for clause in should_clauses:
            assert "wildcard" in clause
            # 验证 case_insensitive 默认为 True
            field = list(clause["wildcard"].keys())[0]
            assert clause["wildcard"][field].get("case_insensitive") is True

    def test_wildcard_case_sensitive(self):
        """测试大小写敏感的通配符匹配"""
        result = _build_keyword_query("Test*", "wildcard", {"case_insensitive": False})
        
        should_clauses = result["bool"]["should"]
        for clause in should_clauses:
            field = list(clause["wildcard"].keys())[0]
            # 当 case_insensitive=False 时，不应该有 case_insensitive 字段
            assert clause["wildcard"][field].get("case_insensitive") is None

    def test_regexp_match(self):
        """测试正则表达式匹配"""
        result = _build_keyword_query("err.*or", "regexp")
        
        # 验证返回的是 bool + should + regexp 查询
        assert "bool" in result
        assert "should" in result["bool"]
        
        should_clauses = result["bool"]["should"]
        for clause in should_clauses:
            assert "regexp" in clause
            # 验证默认启用大小写不敏感
            field = list(clause["regexp"].keys())[0]
            assert clause["regexp"][field].get("flags") == "ALL"

    def test_invalid_fuzzy_type_fallback(self):
        """测试无效的 fuzzy_type 自动回退到 contains"""
        result = _build_keyword_query("test", "invalid_type")
        
        # 应该回退到默认的 contains 类型
        assert "multi_match" in result
        assert result["multi_match"]["type"] == "best_fields"

    def test_empty_fuzzy_options(self):
        """测试空的 fuzzy_options"""
        result = _build_keyword_query("test", "contains", None)
        
        # 应该正常工作，使用默认值
        assert "multi_match" in result

    def test_supported_fuzzy_types(self):
        """测试支持的模糊匹配类型集合"""
        expected_types = {"contains", "prefix", "fuzzy", "wildcard", "regexp"}
        assert FUZZY_MATCH_TYPES == expected_types


class TestQueryAdapterIntegration:
    """测试 query_adapter 的集成功能"""

    def test_adapt_query_with_fuzzy_params(self):
        """测试 adapt_query_to_es6 接受模糊匹配参数"""
        from app.es.query_adapter import adapt_query_to_es6
        
        payload = {
            "tenant_id": "test",
            "pagination": {"page": 1, "page_size": 10},
            "time_range": {"start": "2025-01-01T00:00:00Z", "end": "2025-01-02T00:00:00Z"},
            "filters": {
                "keyword": "error",
                "fuzzy_type": "fuzzy",
                "fuzzy_options": {"fuzziness": "AUTO"}
            }
        }
        
        result = adapt_query_to_es6(payload)
        
        # 验证查询结构正确
        assert "query" in result
        assert "bool" in result["query"]
        assert "must" in result["query"]["bool"]
        
        # 验证 must 中包含模糊匹配查询
        must_clauses = result["query"]["bool"]["must"]
        assert len(must_clauses) > 0
        
        # 找到 keyword 相关的查询
        keyword_query = None
        for clause in must_clauses:
            if "multi_match" in clause and clause["multi_match"].get("query") == "error":
                keyword_query = clause
                break
        
        assert keyword_query is not None
        assert keyword_query["multi_match"]["fuzziness"] == "AUTO"

    def test_adapt_query_backward_compatible(self):
        """测试 adapt_query_to_es6 向后兼容（不使用模糊匹配参数）"""
        from app.es.query_adapter import adapt_query_to_es6
        
        payload = {
            "tenant_id": "test",
            "pagination": {"page": 1, "page_size": 10},
            "time_range": {"start": "2025-01-01T00:00:00Z", "end": "2025-01-02T00:00:00Z"},
            "filters": {
                "keyword": "error"
                # 不提供 fuzzy_type 和 fuzzy_options
            }
        }
        
        result = adapt_query_to_es6(payload)
        
        # 验证查询正常工作
        assert "query" in result
        assert "bool" in result["query"]
        
        # 验证默认使用 contains 类型
        must_clauses = result["query"]["bool"]["must"]
        keyword_query = None
        for clause in must_clauses:
            if "multi_match" in clause and clause["multi_match"].get("query") == "error":
                keyword_query = clause
                break
        
        assert keyword_query is not None
        # 默认类型不应该有 fuzziness 参数
        assert "fuzziness" not in keyword_query["multi_match"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
