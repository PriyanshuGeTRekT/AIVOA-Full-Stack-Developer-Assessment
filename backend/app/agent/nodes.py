"""Graph nodes. Pattern: try LLM, on LLMUnavailable use a local heuristic."""

import logging
import re
from difflib import SequenceMatcher

from app.agent import prompts
from app.agent.llm import LLMUnavailable, complete_json, complete_text
from app.agent.state import ComplaintState

logger = logging.getLogger(__name__)

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE_RE = re.compile(r"(?:\+?\d[\d\s().-]{7,}\d)")
BATCH_KEYWORD_RE = re.compile(r"\b(?:batch|lot|b\.?\s*no\.?)\b", re.I)
CODE_TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9\-/]{2,}")
# Skip label words after "batch" / "lot" (e.g. "Lot number: AZI-2404-158").
BATCH_STOPWORDS = {"number", "no", "lot", "batch"}


def _find_batch(raw: str) -> str | None:
    """Return the first batch/lot-like token after a batch/lot keyword."""
    for keyword in BATCH_KEYWORD_RE.finditer(raw):
        tail = raw[keyword.end() : keyword.end() + 50]
        for candidate in CODE_TOKEN_RE.findall(tail):
            if candidate.lower() in BATCH_STOPWORDS:
                continue
            if any(ch.isdigit() for ch in candidate):
                return candidate.strip(".,;")
    return None

# Simple keyword maps for the no-LLM path.
TYPE_KEYWORDS = {
    "Contamination": ["contaminat", "impur", "microb", "mold", "fungus"],
    "Foreign Particle": ["particle", "foreign", "fiber", "glass", "black spot", "speck"],
    "Packaging Defect": ["packag", "seal", "leak", "blister", "carton", "bottle"],
    "Labeling Error": ["label", "mislabel", "expiry", "expiration", "barcode", "artwork"],
    "Broken Tablet": ["broken", "cracked", "crumbl", "chipped", "powder"],
    "Efficacy": ["not working", "ineffective", "no effect", "efficacy", "dissol"],
    "Adverse Event": ["adverse", "reaction", "hospital", "rash", "nausea", "side effect"],
}

CRITICAL_HINTS = [
    "adverse", "hospital", "injury", "injur", "harm", "death", "wrong product",
    "mix up", "mix-up", "contaminat", "sterile", "unconscious", "allergic",
]
MAJOR_HINTS = [
    "label", "packag", "efficacy", "ineffective", "expiry", "seal", "leak",
    "particle", "foreign", "discolor", "discolour", "impur",
]


NEGATIONS = ("no ", "not ", "without ", "denies ", "denied ", "n't ", "free of ")


def _matches_any(text: str, hints: list[str]) -> bool:
    """Keyword match at word start; ignore hits after light negation words."""
    for hint in hints:
        for match in re.finditer(rf"\b{re.escape(hint)}", text):
            prefix = text[max(0, match.start() - 12) : match.start()]
            if any(neg in prefix for neg in NEGATIONS):
                continue
            return True
    return False


def _similar(a: str, b: str) -> float:
    return SequenceMatcher(None, (a or "").lower(), (b or "").lower()).ratio()


# --------------------------------------------------------------------------- #
# Node: extract structured fields                                             #
# --------------------------------------------------------------------------- #
def _mark_llm(state: ComplaintState, used: bool) -> dict:
    # Only set True; never overwrite an earlier True with False.
    if used:
        return {"used_llm": True}
    return {}


def extract_fields(state: ComplaintState) -> dict:
    raw = state["raw_text"]
    try:
        extracted = complete_json(prompts.EXTRACTION_SYSTEM, prompts.extraction_user(raw))
        used_llm = True
    except LLMUnavailable:
        extracted = _extract_heuristic(raw)
        used_llm = False

    # Normalise so downstream nodes can rely on the keys existing.
    for key in ("product_name", "batch_number", "complainant_name",
                "complainant_contact", "complaint_type", "description"):
        extracted.setdefault(key, None)

    return {"extracted": extracted, **_mark_llm(state, used_llm)}


