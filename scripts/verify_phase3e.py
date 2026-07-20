#!/usr/bin/env python3
"""Phase 3E verification: reviewed-promotion importer and review-batch readiness."""
from __future__ import annotations

import importlib
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
    sys.path.insert(0, str(ROOT))
    for module in ["scripts.promotion_importer", "scripts.review_batch"]:
        try:
            importlib.import_module(module)
        except Exception as exc:
            return fail(f"cannot import {module}: {type(exc).__name__}: {exc}")
    feed = load(DATA / "public_sector_feed.json")
    reviewed = load(DATA / "reviewed_promotions.json")
    if "Phase 3E" not in str(feed.get("meta", {}).get("implementation_phase", "")):
        return fail("feed meta does not identify Phase 3E")
    if reviewed.get("version") not in {"3D.1", "3E.1"}:
        return fail("reviewed_promotions.json version must be 3E.1")
    if "reviewed" not in reviewed or not isinstance(reviewed["reviewed"], list):
        return fail("reviewed_promotions.json must contain reviewed[]")
    report = load(DATA / "last_run_report.json")
    if "Phase 3E" not in str(report.get("implementation_phase", "")):
        return fail("last_run_report does not identify Phase 3E")
    for path in ["manual_review_batch_1.json", "manual_review_batch_summary.json"]:
        if not (DATA / path).exists():
            return fail(f"missing data/{path}")
    promo_report = load(DATA / "promotion_import_report.json")
    for key in ["reviewed_total", "added", "rejected", "duplicates"]:
        if key not in promo_report:
            return fail(f"promotion_import_report missing {key}")
    print("OK: Phase 3E reviewed-promotion importer and manual review batch checks passed.")
    print(f"Vacancies: {len(feed.get('vacancies', []))}")
    print(f"Reviewed promotions added: {promo_report.get('added', 0)}")
    print(f"Manual review batch items: {load(DATA / 'manual_review_batch_summary.json').get('items_total', 0)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
