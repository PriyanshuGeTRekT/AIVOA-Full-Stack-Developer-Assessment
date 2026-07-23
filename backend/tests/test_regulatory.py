"""Tests for the deadline math.

These deadlines are the highest stakes logic in the app, so they are the part
most worth pinning down with tests. Everything here is pure and deterministic.
"""

from datetime import datetime, timezone

from app import regulatory as reg


def dt(year, month, day):
    return datetime(year, month, day, 9, 0, tzinfo=timezone.utc)


def test_add_working_days_skips_weekend():
    # Friday 2026-07-24 + 3 working days lands on Wednesday 2026-07-29.
    result = reg.add_working_days(dt(2026, 7, 24), 3)
    assert result.date() == dt(2026, 7, 29).date()


def test_add_working_days_within_week():
    # Monday + 2 working days is Wednesday, no weekend involved.
    result = reg.add_working_days(dt(2026, 7, 20), 2)
    assert result.date() == dt(2026, 7, 22).date()


def test_field_alert_uses_working_days():
    due = reg.report_due_date(reg.REPORT_FIELD_ALERT, dt(2026, 7, 24))
    assert due.date() == dt(2026, 7, 29).date()


def test_pharmacovigilance_uses_calendar_days():
    due = reg.report_due_date(reg.REPORT_PHARMACOVIGILANCE, dt(2026, 7, 24))
    assert due.date() == dt(2026, 8, 8).date()


def test_no_report_has_no_deadline():
    assert reg.report_due_date(reg.REPORT_NONE, dt(2026, 7, 24)) is None
    assert reg.report_due_date(None, dt(2026, 7, 24)) is None


def test_investigation_sla_by_risk():
    assert reg.investigation_due_date("Critical", dt(2026, 7, 24)).date() == dt(2026, 7, 29).date()
    assert reg.investigation_due_date("Major", dt(2026, 7, 24)).date() == dt(2026, 8, 13).date()
    assert reg.investigation_due_date("Minor", dt(2026, 7, 24)).date() == dt(2026, 8, 23).date()
    assert reg.investigation_due_date(None, dt(2026, 7, 24)) is None


def test_days_until_is_negative_when_overdue():
    assert reg.days_until(dt(2026, 7, 20), now=dt(2026, 7, 24)) == -4
    assert reg.days_until(dt(2026, 7, 30), now=dt(2026, 7, 24)) == 6
    assert reg.days_until(None) is None