def _extract_heuristic(raw: str) -> dict:
    batch = _find_batch(raw)
    email = EMAIL_RE.search(raw)
    phone = PHONE_RE.search(raw)

    # Score every category by how many of its keywords appear, then take the
    # best. Counting beats first-match because a single stray word (for example
    # "carton" in a labeling complaint) should not outweigh stronger signals.
    lowered = raw.lower()
    scores = {
        label: sum(kw in lowered for kw in keywords)
        for label, keywords in TYPE_KEYWORDS.items()
    }
    best_label = max(scores, key=scores.get)
    complaint_type = best_label if scores[best_label] > 0 else "Other"

    # First non trivial sentence makes a reasonable description. We drop email
    # header lines (Subject:/From:/To:) so the description reads like the actual
    # problem rather than metadata.
    body = "\n".join(
        line for line in raw.splitlines()
        if not re.match(r"^\s*(subject|from|to|cc|date|regards|kind regards)\b", line, re.I)
    ).strip()
    sentences = re.split(r"(?<=[.!?])\s+", body or raw.strip())
    description = next((s.strip() for s in sentences if len(s.strip()) > 20), raw.strip()[:200])

    # A light attempt at the product name: look for a token after "product" or
    # a capitalised drug-like word ending in common suffixes.
    product = None
    m = re.search(r"product[\s:]+([A-Z][A-Za-z0-9\- ]{2,40})", raw)
    if m:
        product = m.group(1).strip().rstrip(".,")
    if not product:
        # Common drug name endings. Not exhaustive, just enough to give the
        # heuristic a fighting chance; the LLM handles the general case.
        suffixes = (
            "cillin|mycin|micin|floxacin|cin|prazole|zole|sartan|pril|olol|"
            "dipine|statin|vastatin|formin|parin|mab|pine|dine|azepam"
        )
        m = re.search(rf"\b([A-Z][a-z]+(?:{suffixes}))\b", raw)
        if m:
            product = m.group(1)

    return {
        "product_name": product,
        "batch_number": batch,
        "complainant_name": None,
        "complainant_contact": email.group(0) if email else (phone.group(0) if phone else None),
        "complaint_type": complaint_type,
        "description": description,
    }


# --------------------------------------------------------------------------- #
# Node: completeness check                                                    #
# --------------------------------------------------------------------------- #
def check_completeness(state: ComplaintState) -> dict:
    extracted = state["extracted"]
    try:
        result = complete_json(prompts.COMPLETENESS_SYSTEM, prompts.completeness_user(extracted))
        # Guard against a model returning an odd shape.
        result.setdefault("is_complete", False)
        result.setdefault("missing_fields", [])
        return {"completeness": result, **_mark_llm(state, True)}
    except LLMUnavailable:
        result = _completeness_heuristic(extracted)
        return {"completeness": result}


def _completeness_heuristic(extracted: dict) -> dict:
    # Aligned with COMPLETENESS_SYSTEM so LLM and heuristic agree on "ready".
    required = {
        "product_name": "Product name",
        "batch_number": "Batch/lot number",
        "complainant_name": "Complainant name",
        "complaint_type": "Complaint type",
        "description": "Problem description",
    }
    missing = [label for field, label in required.items() if not extracted.get(field)]
    return {
        "is_complete": len(missing) == 0,
        "missing_fields": missing,
        "notes": "Record is ready for investigation." if not missing
        else "Follow up with the complainant to capture the missing details.",
    }


# --------------------------------------------------------------------------- #
# Node: risk classification                                                   #
# --------------------------------------------------------------------------- #
def classify_risk(state: ComplaintState) -> dict:
    extracted = state["extracted"]
    try:
        result = complete_json(prompts.RISK_SYSTEM, prompts.risk_user(extracted, state["raw_text"]))
        level = str(result.get("risk_level", "")).capitalize()
        if level not in {"Critical", "Major", "Minor"}:
            raise LLMUnavailable("unexpected risk level")
        rationale = result.get("rationale") or ""
        return {"risk_level": level, "risk_rationale": rationale, **_mark_llm(state, True)}
    except LLMUnavailable:
        level, rationale = _risk_heuristic(extracted, state["raw_text"])
        return {"risk_level": level, "risk_rationale": rationale}


