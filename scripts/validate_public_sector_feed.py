#!/usr/bin/env python3
"""Accuracy-first validator for Kazi Sasa Kenya public-sector feed.

Checks schema shape, source-confidence rules, original-site links, scam triggers,
source registry consistency, and Phase 1 quality gates.
"""
import argparse, datetime as dt, json, pathlib, sys
from urllib.parse import urlparse

CONFIDENCE = {"official", "official_discovery", "needs_review", "aggregated", "unverified", "rejected", "registry_source"}
VERIFICATION = {"verified", "needs_review", "rejected", "expired"}
EMAIL_BAD_DOMAINS = ("gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "proton.me", "protonmail.com")
REQUIRED_TOP = ["meta", "vacancies"]
REQUIRED_VAC = ["id", "title", "institution", "source", "advert", "location", "employment", "requirements", "job_family", "application", "verification", "links"]


def parse_dt(value):
    if not value:
        return None
    try:
        return dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None


def domain_of(url):
    try:
        return urlparse(url).netloc.lower().replace("www.", "")
    except Exception:
        return ""


def load_json(path):
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))


def validate_feed(path, registry_path=None, production=True):
    data = load_json(path)
    errors, warnings = [], []
    for k in REQUIRED_TOP:
        if k not in data:
            errors.append(f"missing top-level {k}")
    meta = data.get("meta", {})
    vacancies = data.get("vacancies", [])
    if production and meta.get("is_sample_data") is True:
        errors.append("production feed must not set meta.is_sample_data=true")
    if meta.get("vacancy_count") != len(vacancies):
        errors.append(f"meta.vacancy_count {meta.get('vacancy_count')} != actual {len(vacancies)}")
    registry = {}
    if registry_path and pathlib.Path(registry_path).exists():
        reg = load_json(registry_path)
        for s in reg.get("sources", []):
            sid = s.get("source_id")
            if not sid:
                errors.append("source_registry entry missing source_id")
            elif sid in registry:
                errors.append(f"duplicate source_id in registry: {sid}")
            else:
                registry[sid] = s
    ids = set()
    now = dt.datetime.now(dt.timezone.utc)
    for i, v in enumerate(vacancies):
        prefix = f"vacancies[{i}] {v.get('id','<missing-id>')}"
        for k in REQUIRED_VAC:
            if k not in v:
                errors.append(f"{prefix} missing {k}")
        vid = v.get("id")
        if not vid:
            errors.append(f"{prefix} missing id")
        elif vid in ids:
            errors.append(f"duplicate vacancy id: {vid}")
        ids.add(vid)
        if not v.get("title"):
            errors.append(f"{prefix} missing title")
        src = v.get("source", {})
        conf = src.get("confidence")
        if conf not in CONFIDENCE:
            errors.append(f"{prefix} invalid source confidence: {conf}")
        ver = v.get("verification", {}).get("status")
        if ver not in VERIFICATION:
            warnings.append(f"{prefix} unknown verification status: {ver}")
        if ver == "rejected":
            errors.append(f"{prefix} rejected record must not appear in vacancies[]")
        links = v.get("links", {})
        view_url = links.get("view_original_url")
        if not view_url:
            errors.append(f"{prefix} missing links.view_original_url")
        elif not str(view_url).startswith(("http://", "https://")):
            errors.append(f"{prefix} invalid links.view_original_url: {view_url}")
        app = v.get("application", {})
        email = str(app.get("email") or "").lower()
        if app.get("requires_email_submission") and email.endswith(EMAIL_BAD_DOMAINS):
            errors.append(f"{prefix} uses prohibited free-email application address: {email}")
        if app.get("fee_required"):
            errors.append(f"{prefix} fee_required=true is not allowed in open verified feed")
        deadline = parse_dt(v.get("advert", {}).get("deadline"))
        if not deadline:
            warnings.append(f"{prefix} missing/invalid deadline")
        elif deadline.astimezone(dt.timezone.utc) < now and ver != "expired":
            warnings.append(f"{prefix} deadline appears expired but verification.status is not expired")
        # Registry and domain rules
        prov = (v.get("provenance") or [{}])[0]
        source_id = prov.get("source_id")
        if registry_path and source_id and source_id not in registry:
            warnings.append(f"{prefix} provenance source_id not in source_registry: {source_id}")
        if conf == "official":
            domains = []
            if source_id in registry:
                domains = [d.lower().replace("www.", "") for d in registry[source_id].get("allowed_apply_domains", [])]
            url_domains = {domain_of(src.get("url", "")), domain_of(app.get("apply_url", "")), domain_of(view_url)}
            if domains and not any(d in url_domains or any(u.endswith(d) for u in url_domains) for d in domains):
                errors.append(f"{prefix} official confidence but URLs do not match allowed domains {domains}")
        if conf == "official" and ver != "verified":
            warnings.append(f"{prefix} official source but verification.status={ver}")
    print(f"{path}: {len(errors)} error(s), {len(warnings)} warning(s), {len(vacancies)} vacancies")
    for w in warnings[:80]:
        print("WARNING:", w)
    for e in errors:
        print("ERROR:", e)
    return 1 if errors else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("feed", nargs="?", default="data/public_sector_feed.json")
    ap.add_argument("--registry", default="data/source_registry.json")
    ap.add_argument("--allow-sample", action="store_true")
    args = ap.parse_args()
    raise SystemExit(validate_feed(args.feed, args.registry, production=not args.allow_sample))


if __name__ == "__main__":
    main()
