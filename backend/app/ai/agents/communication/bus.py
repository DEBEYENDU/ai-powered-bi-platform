"""Communication bus — message passing between agents."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from app.ai.agents.schemas import AgentMessage, MessageType


class CommunicationBus:
    """In-process message bus for inter-agent communication."""

    def __init__(self) -> None:
        self._inbox: dict[str, list[AgentMessage]] = defaultdict(list)
        self._outbox: dict[str, list[AgentMessage]] = defaultdict(list)
        self._history: list[AgentMessage] = []

    def send(self, message: AgentMessage) -> None:
        """Send a message to an agent's inbox."""
        self._inbox[message.to_agent].append(message)
        self._outbox[message.from_agent].append(message)
        self._history.append(message)

    def receive(self, agent_type: str, limit: int = 10) -> list[AgentMessage]:
        """Receive messages from an agent's inbox."""
        messages = self._inbox[agent_type][-limit:]
        return messages

    def receive_latest(self, agent_type: str) -> AgentMessage | None:
        """Receive the latest message from an agent's inbox."""
        inbox = self._inbox.get(agent_type, [])
        return inbox[-1] if inbox else None

    def clear_inbox(self, agent_type: str) -> None:
        """Clear an agent's inbox."""
        self._inbox.pop(agent_type, None)

    def get_history(
        self,
        task_id: str | None = None,
        agent_type: str | None = None,
        limit: int = 50,
    ) -> list[AgentMessage]:
        """Get message history with optional filtering."""
        msgs = self._history
        if task_id:
            msgs = [m for m in msgs if m.task_id == task_id]
        if agent_type:
            msgs = [m for m in msgs if m.from_agent == agent_type or m.to_agent == agent_type]
        return msgs[-limit:]

    def delegate_task(
        self,
        from_agent: str,
        to_agent: str,
        task_id: str,
        content: dict[str, Any],
    ) -> AgentMessage:
        """Create and send a delegation message."""
        msg = AgentMessage(
            from_agent=from_agent,
            to_agent=to_agent,
            message_type=MessageType.DELEGATE,
            content=content,
            task_id=task_id,
        )
        self.send(msg)
        return msg

    def send_result(
        self,
        from_agent: str,
        to_agent: str,
        task_id: str,
        result: dict[str, Any],
    ) -> AgentMessage:
        """Send a result message back."""
        msg = AgentMessage(
            from_agent=from_agent,
            to_agent=to_agent,
            message_type=MessageType.RESULT,
            content=result,
            task_id=task_id,
        )
        self.send(msg)
        return msg

    def request_clarification(
        self,
        from_agent: str,
        to_agent: str,
        task_id: str,
        question: str,
    ) -> AgentMessage:
        """Request clarification about a task."""
        msg = AgentMessage(
            from_agent=from_agent,
            to_agent=to_agent,
            message_type=MessageType.CLARIFICATION,
            content={"question": question},
            task_id=task_id,
        )
        self.send(msg)
        return msg

    def send_error(
        self,
        from_agent: str,
        to_agent: str,
        task_id: str,
        error: str,
    ) -> AgentMessage:
        """Report an error."""
        msg = AgentMessage(
            from_agent=from_agent,
            to_agent=to_agent,
            message_type=MessageType.ERROR,
            content={"error": error},
            task_id=task_id,
        )
        self.send(msg)
        return msg

    def get_stats(self) -> dict[str, int]:
        return {
            "total_messages": len(self._history),
            "inboxes_active": len(self._inbox),
            "outboxes_active": len(self._outbox),
        }


# Singleton
_bus: CommunicationBus | None = None


def get_bus() -> CommunicationBus:
    global _bus
    if _bus is None:
        _bus = CommunicationBus()
    return _bus