def _risk_heuristic(extracted: dict, raw: str) -> tuple[str, str]:
    text = f"{raw} {extracted.get('description') or ''}".lower()
    if _matches_any(text, CRITICAL_HINTS):
        return "Critical", "Language suggests a potential patient safety impact."
    if _matches_any(text, MAJOR_HINTS):
        return "Major", "Quality defect likely affecting compliance or efficacy."
    return "Minor", "No safety or major quality impact detected in the text."


# --------------------------------------------------------------------------- #
# Node: regulatory reportability assessment                                   #
# --------------------------------------------------------------------------- #
ADVERSE_HINTS = [
    "adverse", "reaction", "hospital", "death", "injury", "injur", "harm",
    "allergic", "rash", "unconscious", "anaphyla",
]
FIELD_ALERT_HINTS = [
    "contaminat", "mix up", "mix-up", "wrong product", "microb", "sterile",
    "foreign", "particle", "impur", "discolor", "discolour", "mould", "mold",
]


def assess_reportability(state: ComplaintState) -> dict:
    extracted = state["extracted"]
    risk = state.get("risk_level", "")
    try:
        result = complete_json(
            prompts.REPORTABILITY_SYSTEM,
            prompts.reportability_user(extracted, risk, state["raw_text"]),
        )
        report_type = str(result.get("report_type", "")).strip()
        valid = {
            "FDA Field Alert Report",
            "Pharmacovigilance / Adverse Event",
            "None",
        }
        if report_type not in valid:
            raise LLMUnavailable("unexpected report type")
        reportable = bool(result.get("reportable")) and report_type != "None"
        reason = result.get("reason") or ""
        return {
            "reportable": reportable,
            "report_type": report_type,
            "report_reason": reason,
            **_mark_llm(state, True),
        }
    except LLMUnavailable:
        reportable, report_type, reason = _reportability_heuristic(extracted, state["raw_text"])
        return {"reportable": reportable, "report_type": report_type, "report_reason": reason}


def _reportability_heuristic(extracted: dict, raw: str) -> tuple[bool, str, str]:
    text = f"{raw} {extracted.get('description') or ''}".lower()
    complaint_type = extracted.get("complaint_type")

    if complaint_type == "Adverse Event" or _matches_any(text, ADVERSE_HINTS):
        return (
            True,
            "Pharmacovigilance / Adverse Event",
            "Suspected adverse drug reaction; route to pharmacovigilance for expedited reporting.",
        )
    if _matches_any(text, FIELD_ALERT_HINTS):
        return (
            True,
            "FDA Field Alert Report",
            "Possible contamination, mix up or significant defect on a distributed product.",
        )
    return (False, "None", "No regulatory reporting trigger identified in the complaint.")


# --------------------------------------------------------------------------- #
# Node: duplicate detection (no LLM, pure comparison)                         #
# --------------------------------------------------------------------------- #
def detect_duplicate(state: ComplaintState) -> dict:
    extracted = state["extracted"]
    best_id = None
    best_score = 0.0

    # Weights sum to 1.0 so the score reads as a 0 to 1 similarity. A shared
    # batch number for the same product is the strongest single signal.
    for other in state.get("existing", []):
        score = 0.0
        if extracted.get("batch_number") and other.get("batch_number"):
            if extracted["batch_number"].lower() == other["batch_number"].lower():
                score += 0.5
        if extracted.get("product_name") and other.get("product_name"):
            score += 0.2 * _similar(extracted["product_name"], other["product_name"])
        score += 0.3 * _similar(extracted.get("description") or "", other.get("description") or "")

        if score > best_score:
            best_score = score
            best_id = other["id"]

    # Only flag it as a duplicate when the evidence is strong enough.
    if best_score >= 0.7:
        return {"duplicate_of": best_id, "duplicate_score": round(best_score, 2)}
    return {"duplicate_of": None, "duplicate_score": round(best_score, 2)}


# --------------------------------------------------------------------------- #
# Node: skip investigation when a strong duplicate was found                  #
# --------------------------------------------------------------------------- #
def skip_investigation_for_duplicate(state: ComplaintState) -> dict:
    """Avoid inventing root cause / CAPA for a likely re-logged complaint."""
    score = state.get("duplicate_score")
    score_txt = f" (similarity {score:.0%})" if isinstance(score, (int, float)) else ""
    note = (
        f"Investigation suggestions skipped{score_txt}: this complaint was flagged as a "
        f"likely duplicate of #{state.get('duplicate_of')}. Review the original record "
        "before opening a parallel investigation."
    )
    return {"root_cause": note, "capa": note}


