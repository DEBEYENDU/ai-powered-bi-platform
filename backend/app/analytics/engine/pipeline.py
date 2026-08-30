from abc import ABC, abstractmethod
from typing import Any, Dict, List
from datetime import datetime

class AnalyticsStage(ABC):
    name: str
    @abstractmethod
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        pass

class AnalyticsPipeline:
    def __init__(self, stages: List[AnalyticsStage]):
        self.stages = stages
    async def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        for stage in self.stages:
            context = await stage.execute(context)
        return context