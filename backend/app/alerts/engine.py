"""
Copyright (c) 2025, elk-MCP Project.
All rights reserved.
"""

from typing import Any, Dict, List


def evaluate_alerts(hits: List[Dict[str, Any]], severities: List[str]) -> List[Dict[str, Any]]:
    """Simple alert evaluation based on level mapping.

    This is a placeholder; in production, load rules from config and apply.
    """
    severity_map = {"error": "high", "warn": "medium", "info": "low"}
    out: List[Dict[str, Any]] = []
    for h in hits:
        src = h.get("_source", {})
        level = (src.get("level") or "").lower()
        sev = severity_map.get(level, "low")
        if not severities or sev in severities:
            out.append({"hit": h, "severity": sev})
    return out

