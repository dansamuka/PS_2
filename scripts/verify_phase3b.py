#!/usr/bin/env python3
"""Phase 3B checks: latest-role ingestion hardening."""
from __future__ import annotations

import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
REQUIRED_FILES = [
    ROOT / "scripts" / "collectors" / "pscims.py",
    ROOT / "scripts" / "collectors" / "mygov.py",
    ROOT / "scripts" / "collectors" / "ksg.py",
    ROOT / "scripts" / "collectors" / "official_page_monitor.py",
    ROOT / "scripts" / "collectors" / "_common.py",
    DATA / "last_run_report.json",
    DATA / "central_collector_report.json",
    DATA / "discovery_queue.json",
]


def load(path):
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))


def fail(msg):
    print("ERROR:", msg)
    return 1


def main():
    for path in REQUIRED_FILES:
        if not path.exists():
            return fail(f"missing Phase 3B file: {path.relative_to(ROOT)}")
    feed = load(DATA / "public_sector_feed.json")
    reg = load(DATA / "source_registry.json")
    report = load(DATA / "last_run_report.json")
    if not any(x in str(feed.get("meta", {}).get("implementation_phase", "")) for x in ["Phase 3B", "Phase 3C"]):
        return fail("feed meta does not identify Phase 3B/3C latest-role ingestion lineage")
    if feed.get("meta", {}).get("role_scope") not in {"all_role_families", "all_job_families"}:
        return fail("feed meta role_scope must identify all role/job families")
    vacancies = feed.get("vacancies", [])
    if not vacancies:
        return fail("feed contains no active/latest vacancies")
    missing_links = [v.get("id") for v in vacancies if not str(v.get("links", {}).get("view_original_url", "")).startswith(("http://", "https://"))]
    if missing_links:
        return fail(f"vacancies missing valid view_original_url: {missing_links[:10]}")
    ids = {s.get("source_id") for s in reg.get("sources", [])}
    for source_id in ["pscims_active_adverts", "ksg_jobapplications", "mygov_government_advertising_agency"]:
        if source_id not in ids:
            return fail(f"missing required source registry entry: {source_id}")
    enabled = {s.get("source_id") for s in reg.get("sources", []) if s.get("enabled")}
    for source_id in ["pscims_active_adverts", "ksg_jobapplications", "mygov_government_advertising_agency"]:
        if source_id not in enabled:
            return fail(f"required source is not enabled: {source_id}")
    cs = feed.get("meta", {}).get("change_summary")
    if not isinstance(cs, dict):
        return fail("feed meta missing change_summary")
    for key in ["new_roles", "updated_roles", "expired_roles", "unchanged_roles"]:
        if key not in cs:
            return fail(f"change_summary missing {key}")
    if not any(x in str(report.get("implementation_phase", "")) for x in ["Phase 3B", "Phase 3C"]):
        return fail("last_run_report does not identify Phase 3B/3C latest-role ingestion lineage")
    print("OK: Phase 3B latest-role ingestion checks passed.")
    print(f"Vacancies: {len(vacancies)}")
    print(f"Registered national sources: {len(reg.get('sources', []))}")
    print(f"Change summary: new={cs.get('new_roles')} updated={cs.get('updated_roles')} expired={cs.get('expired_roles')} unchanged={cs.get('unchanged_roles')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
