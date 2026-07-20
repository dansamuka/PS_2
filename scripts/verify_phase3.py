#!/usr/bin/env python3
"""Phase 3 smoke checks for central-government collectors and national-only scope."""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
REQUIRED_COLLECTORS = [
    ROOT / "scripts" / "collectors" / "pscims.py",
    ROOT / "scripts" / "collectors" / "mygov.py",
    ROOT / "scripts" / "collectors" / "official_page_monitor.py",
    ROOT / "scripts" / "collectors" / "_common.py",
]
REQUIRED_CENTRAL_SOURCES = {
    "pscims_active_adverts",
    "pscims_login_portal",
    "psckjobs_portal",
    "public_service_commission_website",
    "mygov_government_advertising_agency",
}


def load(path):
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))


def fail(msg):
    print("ERROR:", msg)
    return 1


def main():
    for path in REQUIRED_COLLECTORS:
        if not path.exists():
            return fail(f"missing Phase 3 collector file: {path.relative_to(ROOT)}")
    feed = load(DATA / "public_sector_feed.json")
    reg = load(DATA / "source_registry.json")
    statuses = load(DATA / "source_status.json")
    report = load(DATA / "last_run_report.json")
    if "Phase 3" not in str(feed.get("meta", {}).get("implementation_phase", "")):
        return fail("feed meta does not identify Phase 3")
    if feed.get("meta", {}).get("role_scope") not in {"all_role_families", "all_job_families"}:
        return fail("feed meta role_scope must identify all role/job families")
    vacancies = feed.get("vacancies", [])
    if not vacancies:
        return fail("feed contains no active vacancies")
    missing_links = [v.get("id") for v in vacancies if not v.get("links", {}).get("view_original_url")]
    if missing_links:
        return fail(f"vacancies missing view_original_url: {missing_links[:10]}")
    county_like = []
    for src in reg.get("sources", []):
        sid = str(src.get("source_id") or "")
        if sid.startswith("county_") or src.get("owner_type") == "county_government" or src.get("source_group") in {"county_psbs", "county_governments", "county_assemblies"}:
            county_like.append(sid)
    if county_like:
        return fail(f"county sources are present despite national-only scope: {county_like[:10]}")
    source_ids = {s.get("source_id") for s in reg.get("sources", [])}
    missing = REQUIRED_CENTRAL_SOURCES - source_ids
    if missing:
        return fail(f"missing central source registry entries: {sorted(missing)}")
    enabled = {s.get("source_id") for s in reg.get("sources", []) if s.get("enabled")}
    must_enabled = {"pscims_active_adverts", "mygov_government_advertising_agency"}
    if not must_enabled <= enabled:
        return fail(f"central collector sources not enabled: {sorted(must_enabled - enabled)}")
    status_ids = {s.get("id") for s in statuses.get("sources", [])}
    if not REQUIRED_CENTRAL_SOURCES <= status_ids:
        return fail("source_status missing one or more central sources")
    discovery = load(DATA / "discovery_queue.json") if (DATA / "discovery_queue.json").exists() else {"items": []}
    central_report = load(DATA / "central_collector_report.json") if (DATA / "central_collector_report.json").exists() else {}
    if "Phase 3" not in str(report.get("implementation_phase", "")):
        return fail("last_run_report does not identify Phase 3")
    print("OK: Phase 3 central-government collector checks passed.")
    print(f"Vacancies: {len(vacancies)}")
    print(f"Registered national sources: {len(reg.get('sources', []))}")
    print(f"Central sources required/present: {len(REQUIRED_CENTRAL_SOURCES)}")
    print(f"Discovery queue items: {len(discovery.get('items', []))}")
    print(f"Central collector report phase: {central_report.get('phase', 'missing')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
