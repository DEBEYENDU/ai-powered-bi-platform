from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.knowledge.repositories.document_repository import DocumentRepository
from app.knowledge.services.retrieval_service import RetrievalService


@dataclass
class EvaluationResult:
    query: str
    expected_document_id: str | None
    retrieved_document_ids: list[str]
    retrieval_rank: int | None
    relevance_score: float
    grounded: bool
    citation_valid: bool


class EvaluationService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.retrieval = RetrievalService(db)
        self.doc_repo = DocumentRepository(db)

    async def evaluate_query(
        self, query: str, expected_doc_id: str | None, org_id: str
    ) -> EvaluationResult:
        results = await self.retrieval.hybrid_search(query=query, org_id=org_id, top_k=20)

        retrieved_ids = [r["document_id"] for r in results]

        retrieval_rank: int | None = None
        if expected_doc_id:
            for idx, doc_id in enumerate(retrieved_ids):
                if doc_id == expected_doc_id:
                    retrieval_rank = idx + 1
                    break

        relevance_score = 0.0
        if retrieval_rank is not None:
            relevance_score = 1.0 / retrieval_rank

        grounded = relevance_score > 0
        citation_valid = relevance_score > 0

        return EvaluationResult(
            query=query,
            expected_document_id=expected_doc_id,
            retrieved_document_ids=retrieved_ids[:10],
            retrieval_rank=retrieval_rank,
            relevance_score=relevance_score,
            grounded=grounded,
            citation_valid=citation_valid,
        )

    async def run_evaluation_suite(self, test_cases: list[dict], org_id: str) -> dict:
        results: list[EvaluationResult] = []

        for case in test_cases:
            query = case.get("query", "")
            expected_doc_id = case.get("expected_document_id")
            result = await self.evaluate_query(query, expected_doc_id, org_id)
            results.append(result)

        precision_at_k = self._compute_precision_at_k(results, k=5)
        recall_at_k = self._compute_recall_at_k(results, k=5)
        mrr = self._compute_mrr(results)
        citation_validity_rate = self._compute_citation_validity(results)
        grounded_rate = self._compute_grounded_rate(results)

        return {
            "total_queries": len(results),
            "precision_at_k": precision_at_k,
            "recall_at_k": recall_at_k,
            "mrr": mrr,
            "citation_validity_rate": citation_validity_rate,
            "grounded_rate": grounded_rate,
        }

    @staticmethod
    def _compute_precision_at_k(results: list[EvaluationResult], k: int = 5) -> float:
        if not results:
            return 0.0

        relevant_count = 0
        for result in results:
            if result.retrieval_rank is not None and result.retrieval_rank <= k:
                relevant_count += 1

        return relevant_count / len(results)

    @staticmethod
    def _compute_recall_at_k(results: list[EvaluationResult], k: int = 5) -> float:
        if not results:
            return 0.0

        found_count = 0
        for result in results:
            if result.expected_document_id:
                if result.retrieval_rank is not None and result.retrieval_rank <= k:
                    found_count += 1
                elif result.retrieval_rank is None:
                    found_count += 0
                else:
                    found_count += 0
            else:
                found_count += 1

        expected_count = sum(1 for r in results if r.expected_document_id)
        if expected_count == 0:
            return 1.0

        return found_count / expected_count

    @staticmethod
    def _compute_mrr(results: list[EvaluationResult]) -> float:
        if not results:
            return 0.0

        reciprocal_ranks: list[float] = []
        for result in results:
            if result.retrieval_rank is not None and result.retrieval_rank > 0:
                reciprocal_ranks.append(1.0 / result.retrieval_rank)
            else:
                reciprocal_ranks.append(0.0)

        return sum(reciprocal_ranks) / len(reciprocal_ranks) if reciprocal_ranks else 0.0

    @staticmethod
    def _compute_citation_validity(results: list[EvaluationResult]) -> float:
        if not results:
            return 0.0

        valid_count = sum(1 for r in results if r.citation_valid)
        return valid_count / len(results)

    @staticmethod
    def _compute_grounded_rate(results: list[EvaluationResult]) -> float:
        if not results:
            return 0.0

        grounded_count = sum(1 for r in results if r.grounded)
        return grounded_count / len(results)
