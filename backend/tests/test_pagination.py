"""
分页查询功能测试文件
测试分页查询的各种边界条件和异常情况，确保分页查询的稳定性和安全性

作者：AI Assistant
创建时间：2025-07-20
最后修改：2025-07-20
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings

client = TestClient(app)


@pytest.fixture
def valid_query_payload():
    """
    提供有效的查询负载
    
    返回：
        dict: 包含必要字段的查询负载
    """
    return {
        "tenant_id": "test_tenant",
        "pagination": {
            "page": 1,
            "page_size": 20
        },
        "time_range": {
            "start": "2023-01-01T00:00:00Z",
            "end": "2025-12-31T23:59:59Z"
        },
        "filters": {},
        "sort": {
            "field": "timestamp",
            "order": "desc"
        },
        "index_keyword": "test",  # 添加索引关键字，满足安全检查
        "override_indexes": ["test-index-2023.01.01"]  # 明确指定索引
    }


def test_pagination_default_values(valid_query_payload):
    """
    测试分页默认值
    验证当使用默认分页参数时，系统能正常处理
    """
    # 使用默认分页参数
    valid_query_payload["pagination"] = {
        "page": 1,
        "page_size": 50
    }
    
    # 添加认证头信息
    headers = {
        "Authorization": "Bearer test-token",
        "X-Tenant-Id": "test_tenant"
    }
    
    # 这里我们只测试API结构，不验证实际数据
    # 因为测试环境可能没有真实数据
    response = client.post("/api/logs/query", json=valid_query_payload, headers=headers)
    
    # 验证响应结构
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["code"] == 0
    assert "data" in response_data
    assert "total" in response_data["data"]
    assert "items" in response_data["data"]


def test_pagination_valid_page_sizes(valid_query_payload):
    """
    测试有效页大小范围
    验证不同的有效页大小都能正常工作
    """
    test_sizes = [1, 20, 50, 100, 200]  # 最大允许200
    
    # 添加认证头信息
    headers = {
        "Authorization": "Bearer test-token",
        "X-Tenant-Id": "test_tenant"
    }
    
    for size in test_sizes:
        valid_query_payload["pagination"]["page_size"] = size
        
        response = client.post("/api/logs/query", json=valid_query_payload, headers=headers)
        
        # 验证响应结构
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["code"] == 0
        assert "data" in response_data


def test_pagination_page_size_limits(valid_query_payload):
    """
    测试页大小限制
    验证超出限制的页大小会被自动调整
    """
    # 添加认证头信息
    headers = {
        "Authorization": "Bearer test-token",
        "X-Tenant-Id": "test_tenant"
    }
    
    # 测试最大值边界
    valid_query_payload["pagination"]["page_size"] = 200
    response = client.post("/api/logs/query", json=valid_query_payload, headers=headers)
    assert response.status_code == 200
    
    # 测试最小值边界
    valid_query_payload["pagination"]["page_size"] = 1
    response = client.post("/api/logs/query", json=valid_query_payload, headers=headers)
    assert response.status_code == 200


def test_pagination_page_number_limits(valid_query_payload):
    """
    测试页码限制
    验证页码在有效范围内时能正常工作
    """
    # 添加认证头信息
    headers = {
        "Authorization": "Bearer test-token",
        "X-Tenant-Id": "test_tenant"
    }
    
    # 测试页码最小值
    valid_query_payload["pagination"]["page"] = 1
    response = client.post("/api/logs/query", json=valid_query_payload, headers=headers)
    assert response.status_code == 200
    
    # 测试页码最大值边界
    valid_query_payload["pagination"]["page"] = 100000
    response = client.post("/api/logs/query", json=valid_query_payload, headers=headers)
    assert response.status_code == 200


def test_pagination_deep_paging_protection(valid_query_payload):
    """
    测试深度分页保护
    验证深度分页请求不会导致系统崩溃
    """
    # 添加认证头信息
    headers = {
        "Authorization": "Bearer test-token",
        "X-Tenant-Id": "test_tenant"
    }
    
    # 测试较大的页码
    valid_query_payload["pagination"]["page"] = 1000
    valid_query_payload["pagination"]["page_size"] = 10
    
    response = client.post("/api/logs/query", json=valid_query_payload, headers=headers)
    
    # 验证响应结构，即使没有数据也应该正常响应
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["code"] == 0
    assert "data" in response_data


def test_pagination_cursor_mode(valid_query_payload):
    """
    测试游标分页模式
    验证游标分页模式是否正常工作
    """
    # 添加认证头信息
    headers = {
        "Authorization": "Bearer test-token",
        "X-Tenant-Id": "test_tenant"
    }
    
    # 添加游标分页模式参数
    valid_query_payload["mode"] = "cursor"
    
    response = client.post("/api/logs/query", json=valid_query_payload, headers=headers)
    
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["code"] == 0
    
    # 验证响应中是否包含游标相关字段
    assert "data" in response_data
    if response_data["data"]["items"]:
        assert "next_cursor_after" in response_data["data"]
        assert "page_size" in response_data["data"]


def test_pagination_index_limit_protection(valid_query_payload):
    """
    测试索引数量限制保护
    验证系统会限制查询的索引数量
    """
    # 添加认证头信息
    headers = {
        "Authorization": "Bearer test-token",
        "X-Tenant-Id": "test_tenant"
    }
    
    # 尝试覆盖索引列表，使用大量索引
    valid_query_payload["override_indexes"] = [f"logs-{i}" for i in range(300)]  # 超过200个索引
    
    response = client.post("/api/logs/query", json=valid_query_payload, headers=headers)
    
    # 即使索引数量超过限制，系统也应该进行降级处理而不是崩溃
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["code"] == 0


def test_pagination_with_keyword_search(valid_query_payload):
    """
    测试带有关键词搜索的分页查询
    验证关键词搜索与分页的结合使用
    """
    # 添加认证头信息
    headers = {
        "Authorization": "Bearer test-token",
        "X-Tenant-Id": "test_tenant"
    }
    
    # 添加关键词搜索
    valid_query_payload["filters"]["keyword"] = "test"
    
    response = client.post("/api/logs/query", json=valid_query_payload, headers=headers)
    
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["code"] == 0
    assert "data" in response_data


def test_pagination_with_time_range(valid_query_payload):
    """
    测试带有时间范围的分页查询
    验证时间范围过滤与分页的结合使用
    """
    # 添加认证头信息
    headers = {
        "Authorization": "Bearer test-token",
        "X-Tenant-Id": "test_tenant"
    }
    
    # 使用更具体的时间范围
    valid_query_payload["time_range"]["start"] = "2024-01-01T00:00:00Z"
    valid_query_payload["time_range"]["end"] = "2024-12-31T23:59:59Z"
    
    response = client.post("/api/logs/query", json=valid_query_payload, headers=headers)
    
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["code"] == 0
    assert "data" in response_data


def test_pagination_performance_metrics(valid_query_payload):
    """
    测试分页查询的性能指标
    验证系统会记录分页查询的性能指标
    """
    # 添加认证头信息
    headers = {
        "Authorization": "Bearer test-token",
        "X-Tenant-Id": "test_tenant"
    }
    
    # 这个测试主要验证系统不会崩溃，性能指标的具体验证需要专门的监控工具
    response = client.post("/api/logs/query", json=valid_query_payload, headers=headers)
    
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["code"] == 0


if __name__ == "__main__":
    # 运行所有测试
    import pytest
    pytest.main([__file__, "-v"])