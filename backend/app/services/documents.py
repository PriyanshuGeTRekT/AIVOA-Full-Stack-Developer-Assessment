"""Turn an uploaded file into plain text for the agent.

The assignment does not require production grade OCR, so we handle the common
demo formats: plain text, .eml emails and PDFs. Images are accepted but we only
record a placeholder note, since real OCR is out of scope.
"""

import io
from email import policy
from email.parser import BytesParser


def extract_text(filename: str, content: bytes) -> str:
    name = (filename or "").lower()

    if name.endswith(".pdf"):
        return _from_pdf(content)
    if name.endswith(".eml"):
        return _from_email(content)
    if name.endswith((".txt", ".md", ".csv")):
        return content.decode("utf-8", errors="replace").strip()
    if name.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")):
        return (
            "[Image upload received. OCR is out of scope for this demo, so please "
            "enter the complaint details as text.]"
        )

    # Best effort for anything else: try to decode as text.
    return content.decode("utf-8", errors="replace").strip()


def _from_pdf(content: bytes) -> str:
    try:
        import pdfplumber
    except ImportError:
        return "[PDF received but pdfplumber is not installed.]"

    pages = []
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for page in pdf.pages:
            pages.append(page.extract_text() or "")
    return "\n".join(pages).strip()


def _from_email(content: bytes) -> str:
    message = BytesParser(policy=policy.default).parsebytes(content)
    subject = message.get("subject", "")
    body_part = message.get_body(preferencelist=("plain", "html"))
    body = body_part.get_content() if body_part else ""
    return f"Subject: {subject}\n\n{body}".strip()
