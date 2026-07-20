import importlib
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]


def test_ksg_import_from_scripts_path():
    sys.path.insert(0, str(ROOT / "scripts"))
    mod = importlib.import_module("collectors.ksg")
    assert hasattr(mod, "collect")


def test_discovery_promotion_candidate_builds_without_auto_publish():
    sys.path.insert(0, str(ROOT / "scripts"))
    promoter = importlib.import_module("discovery_promoter")
    review = {
        "items": [{
            "id": "d1",
            "title": "Deputy Commissioner Audit and Risk Career Opportunity at KRA",
            "institution": "Kenya Revenue Authority (KRA)",
            "source_id": "mygov_government_advertising_agency",
            "source_confidence": "official_discovery",
            "view_original_url": "https://gaa.go.ke/sample.pdf",
            "attachment_url": "https://gaa.go.ke/sample.pdf",
        }]
    }
    wb = promoter.build_promotion_workbench(review, [])
    assert wb["generated_count"] >= 1
    assert all(c["can_enter_open_feed"] is False for c in wb["candidates"])
    assert all(c["needs_manual_review"] for c in wb["candidates"])