# --------------------------------------------------------------------------- #
# Node: root cause recommendation                                            #
# --------------------------------------------------------------------------- #
def recommend_root_cause(state: ComplaintState) -> dict:
    extracted = state["extracted"]
    try:
        text = complete_text(prompts.ROOT_CAUSE_SYSTEM, prompts.root_cause_user(extracted))
        return {"root_cause": text, **_mark_llm(state, True)}
    except LLMUnavailable:
        text = _root_cause_heuristic(extracted)
        return {"root_cause": text}


def _root_cause_heuristic(extracted: dict) -> str:
    mapping = {
        "Contamination": "Possible breach in aseptic processing or inadequate cleaning "
        "validation on the line that produced this batch.",
        "Foreign Particle": "Likely equipment wear or environmental particulate ingress "
        "during compression or filling; review line clearance records.",
        "Packaging Defect": "Sealing or blister forming parameters may have drifted; "
        "check the packaging line qualification and in process controls.",
        "Labeling Error": "Artwork version control or line clearance gap during the "
        "labeling step; review the batch reconciliation for labels.",
        "Broken Tablet": "Tablet hardness or friability may be out of specification, or "
        "the product was subjected to mechanical stress in transit.",
        "Efficacy": "Potential dissolution or assay drift; review stability and the "
        "batch release test data for this lot.",
        "Adverse Event": "Requires pharmacovigilance triage; investigate for product "
        "quality contribution alongside the medical assessment.",
    }
    return mapping.get(
        extracted.get("complaint_type"),
        "Investigate the manufacturing, packaging and distribution history of the "
        "affected batch to isolate the contributing factor.",
    )


# --------------------------------------------------------------------------- #
# Node: CAPA recommendation                                                   #
# --------------------------------------------------------------------------- #
def recommend_capa(state: ComplaintState) -> dict:
    extracted = state["extracted"]
    root_cause = state.get("root_cause", "")
    try:
        text = complete_text(prompts.CAPA_SYSTEM, prompts.capa_user(extracted, root_cause))
        return {"capa": text, **_mark_llm(state, True)}
    except LLMUnavailable:
        text = _capa_heuristic(extracted)
        return {"capa": text}


def _capa_heuristic(extracted: dict) -> str:
    complaint_type = extracted.get("complaint_type")
    presets = {
        "Contamination": (
            "Corrective: Quarantine the affected batch and perform sterility and "
            "bioburden testing; assess the need for a recall.\n"
            "Preventive: Requalify the cleaning procedure and increase environmental "
            "monitoring frequency on the line."
        ),
        "Packaging Defect": (
            "Corrective: Segregate suspect stock and re-inspect retained samples "
            "from the batch.\n"
            "Preventive: Recalibrate the sealing equipment and tighten in process "
            "seal integrity checks."
        ),
        "Labeling Error": (
            "Corrective: Hold distribution and reconcile all labels used for the "
            "batch.\n"
            "Preventive: Strengthen artwork version control and add an automated "
            "label verification step at the line."
        ),
    }
    return presets.get(
        complaint_type,
        "Corrective: Investigate and contain the affected batch, and notify the "
        "complainant of the outcome.\n"
        "Preventive: Address the confirmed root cause with a process or training "
        "change and verify effectiveness after implementation.",
    )


# --------------------------------------------------------------------------- #
# Node: complaint summary                                                     #
# --------------------------------------------------------------------------- #
def summarise(state: ComplaintState) -> dict:
    extracted = state["extracted"]
    try:
        text = complete_text(prompts.SUMMARY_SYSTEM, prompts.summary_user(extracted))
        return {"summary": text.strip(), **_mark_llm(state, True)}
    except LLMUnavailable:
        product = extracted.get("product_name") or "Unknown product"
        problem = extracted.get("description") or "an unspecified issue"
        text = f"{product}: {problem}"
        return {"summary": text.strip()}
