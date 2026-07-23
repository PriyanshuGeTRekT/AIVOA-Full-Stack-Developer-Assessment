"""Heuristic-path agent tests (no Groq key)."""

from app.agent import nodes
from app.agent.graph import run_pipeline


def test_batch_parsing_handles_lot_number_label():
    # "Lot number:" should not be mistaken for the code itself.
    assert nodes._find_batch("Batch / Lot number: AZI-2404-158") == "AZI-2404-158"
    assert nodes._find_batch("batch AMX-2405-118") == "AMX-2405-118"
    assert nodes._find_batch("Lot MET-2312-04") == "MET-2312-04"


def test_risk_keyword_respects_word_boundaries():
    # "pharmacist" contains "harm" but must not trigger a critical rating.
    level, _ = nodes._risk_heuristic(
        {"description": "routine query"}, "Reported by the pharmacist on duty."
    )
    assert level == "Minor"


def test_risk_heuristic_handles_negation():
    level, _ = nodes._risk_heuristic(
        {"description": "cracked tablet"}, "No adverse effect was reported."
    )
    assert level == "Minor"


def test_reportability_flags_adverse_event():
    reportable, report_type, _ = nodes._reportability_heuristic(
        {"complaint_type": "Adverse Event"},
        "Patient hospitalised with a severe rash after taking the tablets.",
    )
    assert reportable is True
    assert report_type == "Pharmacovigilance / Adverse Event"


def test_reportability_flags_contamination_as_field_alert():
    reportable, report_type, _ = nodes._reportability_heuristic(
        {"complaint_type": "Contamination"},
        "Visible microbial contamination found in the distributed bottles.",
    )
    assert reportable is True
    assert report_type == "FDA Field Alert Report"


def test_full_pipeline_produces_expected_shape():
    result = run_pipeline(
        "Amoxicillin 500mg capsules, batch AMX-2405-118, contain black particles.", []
    )
    assert result["extracted"]["product_name"] == "Amoxicillin"
    assert result["extracted"]["batch_number"] == "AMX-2405-118"
    assert result["risk_level"] in {"Critical", "Major", "Minor"}
    assert result["report_type"] in {
        "FDA Field Alert Report",
        "Pharmacovigilance / Adverse Event",
        "None",
    }
    assert result["summary"]


def test_duplicate_score_never_exceeds_one():
    existing = [
        {
            "id": 1,
            "product_name": "Amoxicillin",
            "batch_number": "AMX-2405-118",
            "description": "Amoxicillin 500mg capsules, batch AMX-2405-118, contain black particles.",
        }
    ]
    result = run_pipeline(
        "Amoxicillin 500mg capsules, batch AMX-2405-118, contain black particles.", existing
    )
    assert 0.0 <= result["duplicate_score"] <= 1.0
    assert result["duplicate_of"] == 1
    assert "duplicate" in (result.get("root_cause") or "").lower()


def test_completeness_requires_complainant_name():
    result = nodes._completeness_heuristic(
        {
            "product_name": "Amoxicillin",
            "batch_number": "AMX-1",
            "complaint_type": "Foreign Particle",
            "description": "Black particles visible in capsules.",
            "complainant_name": None,
        }
    )
    assert result["is_complete"] is False
    assert "Complainant name" in result["missing_fields"]
