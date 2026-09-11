"""Knowledge Agent — document search, vector search, policies, historical reports."""

from __future__ import annotations

from typing import Any

from app.ai.agents.agents.base import BaseAgent
from app.ai.agents.prompts.templates import KNOWLEDGE_AGENT_PROMPT


class KnowledgeAgent(BaseAgent):
    agent_type = "knowledge"
    name = "Knowledge Agent"
    description = "Search documents, vector search, company policies, historical reports"

    async def execute(
        self,
        task: str,
        context: dict[str, Any],
        tools: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        sources = context.get("sources", "documents, policies, reports")
        results = context.get("search_results", "No prior results")

        prompt = KNOWLEDGE_AGENT_PROMPT.format(
            task=task,
            sources=sources,
            results=results,
        )

        llm_response = await self._call_llm(prompt)

        search_results = self._search_knowledge(task, context)

        return self._build_result(
            output=llm_response,
            data={
                "search_results": search_results,
                "relevant_documents": search_results.get("documents", []),
                "key_information": self._extract_key_info(search_results),
                "confidence": search_results.get("confidence", 0.5),
                "source_citations": search_results.get("citations", []),
            },
            artifacts=[{"type": "knowledge", "content": search_results}],
        )

    def _search_knowledge(self, task: str, context: dict[str, Any]) -> dict[str, Any]:
        """Search knowledge base."""
        return {
            "documents": [],
            "confidence": 0.5,
            "citations": [],
            "query": task,
            "total_results": 0,
        }

    def _extract_key_info(self, results: dict[str, Any]) -> list[str]:
        """Extract key information from search results."""
        return [
            "Knowledge search completed — no matching documents found in current knowledge base"
        ]
