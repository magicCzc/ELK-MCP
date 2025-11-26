"""
Copyright (c) 2025, elk-MCP Project.
All rights reserved.
"""

from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def test_healthz():
    resp = client.get("/healthz")
    assert resp.status_code == 200
    js = resp.json()
    assert js["code"] == 0


def test_query_auth_required():
    resp = client.post("/api/logs/query", json={})
    assert resp.status_code == 401

