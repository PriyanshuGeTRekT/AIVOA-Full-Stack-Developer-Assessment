"""Deadline helpers for reportability and investigation SLAs.

Kept pure and free of LLM calls so due dates stay testable. Numbers are demo
defaults, not legal advice; real sites would load them from SOPs.
"""

from datetime import datetime, timedelta, timezone

REPORT_FIELD_ALERT = "FDA Field Alert Report"
REPORT_PHARMACOVIGILANCE = "Pharmacovigilance / Adverse Event"
REPORT_NONE = "None"

# Field Alert: 21 CFR 314.81 style window (working days).
FIELD_ALERT_WORKING_DAYS = 3
# Common expedited ADR window (calendar days).
PHARMACOVIGILANCE_CALENDAR_DAYS = 15

INVESTIGATION_SLA = {
    "Critical": ("working", 3),
    "Major": ("calendar", 20),
    "Minor": ("calendar", 30),
}


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def add_working_days(start: datetime, days: int) -> datetime:
    """Add N working days (skip Sat/Sun)."""
    current = _as_utc(start)
    remaining = days
    while remaining > 0:
        current = current + timedelta(days=1)
        if current.weekday() < 5:
            remaining -= 1
    return current


def report_due_date(report_type: str | None, received_at: datetime) -> datetime | None:
    if report_type == REPORT_FIELD_ALERT:
        return add_working_days(received_at, FIELD_ALERT_WORKING_DAYS)
    if report_type == REPORT_PHARMACOVIGILANCE:
        return _as_utc(received_at) + timedelta(days=PHARMACOVIGILANCE_CALENDAR_DAYS)
    return None


def investigation_due_date(risk_level: str | None, received_at: datetime) -> datetime | None:
    rule = INVESTIGATION_SLA.get(risk_level or "")
    if rule is None:
        return None
    kind, amount = rule
    if kind == "working":
        return add_working_days(received_at, amount)
    return _as_utc(received_at) + timedelta(days=amount)


def days_until(due_at: datetime | None, now: datetime | None = None) -> int | None:
    """Whole days until due. Negative means overdue. None if no deadline."""
    if due_at is None:
        return None
    reference = _as_utc(now) if now else datetime.now(timezone.utc)
    delta = _as_utc(due_at) - reference
    return int(delta.total_seconds() // 86400)
