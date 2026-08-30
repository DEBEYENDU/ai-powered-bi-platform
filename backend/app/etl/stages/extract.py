from abc import ABC, abstractmethod
from typing import Any, Optional
import aiofiles
import chardet

class ExtractStage(PipelineStage):
    name = "extract"

    async def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        dataset_id = context["dataset_id"]
        file_path = context["file_path"]
        async with aiofiles.open(file_path, "rb") as f:
            raw = await f.read()
        encoding = chardet.detect(raw)["encoding"] or "utf-8"
        context["raw_bytes"] = raw
        context["encoding"] = encoding
        return context