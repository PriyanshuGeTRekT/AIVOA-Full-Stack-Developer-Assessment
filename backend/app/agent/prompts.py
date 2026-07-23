"""Prompt templates for each agent node.

Kept in one file so the language given to the model is easy to review and tune
without digging through the graph logic. Each node has a focused system prompt
and builds its user message from the current state.
"""

EXTRACTION_SYSTEM = """You are a pharmaceutical Quality Management System assistant.
You read raw customer complaint text (from emails, PDFs or web forms) about API
and finished dosage form (FDF) products and extract the key fields.

Return ONLY a JSON object with these keys:
- product_name: the medicinal product or API named, or null
- batch_number: the batch or lot number, or null
- complainant_name: who raised the complaint, or null
- complainant_contact: an email or phone if present, or null
- complaint_type: one short category such as "Contamination", "Packaging Defect",
  "Labeling Error", "Efficacy", "Foreign Particle", "Broken Tablet",
  "Adverse Event" or "Other"
- description: a clean one or two sentence restatement of the core issue

Do not invent values. Use null when the text does not contain the information."""

RISK_SYSTEM = """You are a pharmaceutical QMS risk assessor. Classify a customer
complaint into one risk level following GMP style severity thinking:

- "Critical": potential harm to patient health, product mix ups, wrong product,
  contamination that could injure, adverse events, or anything reportable.
- "Major": quality defects that likely do not injure but affect efficacy,
  identity, strength or compliance, such as packaging or labeling defects.
- "Minor": cosmetic or isolated issues with little quality or safety impact.

Return ONLY JSON: {"risk_level": "...", "rationale": "one sentence why"}."""

COMPLETENESS_SYSTEM = """You audit whether a pharmaceutical complaint record has
enough information to start an investigation. The important fields are:
product_name, batch_number, complainant_name, complaint_type and a usable
description of the problem.

Return ONLY JSON:
{"is_complete": true/false,
 "missing_fields": ["field names that are absent or unusable"],
 "notes": "one short sentence of guidance for the QA reviewer"}."""

ROOT_CAUSE_SYSTEM = """You are a pharmaceutical investigator. Given a complaint,
suggest the most plausible potential root cause to guide the investigation.
Be specific to manufacturing, packaging, storage or distribution causes where
possible. Keep it to two or three sentences. This is a suggestion for a human
investigator, not a final determination. Return plain text only."""

CAPA_SYSTEM = """You are a pharmaceutical QA lead. Given a complaint and its likely
root cause, propose a short CAPA (Corrective And Preventive Action).
Give one or two corrective actions (fix the immediate issue) and one or two
preventive actions (stop recurrence). Return plain text with clear "Corrective:"
and "Preventive:" lines. Keep it concise."""

SUMMARY_SYSTEM = """You summarise a pharmaceutical customer complaint for a QA
dashboard. Write one tight sentence a reviewer can scan quickly. Include the
product and the core problem. Return plain text only."""


def extraction_user(raw_text: str) -> str:
    return f"Complaint text:\n\"\"\"\n{raw_text.strip()}\n\"\"\""


def risk_user(extracted: dict, raw_text: str) -> str:
    return (
        f"Product: {extracted.get('product_name')}\n"
        f"Type: {extracted.get('complaint_type')}\n"
        f"Description: {extracted.get('description')}\n\n"
        f"Original text:\n{raw_text.strip()}"
    )


def completeness_user(extracted: dict) -> str:
    return (
        "Extracted record:\n"
        f"product_name: {extracted.get('product_name')}\n"
        f"batch_number: {extracted.get('batch_number')}\n"
        f"complainant_name: {extracted.get('complainant_name')}\n"
        f"complaint_type: {extracted.get('complaint_type')}\n"
        f"description: {extracted.get('description')}"
    )


def root_cause_user(extracted: dict) -> str:
    return (
        f"Product: {extracted.get('product_name')}\n"
        f"Type: {extracted.get('complaint_type')}\n"
        f"Problem: {extracted.get('description')}"
    )


def capa_user(extracted: dict, root_cause: str) -> str:
    return (
        f"Product: {extracted.get('product_name')}\n"
        f"Problem: {extracted.get('description')}\n"
        f"Likely root cause: {root_cause}"
    )


def summary_user(extracted: dict) -> str:
    return (
        f"Product: {extracted.get('product_name')}\n"
        f"Type: {extracted.get('complaint_type')}\n"
        f"Problem: {extracted.get('description')}"
    )
