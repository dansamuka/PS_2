#!/usr/bin/env python3
"""Build a Phase 3E manual review batch from discovery promotion candidates."""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import pathlib
from collections import Counter

EAT = dt.timezone(dt.timedelta(hours=3))
ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

PRIORITY_INSTITUTIONS = [
    "Kenya Revenue Authority", "Competition Authority", "Kenya Railways", "KenTrade", "KEMSA", "KCAA",
    "Commission", "Authority", "Board", "University", "Ministry", "Hospital", "TVET", "Agency",
]


def load(path, default=None):
    p = pathlib.Path(path)
    if not p.exists():
        return default
    return json.loads(p.read_text(encoding="utf-8"))


def write(path, obj):
    p = pathlib.Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def score_candidate(c: dict) -> int:
    score = int(c.get("confidence_score") or 0)
    title = f"{c.get('title','')} {c.get('institution','')}"
    for i, pat in enumerate(PRIORITY_INSTITUTIONS):
        if pat.lower() in title.lower():
            score += max(2, 20 - i)
            break
    if c.get("promotion_status") == "ready_for_manual_confirmation":
        score += 30
    if c.get("duplicate_open_role"):
        score -= 40
    if c.get("deadline_detected"):
        score += 10
    return score


def build_batch(candidates_payload: dict, limit: int = 25) -> dict:
    candidates = candidates_payload.get("candidates", []) if isinstance(candidates_payload, dict) else []
    ranked = []
    for c in candidates:
        if c.get("duplicate_open_role"):
            continue
        ranked.append({**c, "review_batch_score": score_candidate(c)})
    ranked.sort(key=lambda c: (-c["review_batch_score"], c.get("institution") or "", c.get("title") or ""))
    batch = ranked[:limit]
    counts = Counter(c.get("promotion_status", "unknown") for c in batch)
    return {
        "version": "3E.1",
        "generated_at": dt.datetime.now(EAT).isoformat(timespec="seconds"),
        "batch_name": "Phase 3E Batch 1 — high-value discovery promotions",
        "policy": "This is a manual review batch. Items are not open roles until copied into data/reviewed_promotions.json with all manual checks complete.",
        "items_total": len(batch),
        "status_counts": dict(counts),
        "items": batch,
    }


def write_csv(path: pathlib.Path, batch: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[
            "id", "title", "institution", "promotion_status", "confidence_score", "review_batch_score",
            "missing_fields", "original_url", "attachment_url", "manual_review_decision", "deadline_confirmed", "application_channel_confirmed", "notes",
        ])
        w.writeheader()
        for item in batch.get("items", []):
            w.writerow({
                "id": item.get("id"),
                "title": item.get("title"),
                "institution": item.get("institution"),
                "promotion_status": item.get("promotion_status"),
                "confidence_score": item.get("confidence_score"),
                "review_batch_score": item.get("review_batch_score"),
                "missing_fields": ";".join(item.get("missing_fields") or []),
                "original_url": item.get("original_url"),
                "attachment_url": item.get("attachment_url"),
                "manual_review_decision": "",
                "deadline_confirmed": "",
                "application_channel_confirmed": "",
                "notes": "",
            })


def write_markdown(path: pathlib.Path, batch: dict):
    lines = [f"# {batch.get('batch_name')}", "", batch.get("policy", ""), ""]
    for i, item in enumerate(batch.get("items", []), 1):
        lines.extend([
            f"## {i}. {item.get('title')} — {item.get('institution')}",
            f"- Candidate ID: `{item.get('id')}`",
            f"- Status: `{item.get('promotion_status')}`",
            f"- Missing fields: {', '.join(item.get('missing_fields') or []) or 'none detected'}",
            f"- Original: {item.get('original_url') or '—'}",
            "- Manual checks: confirm institution, deadline, application route, no fee/payment, and requirements.",
            "",
        ])
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=25)
    args = ap.parse_args()
    candidates = load(DATA / "discovery_promotion_candidates.json", {"candidates": []})
    batch = build_batch(candidates, limit=args.limit)
    write(DATA / "manual_review_batch_1.json", batch)
    write_csv(DATA / "manual_review_batch_1.csv", batch)
    write_markdown(DATA / "manual_review_batch_1.md", batch)
    write(DATA / "manual_review_batch_summary.json", {
        "generated_at": batch.get("generated_at"),
        "items_total": batch.get("items_total"),
        "status_counts": batch.get("status_counts"),
        "policy": batch.get("policy"),
    })
    print(f"Manual review batch generated: {batch.get('items_total')} items")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
