from scripts.role_identity import build_reconciled_change_summary, is_generic_listing_title, role_identity_key


def _role(vid, title):
    return {
        "id": vid,
        "title": title,
        "institution": {"name": "Kenya School of Government"},
        "advert": {"deadline": "2026-08-04T23:59:00+03:00"},
        "location": {"raw": "Mombasa, Tsavo East, Tsavo West"},
        "source": {"confidence": "needs_review"},
        "verification": {"status": "needs_review"},
        "links": {"view_original_url": "https://jobapplications.ke/"},
        "provenance": [{"source_id": "ksg_jobapplications"}],
    }


def test_ksg_old_and_live_ids_reconcile_same_role_identity():
    old = _role("ksg_2026_artisan_i_rac_technician", "Artisan I (RAC Technician)")
    new = _role("ksg_airtisan_i_rac_techhnician_2026_08_04_fbd3ce6886e0", "Airtisan I Rac Techhnician")
    assert role_identity_key(old) == role_identity_key(new)
    summary = build_reconciled_change_summary([old], [new])
    assert summary["genuine_new_roles"] == 0
    assert summary["genuine_removed_roles"] == 0
    assert summary["identity_reconciled_roles"] == 1


def test_generic_ksg_advert_heading_is_not_a_role():
    assert is_generic_listing_title("Advertised Vacancies Mombasa Tsavo East Tsavo West 2026")
