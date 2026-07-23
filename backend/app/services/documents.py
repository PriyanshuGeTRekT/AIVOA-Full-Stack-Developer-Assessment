"""Extract plain text from uploaded complaint files (pdf/eml/txt). No OCR."""

import io
from email import policy
from email.parser import BytesParser


class DocumentExtractError(Exception):
    pass


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
    except ImportError as exc:
        raise DocumentExtractError("PDF received but pdfplumber is not installed.") from exc

    try:
        pages = []
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page in pdf.pages:
                pages.append(page.extract_text() or "")
        text = "\n".join(pages).strip()
    except Exception as exc:  # noqa: BLE001
        raise DocumentExtractError(f"Could not parse PDF: {exc}") from exc

    if not text:
        raise DocumentExtractError("PDF contained no extractable text (it may be scanned).")
    return text


def _from_email(content: bytes) -> str:
    try:
        message = BytesParser(policy=policy.default).parsebytes(content)
    except Exception as exc:  # noqa: BLE001
        raise DocumentExtractError(f"Could not parse email: {exc}") from exc
    subject = message.get("subject", "")
    body_part = message.get_body(preferencelist=("plain", "html"))
    body = body_part.get_content() if body_part else ""
    return f"Subject: {subject}\n\n{body}".strip()
