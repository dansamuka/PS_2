#!/usr/bin/env python3
"""Lightweight central official-page monitor.

This is a source-health monitor, not a vacancy extractor. It checks the central PSC/public-service
reference pages so the dashboard can report source health without pretending every page has been
converted into structured jobs.
"""
from __future__ import annotations

try:
    from ._common import fetch_html
except ImportError:  # pragma: no cover
    from _common import fetch_html

DEFAULT_TARGETS = [
    ("public_service_commission_website", "Public Service Commission Website", "https://www.publicservice.go.ke/"),
    ("psckjobs_portal", "Public Service Commission Jobs Portal", "https://www.psckjobs.go.ke/"),
    ("pscims_login_portal", "PSCIMS Login / Application Portal", "https://pscims.publicservice.go.ke/puio/"),
]


def monitor(targets=None) -> list[dict]:
    results = []
    for source_id, name, url in (targets or DEFAULT_TARGETS):
        html, status, error = fetch_html(url, timeout=20)
        results.append({
            "source_id": source_id,
            "name": name,
            "url": url,
            "http_status": status,
            "error": error,
            "reachable": bool(status and not error),
            "content_length": len(html or ""),
            "collector_type": "official_page_monitor",
        })
    return results


if __name__ == "__main__":  # pragma: no cover
    import json
    print(json.dumps(monitor(), indent=2))
