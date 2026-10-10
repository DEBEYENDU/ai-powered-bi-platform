"""Tests for LLM reply parsing — fenced JSON must not leak into the UI."""

from __future__ import annotations

from app.ai.services.model_output import parse_json_reply


class TestParseJsonReply:
    def test_plain_json_object(self):
        assert parse_json_reply('{"a": 1}') == {"a": 1}

    def test_fenced_json_object(self):
        assert parse_json_reply('```json\n{"a": 1}\n```') == {"a": 1}

    def test_fenced_json_array(self):
        assert parse_json_reply('```\n[1, 2, 3]\n```') == [1, 2, 3]

    def test_json_embedded_in_prose(self):
        assert parse_json_reply('Here you go: {"x": true} — enjoy!') == {"x": True}

    def test_prose_returns_none(self):
        assert parse_json_reply("no json here") is None

    def test_empty_returns_none(self):
        assert parse_json_reply("") is None

    def test_truncated_json_returns_none(self):
        assert parse_json_reply('{"broken": ') is None


class TestDatasetInsightsFormatting:
    async def test_fenced_json_becomes_readable_lines(self, monkeypatch):
        from app.ai.data_engineering.services import ai_service

        fenced = (
            "```json\n"
            '{"purpose": "sales data", "observations": ["no nulls", "4 rows"], '
            '"recommendations": ["check outliers"]}\n'
            "```"
        )

        class _LLM:
            async def chat_completion(self, messages, **kwargs):
                return fenced

        monkeypatch.setattr(ai_service, "_get_llm", lambda: _LLM())
        lines = await ai_service.get_dataset_insights(
            name="sales", row_count=4, column_count=3, column_profiles="- sales: numeric"
        )

        assert lines, "insights must not be empty"
        assert not any(line.startswith("```") for line in lines)
        assert any(line.startswith("purpose:") for line in lines)
        assert any("sales data" in line for line in lines)
        assert any("no nulls" in line for line in lines)

    async def test_unavailable_provider_reports_honestly(self, monkeypatch):
        from app.ai.data_engineering.services import ai_service

        class _LLM:
            async def chat_completion(self, messages, **kwargs):
                raise RuntimeError("provider down")

        monkeypatch.setattr(ai_service, "_get_llm", lambda: _LLM())
        lines = await ai_service.get_dataset_insights(
            name="sales", row_count=4, column_count=3, column_profiles="x"
        )
        assert len(lines) == 1
        assert "unavailable" in lines[0].lower()
