# Phase 3A — PSCIMS postback-link hotfix

## Problem

A live GitHub Actions run reached the PSCIMS table, but PSCIMS exposed role-detail links as ASP.NET pseudo-links such as:

```text
javascript:__doPostBack('DataGrid2$ctl06$LinkButton3','')
```

Those links work only inside the browser form state. They are not valid `http(s)` URLs, so `validate_public_sector_feed.py` correctly failed the refresh.

## Fix

- `scripts/collectors/pscims.py` now ignores `javascript:`, `#`, `mailto:` and `tel:` row links.
- PSCIMS rows without a direct HTTP detail link now use the official PSCIMS active-adverts page as `links.view_original_url`.
- `scripts/refresh_public_sector_feed.py` now sanitises existing or generated `view_original_url` values and replaces invalid pseudo-links with a safe source/application URL.

## Expected result

The next GitHub Actions run should pass validation. PSCIMS roles will still show **View original role**, but the link will open the official PSCIMS active-adverts page rather than an unusable postback pseudo-link.
