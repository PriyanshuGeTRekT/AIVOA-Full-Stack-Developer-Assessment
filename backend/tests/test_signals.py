"""Trend / quality-signal tests."""

from app import crud
from app.services.processing import process_complaint
from app.services.signals import TREND_THRESHOLD, detect_signals


def _make(db, text: str):
    c = crud.create_complaint(db, source_text=text, channel="test")
    return process_complaint(db, c)


def test_batch_signal_when_threshold_met(db_session):
    text = (
        "Amoxicillin 500mg capsules from batch AMX-SIG-001 had dark specks "
        "inside capsules. Reported by Test Pharmacy."
    )
    for _ in range(TREND_THRESHOLD):
        _make(db_session, text)

    signals = detect_signals(db_session)
    batch_signals = [s for s in signals if s["kind"] == "batch"]
    assert any("AMX-SIG-001" in s["label"] for s in batch_signals)
    assert any(s["count"] >= TREND_THRESHOLD for s in batch_signals)


def test_no_signal_below_threshold(db_session):
    text = (
        "Metformin 850mg tablets batch MET-SIG-009 seal broken. "
        "Reported by distributor QA."
    )
    _make(db_session, text)
    _make(db_session, text)

    signals = detect_signals(db_session)
    assert not any("MET-SIG-009" in s["label"] for s in signals)
