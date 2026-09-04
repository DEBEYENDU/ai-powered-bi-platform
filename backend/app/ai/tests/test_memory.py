"""Tests for Conversation Memory."""

from app.ai.memory.memory import ConversationMemory


class TestConversationMemory:
    def test_add_message(self):
        memory = ConversationMemory()
        msg = memory.add_message("user", "Test message")
        assert msg.content == "Test message"

    def test_get_history(self):
        memory = ConversationMemory()
        memory.add_message("user", "Hello")
        history = memory.get_session_history()
        assert len(history) >= 1

    def test_add_long_term_memory(self):
        memory = ConversationMemory()
        entry = memory.add_long_term_memory("Test context")
        assert entry.content == "Test context"

    def test_business_context(self):
        memory = ConversationMemory()
        entry = memory.add_business_context("org_123", "Test context", org_id="org_123")
        assert entry.content == "Test context"
        assert memory.get_business_context("org_123") is not None

    def test_get_recent_queries(self):
        memory = ConversationMemory()
        memory.add_recent_query("test query")
        queries = memory.get_recent_queries()
        assert len(queries) >= 1
