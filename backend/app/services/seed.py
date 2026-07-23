"""Insert sample complaints when the DB is empty (first boot)."""

import logging

from sqlalchemy.orm import Session

from app import crud
from app.models import Complaint
from app.services.processing import process_complaint

logger = logging.getLogger(__name__)

SAMPLE_COMPLAINTS = [
    {
        "channel": "email",
        "text": (
            "Subject: Foreign particles in Amoxicillin 500mg capsules\n\n"
            "Dear Quality team,\n"
            "Our pharmacy received a bottle of Amoxicillin 500mg capsules, batch "
            "AMX-2405-118, and several capsules contain visible black specks. "
            "A patient noticed the particles before taking the medicine and returned "
            "the bottle. Please advise on next steps.\n"
            "Regards, Sunrise Pharmacy, contact: pharmacist@sunrisepharma.com"
        ),
    },
    # Same batch as above so seed data triggers a quality signal.
    {
        "channel": "web_form",
        "text": (
            "Amoxicillin 500mg capsules from batch AMX-2405-118 had dark specks "
            "inside two of the capsules. Reported by Green Cross Pharmacy, "
            "contact: qa@greencrossrx.com"
        ),
    },
    {
        "channel": "email",
        "text": (
            "Subject: Black particles again in Amoxicillin\n\n"
            "A customer returned Amoxicillin 500mg capsules, lot AMX-2405-118, "
            "reporting tiny black particles in the powder inside the capsule shell. "
            "No illness reported. Reported by Northside Chemists."
        ),
    },
    {
        "channel": "web_form",
        "text": (
            "The blister pack of Metformin 850mg tablets (Lot MET-2312-04) arrived "
            "with a broken seal and two of the pockets were empty. The carton also "
            "looked crushed on delivery. Reported by distributor QA."
        ),
    },
    {
        "channel": "email",
        "text": (
            "Subject: Adverse reaction after Atorvastatin\n\n"
            "A patient developed a severe skin rash and was hospitalised after taking "
            "Atorvastatin 20mg from batch ATV-2401-77. The prescriber is asking whether "
            "this is a known issue with the batch. Please treat as urgent.\n"
            "Contact: dr.mehta@cityhospital.org"
        ),
    },
    {
        "channel": "web_form",
        "text": (
            "Label on Pantoprazole 40mg carton shows the wrong expiry date compared to "
            "the blister foil. Batch PAN-2403-22. Customer is confused about which date "
            "to trust."
        ),
    },
]


def seed_if_empty(db: Session) -> None:
    already = db.query(Complaint).count()
    if already:
        return

    logger.info("Seeding %d sample complaints", len(SAMPLE_COMPLAINTS))
    for item in SAMPLE_COMPLAINTS:
        complaint = crud.create_complaint(db, source_text=item["text"], channel=item["channel"])
        process_complaint(db, complaint)
