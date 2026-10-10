"""AI service — wraps the LLM provider for data engineering chat and
recommendations."""

from __future__ import annotations

from typing import Any

from app.ai.data_engineering.prompts.templates import (
    CLEANING_PROMPT,
    DATASET_CHAT_PROMPT,
    DATASET_UNDERSTANDING_PROMPT,
    QUALITY_ANALYSIS_PROMPT,
    RELATIONSHIP_PROMPT,
    SCHEMA_INFER_PROMPT,
    SYSTEM_PROMPT,
    TRANSFORM_PROMPT,
)
from app.ai.providers.registry import get_provider
from app.ai.services.model_output import parse_json_reply


def _get_llm() -> Any:
    return get_provider()


def _extract_text(response: Any) -> str:
    """Extract text content from an LLM response, handling various formats."""
    if isinstance(response, str):
        return response
    if isinstance(response, dict):
        if "content" in response:
            c = response["content"]
            if isinstance(c, str):
                return c
            if isinstance(c, list) and len(c) > 0:
                return c[0].get("text", str(c[0]))
        if "choices" in response and len(response["choices"]) > 0:
            choice = response["choices"][0]
            if "message" in choice:
                return choice["message"].get("content", "")
            return choice.get("text", "")
        return str(response)
    if hasattr(response, "choices") and len(response.choices) > 0:
        return response.choices[0].message.content or ""
    return str(response)


def _parse_json(text: str) -> Any | None:
    """Parse JSON out of a model reply (tolerates ```json fences)."""
    return parse_json_reply(text)


def _flatten(payload: Any, prefix: str = "") -> list[str]:
    """Turn parsed JSON into readable one-line insights."""
    lines: list[str] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            label = f"{prefix}{key}"
            if isinstance(value, list):
                for item in value[:5]:
                    lines.append(f"{label}: {_scalar(item)}")
            elif isinstance(value, dict):
                lines.extend(_flatten(value, prefix=f"{label}."))
            else:
                lines.append(f"{label}: {_scalar(value)}")
    elif isinstance(payload, list):
        lines.extend(_flatten({"insight": payload}, prefix=prefix))
    else:
        lines.append(_scalar(payload))
    return [ln[:500] for ln in lines if ln.strip()]


def _scalar(value: Any) -> str:
    if isinstance(value, dict):
        return "; ".join(f"{k}={v}" for k, v in value.items())
    return str(value)


async def chat(
    question: str,
    dataset_context: str,
    profile_summary: str = "",
    conversation_history: list[dict[str, str]] | None = None,
    data_sample: str = "",
    data_summary: str = "",
    dataset_name: str = "",
) -> dict[str, Any]:
    """Chat with the AI about a specific dataset."""
    name = dataset_name or (
        dataset_context.split("\n")[0] if dataset_context else "dataset"
    )
    messages: list[dict[str, str]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": DATASET_CHAT_PROMPT.format(
                name=name,
                schema=dataset_context,
                profile_summary=profile_summary or "(no profile available)",
                data_summary=data_summary or "(no aggregates available)",
                data_sample=data_sample or "(no rows available)",
                question=question,
            ),
        },
    ]

    if conversation_history:
        messages = [messages[0], *conversation_history[-6:], *messages[1:]]

    try:
        llm = _get_llm()
        raw = await llm.chat_completion(messages=messages, temperature=0.3, max_tokens=1500)
        answer = _extract_text(raw)
        # Evidence is the real, computed aggregates — not model prose.
        evidence = [line for line in data_summary.split("\n") if line.strip()][:5]
        return {
            "answer": answer,
            "confidence": "high" if answer.strip() else "low",
            "evidence": evidence,
            "suggested_actions": [],
        }
    except Exception as exc:
        return {
            "answer": (
                "I could not answer that because the AI provider call failed: "
                f"{exc}. Check Settings → AI provider configuration and retry."
            ),
            "confidence": "low",
            "evidence": [],
            "suggested_actions": ["Check AI provider configuration"],
        }


async def get_dataset_insights(
    name: str,
    row_count: int,
    column_count: int,
    column_profiles: str,
) -> list[str]:
    """Get AI-generated insights about a dataset."""
    prompt = DATASET_UNDERSTANDING_PROMPT.format(
        name=name,
        row_count=row_count,
        column_count=column_count,
        column_profiles=column_profiles,
    )

    try:
        llm = _get_llm()
        raw = await llm.chat_completion(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=1500,
        )
        text = _extract_text(raw)
        parsed = _parse_json(text)
        if parsed is not None:
            lines = _flatten(parsed)
        else:
            lines = [line.strip("- ").strip() for line in text.split("\n") if line.strip()]
        return lines[:10] if lines else [text]
    except Exception:
        return ["AI insights unavailable — check provider configuration"]


async def get_quality_recommendations(
    quality_scores: str,
    issues: str,
) -> list[str]:
    """Get AI recommendations for quality issues."""
    prompt = QUALITY_ANALYSIS_PROMPT.format(
        quality_scores=quality_scores,
        issues=issues,
    )

    try:
        llm = _get_llm()
        raw = await llm.chat_completion(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=1500,
        )
        text = _extract_text(raw)
        lines = [line.strip("- ").strip() for line in text.split("\n") if line.strip()]
        return lines[:10] if lines else [text]
    except Exception:
        return ["AI recommendations unavailable"]


async def get_cleaning_suggestions_ai(
    column: str,
    current_state: str,
    statistics: str,
) -> list[dict[str, Any]]:
    """Get AI-powered cleaning suggestions for a specific column."""
    prompt = CLEANING_PROMPT.format(
        column=column,
        current_state=current_state,
        statistics=statistics,
    )

    try:
        llm = _get_llm()
        raw = await llm.chat_completion(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=1000,
        )
        text = _extract_text(raw)
        parsed = _parse_json(text)
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict):
            return [parsed]
        return [{"description": text}]
    except Exception:
        return []


async def get_relationship_insights(
    table_info: str,
) -> list[dict[str, Any]]:
    """Get AI insights about discovered relationships."""
    prompt = RELATIONSHIP_PROMPT.format(table_info=table_info)

    try:
        llm = _get_llm()
        raw = await llm.chat_completion(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=1000,
        )
        text = _extract_text(raw)
        parsed = _parse_json(text)
        if isinstance(parsed, dict):
            return [parsed]
        if isinstance(parsed, list):
            return parsed
        return [{"insight": text}]
    except Exception:
        return []


async def get_transform_recommendations(
    dataset_info: str,
    goal: str,
) -> list[dict[str, Any]]:
    """Get AI transform recommendations based on a user goal."""
    prompt = TRANSFORM_PROMPT.format(dataset_info=dataset_info, goal=goal)

    try:
        llm = _get_llm()
        raw = await llm.chat_completion(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=1500,
        )
        text = _extract_text(raw)
        parsed = _parse_json(text)
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict):
            return [parsed]
        return [{"transform_type": "unknown", "description": text}]
    except Exception:
        return []


async def infer_column_types_ai(
    columns: str,
    sample_data: str,
) -> list[dict[str, Any]]:
    """Get AI-inferred semantic types for columns."""
    prompt = SCHEMA_INFER_PROMPT.format(columns=columns, sample_data=sample_data)

    try:
        llm = _get_llm()
        raw = await llm.chat_completion(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=1000,
        )
        text = _extract_text(raw)
        parsed = _parse_json(text)
        if isinstance(parsed, list):
            return [p for p in parsed if isinstance(p, dict)]
        if isinstance(parsed, dict):
            return [parsed]
        return []
    except Exception:
        return []
