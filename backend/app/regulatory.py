"""Regulatory timelines and deadlines.

The one thing a pharma complaint team cannot afford to get wrong is a missed
mandatory reporting deadline. This module keeps that logic in one deterministic,
testable place, separate from any AI. The AI decides *what kind* of event this
is; these pure functions decide *by when* it must be actioned.

The specific windows below are realistic defaults, not legal advice. A real
deployment would drive them from the site's SOPs, which is exactly why they live
here as named constants rather than being scattered through the code.
"""

from datetime import datetime, timedelta, timezone

# Report categories the reportability node can assign.
REPORT_FIELD_ALERT = "FDA Field Alert Report"
REPORT_PHARMACOVIGILANCE = "Pharmacovigilance / Adverse Event"
REPORT_NONE = "None"

# Regulatory clocks.
#   Field Alert Report: 21 CFR 314.81 requires submission within 3 working days
#   of receiving information about a distributed product defect.
#   Expedited ADR reporting is commonly 15 calendar days for serious cases.
FIELD_ALERT_WORKING_DAYS = 3
PHARMACOVIGILANCE_CALENDAR_DAYS = 15

# Internal investigation SLA by risk level (calendar days, except Critical which
# we treat as working days so a weekend does not eat most of the window).
INVESTIGATION_SLA = {
    "Critical": ("working", 3),
    "Major": ("calendar", 20),
    "Minor": ("calendar", 30),
}


def _as_utc(value: datetime) -> datetime:
    """Make a datetime timezone aware so arithmetic and comparisons are safe."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def add_working_days(start: datetime, days: int) -> datetime:
    """Return start plus a number of working days, skipping weekends."""
    current = _as_utc(start)
    remaining = days
    while remaining > 0:
        current = current + timedelta(days=1)
        if current.weekday() < 5:  # Monday is 0, Saturday is 5.
            remaining -= 1
    return current


def report_due_date(report_type: str | None, received_at: datetime) -> datetime | None:
    """When a regulatory report is due, or None if the event is not reportable."""
    if report_type == REPORT_FIELD_ALERT:
        return add_working_days(received_at, FIELD_ALERT_WORKING_DAYS)
    if report_type == REPORT_PHARMACOVIGILANCE:
        return _as_utc(received_at) + timedelta(days=PHARMACOVIGILANCE_CALENDAR_DAYS)
    return None


def investigation_due_date(risk_level: str | None, received_at: datetime) -> datetime | None:
    """Internal investigation deadline based on the assessed risk level."""
    rule = INVESTIGATION_SLA.get(risk_level or "")
    if rule is None:
        return None
    kind, amount = rule
    if kind == "working":
        return add_working_days(received_at, amount)
    return _as_utc(received_at) + timedelta(days=amount)


def days_until(due_at: datetime | None, now: datetime | None = None) -> int | None:
    """Whole days from now until a deadline. Negative means overdue."""
    if due_at is None:
        return None
    reference = _as_utc(now) if now else datetime.now(timezone.utc)
    delta = _as_utc(due_at) - reference
    # Round toward zero in a way that reads naturally: 0 means "due today".
    return int(delta.total_seconds() // 86400)
