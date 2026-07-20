#!/usr/bin/env python3
"""MyGov/GAA job-adverts discovery collector.

MyGov is used as a central government-advertising discovery layer. Items are emitted to the
review/discovery queue unless the hiring institution's official application source is resolved by a
later collector. This prevents old or PDF-only discovery items from polluting the live vacancy feed.
"""
from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

try:
    from ._common import clean_title, fetch_html, now_iso, parse_date, sanitize_keywords, stable_id
except ImportError:  # pragma: no cover
    from _common import clean_title, fetch_html, now_iso, parse_date, sanitize_keywords, stable_id

MYGOV_JOB_ADVERTS_URL = "https://www.mygov.go.ke/job-adverts"


def _parse_rows(html: str, url: str = MYGOV_JOB_ADVERTS_URL) -> list[dict]:
    soup = BeautifulSoup(html or "", "html.parser")
    rows = []
    # The site renders a table. Use <tr> if available.
    for tr in soup.find_all("tr"):
        cells = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
        if len(cells) < 3:
            continue
        joined = " ".join(cells).lower()
        if "title" in joined and "recruiting agency" in joined:
            continue
        link = tr.find("a", href=True)
        pdf_url = urljoin(url, link["href"]) if link else None
        title = cells[0]
        agency = cells[-2] if len(cells) >= 4 else None
        submission = cells[-1]
        if not title or len(title) < 5:
            continue
        rows.append({"title": title, "agency": agency, "submission_date": submission, "attachment_url": pdf_url})
    if rows:
        return rows
    # Fallback for text extraction: use links to PDFs around likely titles.
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(" ", strip=True)
        if not href.lower().endswith(".pdf") or not text:
            continue
        rows.append({
            "title": re.sub(r"\.pdf$", "", text, flags=re.I),
            "agency": None,
            "submission_date": None,
            "attachment_url": urljoin(url, href),
        })
    return rows


def collect(url: str = MYGOV_JOB_ADVERTS_URL, max_items: int = 80) -> tuple[list[dict], dict]:
    html, status, error = fetch_html(url)
    meta = {
        "source_id": "mygov_government_advertising_agency",
        "source_name": "Government Advertising Agency / MyGov Job Adverts",
        "url": url,
        "http_status": status,
        "error": error,
        "records_seen": 0,
        "records_emitted": 0,
    }
    if error:
        return [], meta
    rows = _parse_rows(html, url)[:max_items]
    items = []
    for r in rows:
        title = clean_title(r.get("title"))
        if not title:
            continue
        pdf_url = r.get("attachment_url") or url
        agency = clean_title(r.get("agency") or "Government Advertising Agency / MyGov")
        submission_date = parse_date(r.get("submission_date"))
        items.append({
            "id": stable_id(title, agency, pdf_url, prefix="mygovdisc"),
            "title": title,
            "institution": agency,
            "source_id": "mygov_government_advertising_agency",
            "source_name": "Government Advertising Agency / MyGov Job Adverts",
            "source_url": url,
            "source_confidence": "official_discovery",
            "verification_status": "needs_review",
            "review_reason": "MyGov/GAA advert discovery item. Cross-check with the hiring institution or original PDF before treating as an open role.",
            "submission_date": submission_date,
            "attachment_url": pdf_url,
            "view_original_url": pdf_url,
            "keywords": sanitize_keywords(title, agency),
            "seen_at": now_iso(),
        })
    meta["records_seen"] = len(rows)
    meta["records_emitted"] = len(items)
    return items, meta


if __name__ == "__main__":  # pragma: no cover
    import json
    print(json.dumps(collect()[0], indent=2, ensure_ascii=False))
