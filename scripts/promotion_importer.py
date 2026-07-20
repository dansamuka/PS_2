#!/usr/bin/env python3
"""Reviewed discovery-promotion importer for PS_2.

Phase 3E is deliberately conservative: GAA/MyGov discovery candidates still do not
enter the open-role feed automatically. They become open vacancies only after a
human reviewer writes a confirmed record into data/reviewed_promotions.json.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import pathlib
import re
from urllib.parse import urlparse

EAT = dt.timezone(dt.timedelta(hours=3))
BAD_EMAIL_DOMAINS = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "proton.me", "protonmail.com"}
DISALLOWED_TEXT = re.compile(r"\b(whatsapp|mpesa|m-pesa|registration\s+fee|processing\s+fee|pay\s+to\s+apply)\b", re.I)


def compact(value: object | None) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def now_iso() -> str:
    return dt.datetime.now(EAT).isoformat(timespec="seconds")


def parse_deadline(value: object | None) -> str | None:
    if not value:
        return None
    text = compact(value)
    try:
        d = dt.datetime.fromisoformat(text.replace("Z", "+00:00"))
        if d.tzinfo is None:
            d = d.replace(tzinfo=EAT)
        return d.astimezone(EAT).isoformat(timespec="seconds")
    except Exception:
        pass
    m = re.search(r"(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+),?\s+(\d{4})", text, re.I)
    months = {
        "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
        "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
        "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9, "oct": 10,
        "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
    }
    if m:
        day = int(m.group(1)); month = months.get(m.group(2).lower()); year = int(m.group(3))
        if month:
            try:
                return dt.datetime(year, month, day, 23, 59, tzinfo=EAT).isoformat(timespec="seconds")
            except ValueError:
                return None
    return None


def is_expired(deadline: str | None, now: dt.datetime | None = None) -> bool:
    if not deadline:
        return False
    now = now or dt.datetime.now(EAT)
    try:
        d = dt.datetime.fromisoformat(deadline.replace("Z", "+00:00"))
        if d.tzinfo is None:
            d = d.replace(tzinfo=EAT)
        return d.astimezone(EAT) < now.astimezone(EAT)
    except Exception:
        return False


def stable_id(*parts: object, prefix: str = "promoted") -> str:
    raw = "|".join(compact(p).lower() for p in parts if p is not None)
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]
    slug = re.sub(r"[^a-z0-9]+", "_", raw.split("|")[0])[:54].strip("_") or prefix
    return f"{prefix}_{slug}_{digest}"


def domain_of(url: str | None) -> str:
    try:
        return urlparse(url or "").netloc.lower().replace("www.", "")
    except Exception:
        return ""


def email_domain(email: str | None) -> str:
    email = compact(email).lower()
    return email.split("@")[-1] if "@" in email else ""


def canonical_pair(title: str, institution: str, deadline: str | None = None) -> tuple[str, str, str]:
    def norm(s): return re.sub(r"[^a-z0-9]+", " ", compact(s).lower()).strip()
    return norm(title), norm(institution), (deadline or "")[:10]


def existing_keys(vacancies: list[dict]) -> set[tuple[str, str, str]]:
    keys = set()
    for v in vacancies or []:
        keys.add(canonical_pair(v.get("title"), (v.get("institution") or {}).get("name"), (v.get("advert") or {}).get("deadline")))
    return keys


def validate_reviewed_record(record: dict, now: dt.datetime | None = None) -> list[str]:
    issues = []
    decision = compact(record.get("decision") or record.get("promotion_decision") or "promote").lower()
    if decision not in {"promote", "approved", "verified"}:
        issues.append("decision_not_promote")
    title = compact(record.get("title"))
    institution = compact(record.get("institution"))
    source_url = compact(record.get("official_source_url") or record.get("original_url") or record.get("source_url"))
    apply_url = compact(record.get("application_url") or record.get("apply_url") or source_url)
    deadline = parse_deadline(record.get("deadline") or record.get("deadline_iso"))
    if not title:
        issues.append("missing_title")
    if not institution:
        issues.append("missing_institution")
    if not source_url.startswith(("http://", "https://")):
        issues.append("missing_or_invalid_official_source_url")
    if apply_url and not apply_url.startswith(("http://", "https://", "mailto:")):
        issues.append("invalid_application_url")
    if not deadline:
        issues.append("missing_or_invalid_deadline")
    elif is_expired(deadline, now=now):
        issues.append("deadline_expired")
    email = compact(record.get("email") or record.get("application_email"))
    if email and email_domain(email) in BAD_EMAIL_DOMAINS:
        issues.append("free_email_application_channel")
    text_blob = " ".join(compact(record.get(k)) for k in ("application_method", "application_instructions", "requirements_text", "notes"))
    if DISALLOWED_TEXT.search(text_blob):
        issues.append("unsafe_application_channel_or_payment_language")
    checks = record.get("manual_checks") or record.get("review_checks") or {}
    if isinstance(checks, dict):
        required_checks = ["hiring_institution_confirmed", "deadline_confirmed", "application_channel_confirmed", "no_fee_or_payment_required"]
        missing_checks = [k for k in required_checks if checks.get(k) is not True]
        if missing_checks:
            issues.append("manual_checks_incomplete:" + ",".join(missing_checks))
    else:
        issues.append("manual_checks_missing")
    return issues


def reviewed_record_to_vacancy(record: dict, now: str | None = None) -> dict:
    now = now or now_iso()
    title = compact(record.get("title"))
    institution = compact(record.get("institution"))
    source_url = compact(record.get("official_source_url") or record.get("original_url") or record.get("source_url"))
    apply_url = compact(record.get("application_url") or record.get("apply_url") or source_url)
    deadline = parse_deadline(record.get("deadline") or record.get("deadline_iso"))
    source_id = compact(record.get("source_id") or "mygov_government_advertising_agency")
    number_of_vacancies = record.get("number_of_vacancies") or record.get("vacancies")
    try:
        number_of_vacancies = int(number_of_vacancies) if number_of_vacancies not in {None, ""} else None
    except Exception:
        number_of_vacancies = None
    job_family = record.get("job_family") or ["public_sector_reviewed"]
    if isinstance(job_family, str):
        job_family = [job_family]
    rid = stable_id(title, institution, deadline, source_url, prefix="promoted")
    application_mode = compact(record.get("application_mode") or record.get("application_method") or "official_source")
    email = compact(record.get("email") or record.get("application_email")) or None
    return {
        "id": rid,
        "title": title,
        "institution": {
            "name": institution,
            "hiring_body": compact(record.get("hiring_body") or institution),
            "type": compact(record.get("institution_type") or "national_government_or_public_body"),
            "official_domain": domain_of(source_url),
        },
        "source": {
            "name": compact(record.get("source_name") or "Reviewed GAA/MyGov discovery promotion"),
            "url": source_url,
            "source_type": "reviewed_official_discovery",
            "confidence": "official_discovery",
            "last_checked_at": now,
            "http_status": None,
        },
        "advert": {
            "advert_number": compact(record.get("advert_number")) or None,
            "job_scale": compact(record.get("job_scale")) or None,
            "number_of_vacancies": number_of_vacancies,
            "advert_date": parse_deadline(record.get("advert_date"))[:10] if parse_deadline(record.get("advert_date")) else None,
            "deadline": deadline,
            "deadline_confidence": "explicit_manual_review",
        },
        "location": {
            "raw": compact(record.get("location") or "Kenya"),
            "county": record.get("county"),
            "region": "national",
            "duty_station": compact(record.get("duty_station") or record.get("location") or "Kenya"),
        },
        "employment": {
            "type": compact(record.get("employment_type") or "public_sector"),
            "terms": compact(record.get("terms") or record.get("employment_type") or "public_sector"),
            "department": compact(record.get("department")) or None,
        },
        "requirements": {
            "education_minimum": record.get("education_minimum"),
            "kcse_minimum": record.get("kcse_minimum"),
            "years_experience_minimum": record.get("years_experience_minimum"),
            "professional_body": record.get("professional_body"),
            "computer_proficiency_required": bool(record.get("computer_proficiency_required", False)),
            "chapter_six_required": bool(record.get("chapter_six_required", False)),
            "mandatory_text": compact(record.get("requirements_text") or record.get("mandatory_text") or "Manually reviewed GAA/MyGov discovery promotion. Open the original source and confirm before applying."),
        },
        "job_family": job_family,
        "keywords": sorted({w.lower() for w in re.findall(r"[A-Za-z0-9]+", title) if len(w) > 2} | set(job_family)),
        "application": {
            "mode": application_mode,
            "apply_url": apply_url,
            "requires_login": bool(record.get("requires_login", False)),
            "requires_email_submission": bool(email),
            "email": email,
            "fee_required": False,
        },
        "verification": {
            "status": "verified",
            "risk_flags": [],
            "notes": compact(record.get("review_notes") or "Promoted from GAA/MyGov discovery after manual confirmation of institution, deadline and application channel."),
        },
        "raw": {
            "html_hash": None,
            "pdf_url": compact(record.get("attachment_url") or source_url) if str(source_url).lower().endswith(".pdf") else compact(record.get("attachment_url")) or None,
            "screenshot_path": None,
        },
        "links": {
            "view_original_url": source_url,
            "view_original_label": "View original reviewed advert",
            "view_source_url": source_url,
            "view_apply_url": apply_url,
        },
        "provenance": [
            {
                "source_id": source_id,
                "url": source_url,
                "seen_at": now,
                "evidence_type": "manual_reviewed_discovery_promotion",
                "discovery_id": record.get("discovery_id") or record.get("candidate_id"),
                "reviewed_by": record.get("reviewed_by"),
            }
        ],
        "scope": "national_government_or_government_related",
    }


def apply_reviewed_promotions(feed: dict, reviewed_payload: dict, now: str | None = None) -> dict:
    now = now or now_iso()
    reviewed = reviewed_payload.get("reviewed", []) if isinstance(reviewed_payload, dict) else []
    vacancies = list(feed.get("vacancies", []))
    keys = existing_keys(vacancies)
    added, rejected, skipped, duplicates = [], [], [], []
    for idx, record in enumerate(reviewed):
        rec_id = record.get("id") or record.get("candidate_id") or record.get("discovery_id") or f"reviewed[{idx}]"
        decision = compact(record.get("decision") or record.get("promotion_decision") or "promote").lower()
        if decision in {"reject", "rejected", "skip", "hold"}:
            skipped.append({"id": rec_id, "reason": decision})
            continue
        issues = validate_reviewed_record(record)
        if issues:
            rejected.append({"id": rec_id, "issues": issues})
            continue
        vacancy = reviewed_record_to_vacancy(record, now=now)
        key = canonical_pair(vacancy.get("title"), vacancy.get("institution", {}).get("name"), vacancy.get("advert", {}).get("deadline"))
        if key in keys:
            duplicates.append({"id": rec_id, "vacancy_id": vacancy.get("id"), "reason": "duplicate_open_role"})
            continue
        vacancies.append(vacancy)
        keys.add(key)
        added.append(vacancy.get("id"))
    feed["vacancies"] = vacancies
    return {
        "reviewed_total": len(reviewed),
        "added": len(added),
        "added_ids": added,
        "rejected": len(rejected),
        "rejected_records": rejected[:100],
        "skipped": len(skipped),
        "skipped_records": skipped[:100],
        "duplicates": len(duplicates),
        "duplicate_records": duplicates[:100],
    }


def template() -> dict:
    return {
        "version": "3E.1",
        "instructions": "Add manually confirmed discovery candidates here. Only records with decision='promote' and all manual_checks true will enter the open feed.",
        "reviewed": [],
        "example_reviewed_record": {
            "decision": "promote",
            "candidate_id": "promo_example_from_discovery_promotion_candidates",
            "discovery_id": "mygovdisc_example",
            "title": "Example Officer",
            "institution": "Example Public Body",
            "official_source_url": "https://example.go.ke/vacancies/example.pdf",
            "application_url": "https://example.go.ke/careers",
            "deadline": "2030-12-31T23:59:00+03:00",
            "number_of_vacancies": 1,
            "location": "Kenya",
            "job_family": ["administration"],
            "requirements_text": "Paste the reviewed mandatory requirements here.",
            "manual_checks": {
                "hiring_institution_confirmed": True,
                "deadline_confirmed": True,
                "application_channel_confirmed": True,
                "no_fee_or_payment_required": True
            },
            "reviewed_by": "human-reviewer",
            "review_notes": "Confirmed from official PDF/source before promotion."
        }
    }


def load_json(path: str | pathlib.Path, default=None):
    p = pathlib.Path(path)
    if not p.exists():
        return default
    return json.loads(p.read_text(encoding="utf-8"))


def write_json(path: str | pathlib.Path, obj: dict):
    p = pathlib.Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    root = pathlib.Path(__file__).resolve().parents[1]
    feed_path = root / "data" / "public_sector_feed.json"
    reviewed_path = root / "data" / "reviewed_promotions.json"
    feed = load_json(feed_path, {"vacancies": []})
    reviewed = load_json(reviewed_path, template())
    result = apply_reviewed_promotions(feed, reviewed)
    write_json(root / "data" / "promotion_import_report.json", {"generated_at": now_iso(), **result})
    write_json(feed_path, feed)
    print(json.dumps(result, indent=2))
