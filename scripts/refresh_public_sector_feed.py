#!/usr/bin/env python3
"""Phase 1 public-sector feed refresh / normalization runner.

This is intentionally accuracy-first. It does not claim near-complete scraping yet.
It normalizes the active snapshot, applies registries/taxonomy, preserves actual rows,
and produces source-health/run-report artifacts. Future phases add real collectors.
"""
import argparse, datetime as dt, json, pathlib, shutil, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
NOW = dt.datetime.now(dt.timezone(dt.timedelta(hours=3))).isoformat(timespec="seconds")


def load(path, default=None):
    p = pathlib.Path(path)
    if not p.exists():
        return default
    return json.loads(p.read_text(encoding="utf-8"))


def write(path, obj):
    pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(path).write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def ensure_links(feed):
    changed = 0
    for v in feed.get("vacancies", []):
        links = v.setdefault("links", {})
        original = links.get("view_original_url") or v.get("raw", {}).get("detail_url") or v.get("source", {}).get("url") or v.get("application", {}).get("apply_url")
        if original and not links.get("view_original_url"):
            links["view_original_url"] = original
            links["view_original_label"] = "View role on original site"
            changed += 1
        links.setdefault("view_source_url", v.get("source", {}).get("url"))
        links.setdefault("view_apply_url", v.get("application", {}).get("apply_url"))
    return changed


def apply_registry(feed):
    reg = load(DATA / "source_registry.json", {"sources": []})
    sources = reg.get("sources", [])
    source_by_id = {s.get("source_id"): s for s in sources}
    counts = {}
    for v in feed.get("vacancies", []):
        prov = (v.get("provenance") or [{}])[0]
        sid = prov.get("source_id")
        if not sid:
            sid = "pscims_active_adverts" if "PSCIMS" in v.get("source", {}).get("name", "") else "ksg_jobapplications"
            v["provenance"] = [{"source_id": sid, "url": v.get("links", {}).get("view_original_url") or v.get("source", {}).get("url"), "seen_at": NOW}]
        counts[sid] = counts.get(sid, 0) + 1
    status = []
    for s in sources:
        sid = s.get("source_id")
        status.append({
            "id": sid,
            "name": s.get("name"),
            "owner": s.get("owner_type"),
            "source_class": s.get("source_group"),
            "enabled": s.get("enabled", False),
            "confidence": s.get("confidence_default"),
            "base_url": s.get("official_url"),
            "collector_type": s.get("collector_type"),
            "coverage_priority": s.get("coverage_priority"),
            "status": s.get("status"),
            "last_successful_fetch_at": NOW if counts.get(sid) else None,
            "active_roles": counts.get(sid, 0),
            "last_error": None if counts.get(sid) else ("not_enabled" if not s.get("enabled") else "no_roles_captured"),
            "notes": s.get("notes")
        })
    write(DATA / "source_status.json", {"generated_at": NOW, "sources": status})
    feed["source_status"] = status
    return counts, len(sources)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=str(DATA / "public_sector_feed.json"))
    ap.add_argument("--out", default=str(DATA / "public_sector_feed.json"))
    ap.add_argument("--root-out", default=str(ROOT / "public_sector_feed.json"))
    args = ap.parse_args()
    feed = load(args.input)
    if not feed:
        print("No input feed found; aborting rather than writing empty feed.")
        return 2
    changed = ensure_links(feed)
    counts, source_count = apply_registry(feed)
    feed.setdefault("meta", {})
    feed["meta"].update({
        "schema_version": "1.1-public-sector-expanded",
        "generated_at": NOW,
        "vacancy_count": len(feed.get("vacancies", [])),
        "source_count": source_count,
        "is_sample_data": False,
    })
    feed.setdefault("rejected_watchlist", load(DATA / "rejected_watchlist.json", {"items": []}).get("items", []))
    write(args.out, feed)
    write(args.root_out, feed)
    report = {
        "run_id": NOW,
        "started_at": NOW,
        "finished_at": NOW,
        "implementation_phase": "Phase 1 — Registry and quality foundation",
        "vacancies_active": len(feed.get("vacancies", [])),
        "sources_registered": source_count,
        "sources_with_roles": len([k for k, v in counts.items() if v]),
        "links_added_or_confirmed": changed,
        "quality_gate_status": "pending_validation",
        "note": "Phase 1 normalizer ran. Future phases add live PSCIMS/MyGov/county/SAGA collectors."
    }
    write(DATA / "last_run_report.json", report)
    print(f"Normalized {len(feed.get('vacancies', []))} vacancies; sources registered: {source_count}; links added: {changed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
