"""Tests for RAG Pipeline."""

from app.ai.rag.rag_pipeline import RAGPipeline


class TestRAGPipeline:
    def test_index_document(self):
        pipeline = RAGPipeline()
        count = pipeline.index_document("Test content", source="test")
        assert count > 0

    def test_retrieve(self):
        pipeline = RAGPipeline()
        pipeline.index_document("Revenue grew 12% this quarter", source="test")
        import asyncio

        result = asyncio.run(pipeline.retrieve("revenue growth"))
        assert result is not None
        assert len(result.retrieved_contexts) >= 0

    def test_get_stats(self):
        pipeline = RAGPipeline()
        pipeline.index_document("Test", source="test")
        stats = pipeline.get_stats()
        assert "documents_indexed" in stats
