from abc import ABC, abstractmethod
from typing import Any
import asyncio

class PipelineStage(ABC):
    name: str
    async def run(self, context: dict[str, Any]) -> dict[str, Any]:
        return await self.execute(context)

    @abstractmethod
    async def execute(self, context: dict[str, Any]) -> dict[str, Any]: ...

class ETLPipeline:
    def __init__(self, stages: list[PipelineStage]):
        self.stages = stages

    async def run(self, context: dict[str, Any]):
        for stage in self.stages:
            context = await stage.run(context)
        return context
