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


async def chat(
    question: str,
    dataset_context: str,
    profile_summary: str = "",
    conversation_history: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Chat with the AI about a specific dataset."""
    messages: list[dict[str, str]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": DATASET_CHAT_PROMPT.format(
                name=dataset_context.split("\n")[0] if dataset_context else "dataset",
                schema=dataset_context,
                profile_summary=profile_summary,
                question=question,
            ),
        },
    ]

    if conversation_history:
        messages = (
            [messages[0], *conversation_history[-6:], *messages[1:]]
        )

    try:
        llm = _get_llm()
        raw = await llm.chat_completion(messages=messages, temperature=0.3, max_tokens=1500)
        answer = _extract_text(raw)
        return {
            "answer": answer,
            "confidence": "high",
            "evidence": [],
            "suggested_actions": [],
        }
    except Exception as exc:
        return {
            "answer": f"I encountered an error processing your question: {exc}",
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
        # Split into individual insight lines
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
        # Try to parse as JSON
        import json
        try:
            return json.loads(text) if text.startswith("[") else [{"description": text}]
        except (json.JSONDecodeError, ValueError):
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
        import json
        try:
            return json.loads(text) if text.startswith("{") else [{"insight": text}]
        except (json.JSONDecodeError, ValueError):
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
        import json
        try:
            parsed = json.loads(text)
            return parsed if isinstance(parsed, list) else [parsed]
        except (json.JSONDecodeError, ValueError):
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
        import json
        try:
            return json.loads(text) if text.startswith("[") else []
        except (json.JSONDecodeError, ValueError):
            return []
    except Exception:
        return []
