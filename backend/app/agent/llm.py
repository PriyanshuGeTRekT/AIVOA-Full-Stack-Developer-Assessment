"""Groq chat wrapper. Nodes call this; on failure they fall back to heuristics."""

import json
import logging

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class LLMUnavailable(Exception):
    """No usable model response (missing key, network error, bad JSON, etc.)."""


_primary_client = None
_fallback_client = None


def _build_client(model: str):
    from langchain_groq import ChatGroq

    return ChatGroq(
        api_key=settings.groq_api_key,
        model=model,
        temperature=settings.llm_temperature,
        max_retries=1,
        timeout=30,
    )


def _get_primary():
    global _primary_client
    if _primary_client is not None:
        return _primary_client
    if not settings.has_groq:
        raise LLMUnavailable("GROQ_API_KEY is not set")
    _primary_client = _build_client(settings.groq_model)
    return _primary_client


def _get_fallback():
    global _fallback_client
    if _fallback_client is not None:
        return _fallback_client
    if not settings.has_groq:
        raise LLMUnavailable("GROQ_API_KEY is not set")
    fallback = (settings.groq_fallback_model or "").strip()
    if not fallback or fallback == settings.groq_model:
        return None
    _fallback_client = _build_client(fallback)
    return _fallback_client


def complete_text(system: str, user: str) -> str:
    """Call primary model, then fallback model, else raise LLMUnavailable."""
    messages = [("system", system), ("human", user)]
    primary = _get_primary()
    try:
        response = primary.invoke(messages)
        return (response.content or "").strip()
    except Exception as primary_exc:  # noqa: BLE001
        logger.warning("Primary Groq model failed (%s): %s", settings.groq_model, primary_exc)
        fallback = _get_fallback()
        if fallback is None:
            raise LLMUnavailable(str(primary_exc)) from primary_exc
        try:
            logger.info("Retrying with fallback model %s", settings.groq_fallback_model)
            response = fallback.invoke(messages)
            return (response.content or "").strip()
        except Exception as fallback_exc:  # noqa: BLE001
            logger.warning(
                "Fallback Groq model failed (%s): %s", settings.groq_fallback_model, fallback_exc
            )
            raise LLMUnavailable(str(fallback_exc)) from fallback_exc


def complete_json(system: str, user: str) -> dict:
    """Ask for JSON and parse defensively (strips fences / surrounding prose)."""
    raw = complete_text(system, user)
    parsed = _extract_json(raw)
    if parsed is None:
        raise LLMUnavailable("Model did not return parseable JSON")
    return parsed


def _extract_json(text: str) -> dict | None:
    text = text.strip()
    if text.startswith("```"):
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
