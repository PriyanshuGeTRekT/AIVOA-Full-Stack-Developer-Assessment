"""Cross complaint trend and signal detection.

Duplicate detection answers "have we seen this exact complaint before". Trending
answers a different and arguably more important question: "are several separate
complaints pointing at the same underlying problem". GMP requires complaints to
be trended for exactly this reason, because a cluster of individually minor
events on one batch can be the first sign of a systemic failure or a recall.

This runs on demand over the stored complaints rather than at intake, because a
signal only becomes visible once enough related records exist. It is deliberately
simple and deterministic; the value is in surfacing the pattern, not in fancy
statistics.
"""

from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Complaint

# A signal needs at least this many related complaints inside the window.
TREND_THRESHOLD = 3
WINDOW_DAYS = 90

_RISK_ORDER = {"Critical": 3, "Major": 2, "Minor": 1, None: 0}


def _window_start() -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=WINDOW_DAYS)


def _recent_complaints(db: Session) -> list[Complaint]:
    stmt = select(Complaint).where(Complaint.processing_state == "done")
    return [c for c in db.scalars(stmt) if _in_window(c)]


def _in_window(complaint: Complaint) -> bool:
    created = complaint.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    return created >= _window_start()


def _highest_risk(complaints: list[Complaint]) -> str | None:
    return max((c.risk_level for c in complaints), key=lambda r: _RISK_ORDER.get(r, 0), default=None)


def _build_signal(kind: str, label: str, members: list[Complaint]) -> dict:
    members = sorted(members, key=lambda c: c.created_at)
    severity = _highest_risk(members)
    return {
        "kind": kind,
        "label": label,
        "count": len(members),
        "severity": severity,
        "product_name": members[0].product_name,
        "batch_number": members[0].batch_number if kind == "batch" else None,
        "complaint_type": members[0].complaint_type if kind == "product_defect" else None,
        "references": [c.reference for c in members],
        "complaint_ids": [c.id for c in members],
        "recommendation": _recommendation(kind, severity),
    }


def _recommendation(kind: str, severity: str | None) -> str:
    if kind == "batch":
        base = (
            "Multiple complaints reference this batch. Open a batch level quality "
            "investigation and review the batch record."
        )
    else:
        base = (
            "A recurring defect pattern is emerging for this product. Consider a "
            "product level review and effectiveness check of any prior CAPA."
        )
    if severity == "Critical":
        base += " Assess the need for a recall and expedited regulatory reporting."
    return base


def detect_signals(db: Session) -> list[dict]:
    """Return quality signals for batches and product/defect combinations."""
    complaints = _recent_complaints(db)

    by_batch: dict[str, list[Complaint]] = defaultdict(list)
    by_product_defect: dict[tuple, list[Complaint]] = defaultdict(list)

    for complaint in complaints:
        if complaint.batch_number:
            by_batch[complaint.batch_number.upper()].append(complaint)
        if complaint.product_name and complaint.complaint_type:
            key = (complaint.product_name.lower(), complaint.complaint_type)
            by_product_defect[key].append(complaint)

    signals: list[dict] = []

    for batch, members in by_batch.items():
        if len(members) >= TREND_THRESHOLD:
            product = members[0].product_name or "Unknown product"
            signals.append(_build_signal("batch", f"{product} - batch {batch}", members))

    for (_, defect), members in by_product_defect.items():
        if len(members) >= TREND_THRESHOLD:
            product = members[0].product_name or "Unknown product"
            signals.append(_build_signal("product_defect", f"{product} - {defect}", members))

    # Most serious and largest clusters first.
    signals.sort(key=lambda s: (_RISK_ORDER.get(s["severity"], 0), s["count"]), reverse=True)
    return signals


def related_complaints(db: Session, complaint: Complaint) -> dict:
    """Complaints that share this one's batch, for the detail view."""
    if not complaint.batch_number:
        return {"batch_number": None, "count": 0, "references": []}

    stmt = select(Complaint).where(
        Complaint.batch_number == complaint.batch_number,
        Complaint.id != complaint.id,
    )
    siblings = list(db.scalars(stmt))
    return {
        "batch_number": complaint.batch_number,
        "count": len(siblings),
        "references": [
            {"id": c.id, "reference": c.reference, "risk_level": c.risk_level}
            for c in sorted(siblings, key=lambda c: c.created_at)
        ],
    }
