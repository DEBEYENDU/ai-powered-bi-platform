from abc import ABC, abstractmethod
from typing import Any


class AnalyticsStage(ABC):
    name: str

    @abstractmethod
    async def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        pass


class AnalyticsPipeline:
    def __init__(self, stages: list[AnalyticsStage]):
        self.stages = stages

    async def run(self, context: dict[str, Any]) -> dict[str, Any]:
        for stage in self.stages:
            context = await stage.execute(context)
        return context
