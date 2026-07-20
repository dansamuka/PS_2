#!/usr/bin/env python3
"""Phase 3C checks for role identity reconciliation and discovery-review readiness."""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def load(path):
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))


def fail(msg):
    print("ERROR:", msg)
    return 1


def main():
    feed = load(DATA / "public_sector_feed.json")
    report = load(DATA / "last_run_report.json")
    role_map = load(DATA / "role_identity_map.json") if (DATA / "role_identity_map.json").exists() else None
    review = load(DATA / "discovery_review_queue.json") if (DATA / "discovery_review_queue.json").exists() else None
    meta = feed.get("meta", {})
    if "Phase 3C" not in str(meta.get("implementation_phase", "")):
        return fail("feed meta does not identify Phase 3C")
    if "Phase 3C" not in str(report.get("implementation_phase", "")):
        return fail("last_run_report does not identify Phase 3C")
    vacancies = feed.get("vacancies", [])
    if not vacancies:
        return fail("feed contains no vacancies")
    missing_identity = [v.get("id") for v in vacancies if not v.get("identity", {}).get("canonical_key")]
    if missing_identity:
        return fail(f"vacancies missing identity.canonical_key: {missing_identity[:10]}")
    keys = [v.get("identity", {}).get("canonical_key") for v in vacancies]
    if len(set(keys)) > len(vacancies):
        return fail("impossible identity count detected")
    if role_map is None:
        return fail("data/role_identity_map.json is missing")
    if role_map.get("role_count") != len(set(keys)):
        return fail(f"role_identity_map role_count {role_map.get('role_count')} != canonical keys {len(set(keys))}")
    cs = report.get("change_summary") or meta.get("change_summary") or {}
    required = ["genuine_new_roles", "identity_reconciled_roles", "refreshed_existing_roles", "canonical_roles_after"]
    missing = [k for k in required if k not in cs]
    if missing:
        return fail(f"change_summary missing Phase 3C fields: {missing}")
    if cs.get("canonical_roles_after") != len(set(keys)):
        return fail("change_summary canonical_roles_after does not match feed canonical identities")
    if review is None:
        return fail("data/discovery_review_queue.json is missing")
    if "promotion_policy" not in review:
        return fail("discovery_review_queue missing promotion_policy")
    print("OK: Phase 3C role identity reconciliation checks passed.")
    print(f"Vacancies: {len(vacancies)}")
    print(f"Canonical roles: {len(set(keys))}")
    print(f"Genuine new roles: {cs.get('genuine_new_roles')}")
    print(f"Identity-reconciled roles: {cs.get('identity_reconciled_roles')}")
    print(f"Discovery review items: {review.get('generated_count', 0)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
