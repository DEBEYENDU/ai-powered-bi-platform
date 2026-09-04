from typing import Any

from app.etl.engine.pipeline import PipelineStage


class TransformStage(PipelineStage):
    name = "transform"

    async def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        # placeholder: rename columns mapping
        context["transformed"] = {"status": "transformed"}
        return context
