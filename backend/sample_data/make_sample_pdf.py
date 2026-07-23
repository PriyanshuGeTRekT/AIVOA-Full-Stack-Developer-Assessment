"""Generate a realistic complaint PDF for the upload demo.

Run this once to produce complaint_form.pdf, then upload that file through the
UI to show the PDF text extraction path. reportlab is only needed for this
helper, so it is not in the main requirements.

    pip install reportlab
    python make_sample_pdf.py
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

LINES = [
    ("Helvetica-Bold", 15, "CUSTOMER COMPLAINT FORM"),
    ("Helvetica", 10, "Acme Pharmaceuticals - Quality Assurance Department"),
    ("Helvetica", 10, ""),
    ("Helvetica-Bold", 11, "Complaint reference (external): RX-CMP-2026-3391"),
    ("Helvetica", 11, "Date received: 21 July 2026"),
    ("Helvetica", 11, ""),
    ("Helvetica-Bold", 11, "Product details"),
    ("Helvetica", 11, "Product: Azithromycin 250mg film-coated tablets"),
    ("Helvetica", 11, "Batch / Lot number: AZI-2404-158"),
    ("Helvetica", 11, "Expiry date: 04/2027"),
    ("Helvetica", 11, ""),
    ("Helvetica-Bold", 11, "Complainant"),
    ("Helvetica", 11, "Name: Dr. Helen Carter, Greenfield Medical Centre"),
    ("Helvetica", 11, "Contact: h.carter@greenfieldmed.org"),
    ("Helvetica", 11, ""),
    ("Helvetica-Bold", 11, "Description of complaint"),
    ("Helvetica", 11, "A patient reported that two tablets from this batch were"),
    ("Helvetica", 11, "cracked and partially crumbled inside an intact blister."),
    ("Helvetica", 11, "The remaining tablets in the strip appeared softer than"),
    ("Helvetica", 11, "usual. No adverse effect was reported, but the patient was"),
    ("Helvetica", 11, "concerned about the correct dose being delivered."),
    ("Helvetica", 11, ""),
    ("Helvetica", 11, "Storage was as directed, below 25C, away from moisture."),
]


def main() -> None:
    pdf = canvas.Canvas("complaint_form.pdf", pagesize=A4)
    width, height = A4
    y = height - 30 * mm
    for font, size, text in LINES:
        pdf.setFont(font, size)
        pdf.drawString(25 * mm, y, text)
        y -= 8 * mm
    pdf.save()
    print("Wrote complaint_form.pdf")


if __name__ == "__main__":
    main()
