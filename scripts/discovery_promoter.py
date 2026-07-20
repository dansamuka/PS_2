#!/usr/bin/env python3
"""Discovery promotion helpers for PS_2.

Phase 3D converts GAA/MyGov discovery records into a structured promotion workbench.
It does NOT automatically publish discovery items as open roles. It prepares reviewable
role candidates, identifies missing fields, and supports a separate manually reviewed
promotion file for later use.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import pathlib
import re
from collections import Counter
from urllib.parse import urlparse

EAT = dt.timezone(dt.timedelta(hours=3))

ROLE_WORDS = re.compile(
    r"\b(commissioner|director|manager|officer|assistant|accountant|auditor|engineer|technician|artisan|driver|clerk|secretary|analyst|specialist|attendant|warden|cook|waiter|chef|operator|lecturer|professor|researcher|registrar|counsel|legal|procurement|supply|finance|human resource|ict|information communication|intern|graduate trainee)\b",
    re.I,
)
INSTITUTION_HINTS = [
    (r"\bKRA\b|Kenya Revenue Authority", "Kenya Revenue Authority (KRA)"),
    (r"Commission for University Education|\bCUE\b", "Commission for University Education (CUE)"),
    (r"Ministry of Water", "Ministry of Water, Sanitation and Irrigation"),
    (r"Kenya School of Government|\bKSG\b", "Kenya School of Government"),
    (r"Public Service Commission|\bPSC\b", "Public Service Commission"),
    (r"Teachers Service Commission|\bTSC\b", "Teachers Service Commission"),
    (r"Ethics and Anti-Corruption Commission|\bEACC\b", "Ethics and Anti-Corruption Commission"),
    (r"Kenya National Highways Authority|\bKeNHA\b", "Kenya National Highways Authority"),
    (r"Kenya Ports Authority|\bKPA\b", "Kenya Ports Authority"),
    (r"Kenya Airports Authority|\bKAA\b", "Kenya Airports Authority"),
]

DATE_PATTERNS = [
    re.compile(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})"),
    re.compile(r"(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+),?\s+(\d{4})", re.I),
]
MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9, "oct": 10, "october": 10,
    "nov": 11, "november": 11, "dec": 12, "december": 12,
}


def compact(value: str | None) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def stable_id(*parts: object, prefix: str = "discrole") -> str:
    raw = "|".join(compact(str(p)).lower() for p in parts if p is not None)
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]
    slug = re.sub(r"[^a-z0-9]+", "_", raw.split("|")[0])[:52].strip("_") or prefix
    return f"{prefix}_{slug}_{digest}"


def parse_date_from_text(text: str | None) -> str | None:
    text = compact(text)
    if not text:
        return None
    m = DATE_PATTERNS[0].search(text)
    if m:
        y, mo, da = map(int, m.groups())
        try:
            return dt.datetime(y, mo, da, 23, 59, tzinfo=EAT).isoformat(timespec="seconds")
        except ValueError:
            return None
    m = DATE_PATTERNS[1].search(text)
    if m:
        da = int(m.group(1))
        mo = MONTHS.get(m.group(2).lower())
        y = int(m.group(3))
        if mo:
            try:
                return dt.datetime(y, mo, da, 23, 59, tzinfo=EAT).isoformat(timespec="seconds")
            except ValueError:
                return None
    return None


def infer_institution(title: str, supplied: str | None) -> str:
    supplied = compact(supplied)
    title = compact(title)
    if supplied and supplied.lower() not in {"government advertising agency / mygov", "gaa", "mygov"}:
        return supplied
    for pat, value in INSTITUTION_HINTS:
        if re.search(pat, title, re.I):
            return value
    m = re.search(r"(?:at|for|under)\s+(?:the\s+)?([A-Z][A-Za-z &(),.'/-]{4,120})", title)
    if m:
        candidate = compact(m.group(1))
        candidate = re.split(r"\b(vacanc|career|job|opportunit)", candidate, flags=re.I)[0].strip(" -–—")
        if candidate:
            return candidate
    return supplied or "Hiring institution to confirm"


def split_possible_roles(title: str) -> list[str]:
    title = compact(title)
    if not title:
        return []
    # Remove common wrapping language while retaining the named roles.
    cleaned = re.sub(r"\b(Career|Job)\s+Opportunit(?:y|ies)\b", "", title, flags=re.I)
    cleaned = re.sub(r"\b(Vacancy|Vacancies|Advertisement|Advert)\b", "", cleaned, flags=re.I)
    cleaned = compact(cleaned.strip(" -–—"))

    # Split only when both sides still look like role titles. Avoid over-splitting institution names.
    parts = [p.strip(" -–—") for p in re.split(r"\s+(?:and|&)\s+", cleaned) if p.strip()]
    if len(parts) > 1 and all(ROLE_WORDS.search(p) for p in parts):
        return [compact(p) for p in parts]
    return [cleaned]


def existing_identity_set(vacancies: list[dict]) -> set[tuple[str, str]]:
    out = set()
    for v in vacancies or []:
        title = compact(v.get("title")).lower()
        inst = compact((v.get("institution") or {}).get("name")).lower()
        if title and inst:
            out.add((title, inst))
    return out


def candidate_from_review(item: dict, vacancies: list[dict] | None = None) -> list[dict]:
    vacancies = vacancies or []
    existing = existing_identity_set(vacancies)
    title = compact(item.get("title"))
    institution = infer_institution(title, item.get("institution"))
    url = item.get("view_original_url") or item.get("attachment_url") or item.get("source_url")
    attachment = item.get("attachment_url") or url
    roles = split_possible_roles(title)
    out = []
    for role_title in roles:
        role_title = compact(role_title)
        if not role_title or len(role_title) < 4:
            continue
        has_role = bool(ROLE_WORDS.search(role_title))
        deadline = parse_date_from_text(title)
        missing = []
        if not has_role:
            missing.append("specific_role_title")
        if not institution or institution == "Hiring institution to confirm":
            missing.append("hiring_institution")
        if not deadline:
            missing.append("deadline")
        if not url:
            missing.append("original_pdf_or_source_url")
        duplicate_open_role = (role_title.lower(), institution.lower()) in existing
        if duplicate_open_role:
            missing.append("duplicate_check_against_open_feed")
        confidence = 40
        if str(url or "").lower().endswith(".pdf"):
            confidence += 20
        if item.get("source_confidence") in {"official", "official_discovery"}:
            confidence += 20
        if has_role:
            confidence += 10
        if institution and institution != "Hiring institution to confirm":
            confidence += 10
        status = "ready_for_manual_confirmation" if len(missing) <= 1 and not duplicate_open_role else "needs_extraction_or_review"
        out.append({
            "id": stable_id(role_title, institution, url, prefix="promo"),
            "discovery_id": item.get("id"),
            "title": role_title,
            "institution": institution,
            "source_id": item.get("source_id"),
            "source_confidence": item.get("source_confidence"),
            "original_url": url,
            "attachment_url": attachment,
            "deadline_detected": deadline,
            "promotion_status": status,
            "can_enter_open_feed": False,
            "needs_manual_review": True,
            "duplicate_open_role": duplicate_open_role,
            "confidence_score": min(100, confidence),
            "missing_fields": missing,
            "review_actions": [
                "Open the PDF/original source and confirm the hiring institution.",
                "Extract exact role title(s), deadline, vacancies, requirements and application method.",
                "Confirm the application channel is official and does not require payment.",
                "Only then copy a reviewed record into data/reviewed_promotions.json.",
            ],
        })
    return out


def build_promotion_workbench(discovery_review: dict, vacancies: list[dict] | None = None) -> dict:
    candidates = []
    for item in discovery_review.get("items", []) if isinstance(discovery_review, dict) else []:
        candidates.extend(candidate_from_review(item, vacancies or []))
    candidates.sort(key=lambda x: (x["promotion_status"] != "ready_for_manual_confirmation", -x["confidence_score"], x["institution"], x["title"]))
    counts = Counter(c["promotion_status"] for c in candidates)
    ready = [c for c in candidates if c["promotion_status"] == "ready_for_manual_confirmation"]
    return {
        "version": "3D.1",
        "policy": "Discovery candidates remain outside open vacancies until manually reviewed. This file is a promotion workbench, not an open-role feed.",
        "generated_count": len(candidates),
        "ready_for_manual_confirmation": len(ready),
        "status_counts": dict(counts),
        "candidates": candidates,
    }


def reviewed_promotions_template() -> dict:
    return {
        "version": "3D.1",
        "instructions": "Add manually confirmed discovery records here. The refresh script will not auto-promote GAA/MyGov discovery items without reviewed records.",
        "reviewed": []
    }


def write_json(path: str | pathlib.Path, obj: dict):
    p = pathlib.Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")
