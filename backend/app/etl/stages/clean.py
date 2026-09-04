from typing import Any

from app.etl.engine.pipeline import PipelineStage


class CleanStage(PipelineStage):
    name = "clean"

    async def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        # placeholder cleaning: strip whitespace from strings
        raw = context.get("raw_bytes", b"")
        text = raw.decode("utf-8", errors="replace")
        cleaned = text.strip()
        context["cleaned_text"] = cleaned
        return context
