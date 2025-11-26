"""
Copyright (c) 2025, elk-MCP Project.
All rights reserved.
"""

from prometheus_client import Counter, Gauge, Histogram, make_asgi_app

REQUESTS_TOTAL = Counter("mcp_requests_total", "Total API requests", ["endpoint"]) 
REQUEST_LATENCY = Histogram("mcp_request_latency_ms", "API latency (ms)", ["endpoint"]) 
ES_BACKEND_LATENCY = Histogram("mcp_es_backend_latency_ms", "ES backend latency (ms)", ["endpoint"]) 
CACHE_HIT_RATIO = Gauge("mcp_cache_hit_ratio", "Cache hit ratio")

# Index discovery and matching metrics
INDEX_REFRESH_TOTAL = Counter("mcp_index_refresh_total", "Index discovery refreshes", [])
INDEX_COUNT_GAUGE = Gauge("mcp_index_count", "Discovered indices count")
INDEX_MATCH_RATIO = Gauge("mcp_index_match_ratio", "Index match success ratio")

metrics_app = make_asgi_app()
