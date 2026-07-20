from scripts.promotion_importer import apply_reviewed_promotions, validate_reviewed_record


def _reviewed(title="Procurement Officer"):
    return {
        "decision": "promote",
        "title": title,
        "institution": "Example Public Authority",
        "official_source_url": "https://example.go.ke/jobs/procurement-officer.pdf",
        "application_url": "https://example.go.ke/careers",
        "deadline": "2030-08-04T23:59:00+03:00",
        "number_of_vacancies": 1,
        "job_family": ["procurement"],
        "requirements_text": "Bachelor degree and relevant professional qualification.",
        "manual_checks": {
            "hiring_institution_confirmed": True,
            "deadline_confirmed": True,
            "application_channel_confirmed": True,
            "no_fee_or_payment_required": True,
        },
    }


def test_valid_reviewed_record_can_be_imported():
    feed = {"vacancies": []}
    result = apply_reviewed_promotions(feed, {"reviewed": [_reviewed()]})
    assert result["added"] == 1
    assert len(feed["vacancies"]) == 1
    assert feed["vacancies"][0]["verification"]["status"] == "verified"
    assert feed["vacancies"][0]["source"]["confidence"] == "official_discovery"


def test_free_email_reviewed_record_is_rejected():
    rec = _reviewed()
    rec["application_email"] = "apply@gmail.com"
    rec["application_url"] = "mailto:apply@gmail.com"
    issues = validate_reviewed_record(rec)
    assert "free_email_application_channel" in issues


def test_incomplete_manual_checks_rejected():
    rec = _reviewed()
    rec["manual_checks"]["no_fee_or_payment_required"] = False
    result = apply_reviewed_promotions({"vacancies": []}, {"reviewed": [rec]})
    assert result["added"] == 0
    assert result["rejected"] == 1


def test_duplicate_reviewed_record_not_added_twice():
    rec = _reviewed()
    feed = {"vacancies": []}
    first = apply_reviewed_promotions(feed, {"reviewed": [rec]})
    second = apply_reviewed_promotions(feed, {"reviewed": [rec]})
    assert first["added"] == 1
    assert second["duplicates"] == 1
