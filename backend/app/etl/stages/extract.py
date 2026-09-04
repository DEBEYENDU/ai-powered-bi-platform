from typing import Any

import aiofiles
import chardet

from app.etl.engine.pipeline import PipelineStage


class ExtractStage(PipelineStage):
    name = "extract"

    async def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        file_path = context["file_path"]
        async with aiofiles.open(file_path, "rb") as f:
            raw = await f.read()
        encoding = chardet.detect(raw)["encoding"] or "utf-8"
        context["raw_bytes"] = raw
        context["encoding"] = encoding
        return context
