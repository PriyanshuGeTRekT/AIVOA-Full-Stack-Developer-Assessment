"""Thin wrapper around the Groq chat model.

The rest of the agent talks to the LLM only through these two helpers. That
keeps the Groq specific details in one place and, importantly, gives us a
single spot to fall back to a heuristic when no API key is configured or a
call fails. The workflow therefore runs end to end even without Groq access,
which makes local demos and CI painless.
"""

import json
import logging

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class LLMUnavailable(Exception):
    """Raised when we cannot get a usable answer from the model.

    Nodes catch this and switch to their deterministic fallback so a missing
    key or a transient Groq error never breaks the pipeline.
    """


# The ChatGroq client is created lazily and reused. We keep it module level so
# we do not pay the construction cost on every node call.
_client = None


def _get_client():
    global _client
    if _client is not None:
        return _client
    if not settings.has_groq:
        raise LLMUnavailable("GROQ_API_KEY is not set")

    # Imported lazily so the package installs and imports even if the optional
    # LLM dependencies are missing in a minimal environment.
    from langchain_groq import ChatGroq

    _client = ChatGroq(
        api_key=settings.groq_api_key,
        model=settings.groq_model,
        temperature=settings.llm_temperature,
        # We have our own heuristic fallback, so there is no point in the client
        # retrying a bad key many times. Fail fast and let the node degrade.
        max_retries=1,
        timeout=30,
    )
    return _client


def complete_text(system: str, user: str) -> str:
    """Return the model's plain text answer for a system/user prompt pair."""
    client = _get_client()
    try:
        response = client.invoke([("system", system), ("human", user)])
    except Exception as exc:  # noqa: BLE001 - we deliberately treat any failure the same
        logger.warning("Groq call failed, falling back to heuristic: %s", exc)
        raise LLMUnavailable(str(exc)) from exc
    return (response.content or "").strip()


def complete_json(system: str, user: str) -> dict:
    """Ask the model for JSON and parse it defensively.

    Small instruction tuned models occasionally wrap JSON in prose or code
    fences, so we extract the outermost object rather than trusting the reply
    to be clean.
    """
    raw = complete_text(system, user)
    parsed = _extract_json(raw)
    if parsed is None:
        raise LLMUnavailable("Model did not return parseable JSON")
    return parsed


def _extract_json(text: str) -> dict | None:
    text = text.strip()
    if text.startswith("```"):
        # Strip a leading ```json / ``` fence and the trailing fence.
        text = text.split("```", 2)[1] if text.count("```") >= 2 else text
        if text.lower().startswith("json"):
            text = text[4:]

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        return None
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None
