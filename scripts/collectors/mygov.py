#!/usr/bin/env python3
"""MyGov / Government Advertising Agency vacancy-discovery collector.

Phase 3B improvement:
- Do not assume one brittle MyGov URL. The old /job-adverts path returned 404.
- Try the current GAA job-adverts node first, then known aliases.
- Emit discovery items only; do not promote MyGov/GAA PDF notices directly into open vacancies.
"""
from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

try:
    from ._common import clean_title, fetch_html, now_iso, parse_date, sanitize_keywords, stable_id
except ImportError:  # pragma: no cover
    from _common import clean_title, fetch_html, now_iso, parse_date, sanitize_keywords, stable_id

SOURCE_ID = "mygov_government_advertising_agency"
SOURCE_NAME = "Government Advertising Agency / MyGov Job Adverts"

# Search/manual audit found the current job-adverts table under the GAA domain.
# Keep legacy MyGov paths as fallbacks because the agency has used both domains historically.
CANDIDATE_URLS = [
    "https://gaa.go.ke/index.php/node/445",
    "https://gaa.go.ke/node/445",
    "https://gaa.go.ke/job-adverts",
    "https://www.gaa.go.ke/index.php/node/445",
    "https://www.gaa.go.ke/node/445",
    "https://www.mygov.go.ke/job-adverts",
    "https://mygov.go.ke/job-adverts",
]


def _looks_like_job_adverts_page(html: str) -> bool:
    text = BeautifulSoup(html or "", "html.parser").get_text(" ", strip=True).lower()
    return ("advert attachment" in text and "recruiting agency" in text) or "job adverts" in text


def _pdf_url(href: str | None, base_url: str) -> str | None:
    if not href:
        return None
    href = href.strip()
    if not href or href.startswith(("javascript:", "mailto:", "tel:", "#")):
        return None
    resolved = urljoin(base_url, href)
    if resolved.lower().startswith(("http://", "https://")):
        return resolved
    return None


def _parse_rows(html: str, url: str) -> list[dict]:
    soup = BeautifulSoup(html or "", "html.parser")
    rows: list[dict] = []

    # Primary: Drupal/table rendering. Expected columns include
    # Title | Advert Attachment | Recruiting Agency | Submission Date
    for tr in soup.find_all("tr"):
        cells = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
        if len(cells) < 3:
            continue
        joined = " ".join(cells).lower()
        if "title" in joined and "recruiting agency" in joined:
            continue
        if "advert attachment" in joined and "submission date" in joined:
            continue
        link = tr.find("a", href=True)
        attachment_url = _pdf_url(link.get("href") if link else None, url)
        title = clean_title(cells[0])
        if not title or len(title) < 5:
            continue
        # Usually: title, attachment, recruiting agency, submission date.
        agency = clean_title(cells[-2]) if len(cells) >= 4 else None
        submission = cells[-1] if len(cells) >= 2 else None
        rows.append({
            "title": title,
            "agency": agency,
            "submission_date": submission,
            "attachment_url": attachment_url,
            "source_page_url": url,
        })
    if rows:
        return rows

    # Fallback: parse PDF links, using nearby parent text as a weak row context.
    seen = set()
    for a in soup.find_all("a", href=True):
        attachment_url = _pdf_url(a.get("href"), url)
        if not attachment_url or ".pdf" not in attachment_url.lower():
            continue
        if attachment_url in seen:
            continue
        seen.add(attachment_url)
        text = clean_title(a.get_text(" ", strip=True))
        parent_text = clean_title(a.find_parent().get_text(" ", strip=True) if a.find_parent() else text)
        title = text or re.sub(r"\.pdf$", "", attachment_url.rsplit("/", 1)[-1], flags=re.I)
        if len(title) < 5 and parent_text:
            title = parent_text[:180]
        rows.append({
            "title": title,
            "agency": None,
            "submission_date": None,
            "attachment_url": attachment_url,
            "source_page_url": url,
        })
    return rows


def collect(url: str | None = None, max_items: int = 120) -> tuple[list[dict], dict]:
    candidates = [url] if url else list(CANDIDATE_URLS)
    meta = {
        "source_id": SOURCE_ID,
        "source_name": SOURCE_NAME,
        "url": candidates[0],
        "candidate_urls_tried": [],
        "selected_url": None,
        "http_status": 0,
        "error": None,
        "records_seen": 0,
        "records_emitted": 0,
    }
    best_error = None
    best_status = 0
    rows: list[dict] = []
    selected_url = None

    for candidate in candidates:
        if not candidate:
            continue
        html, status, error = fetch_html(candidate)
        meta["candidate_urls_tried"].append({"url": candidate, "http_status": status, "error": error})
        best_status = status or best_status
        if error:
            best_error = error
            continue
        parsed = _parse_rows(html, candidate)
        if parsed or _looks_like_job_adverts_page(html):
            rows = parsed[:max_items]
            selected_url = candidate
            break

    if not selected_url:
        meta.update({
            "http_status": best_status,
            "error": best_error or "No reachable MyGov/GAA job-adverts page produced parseable rows.",
            "records_seen": 0,
            "records_emitted": 0,
        })
        return [], meta

    items = []
    for r in rows:
        title = clean_title(r.get("title"))
        if not title:
            continue
        attachment_url = r.get("attachment_url") or r.get("source_page_url") or selected_url
        agency = clean_title(r.get("agency") or "Government Advertising Agency / MyGov")
        submission_date = parse_date(r.get("submission_date"))
        items.append({
            "id": stable_id(title, agency, attachment_url, prefix="mygovdisc"),
            "title": title,
            "institution": agency,
            "source_id": SOURCE_ID,
            "source_name": SOURCE_NAME,
            "source_url": selected_url,
            "source_confidence": "official_discovery",
            "verification_status": "needs_review",
            "review_reason": "MyGov/GAA discovery item. Cross-check the PDF and hiring institution before adding to open roles.",
            "submission_date": submission_date,
            "attachment_url": attachment_url,
            "view_original_url": attachment_url,
            "keywords": sanitize_keywords(title, agency),
            "seen_at": now_iso(),
        })

    meta.update({
        "url": selected_url,
        "selected_url": selected_url,
        "http_status": 200,
        "error": None,
        "records_seen": len(rows),
        "records_emitted": len(items),
    })
    return items, meta


if __name__ == "__main__":  # pragma: no cover
    import json
    print(json.dumps(collect()[0], indent=2, ensure_ascii=False))
