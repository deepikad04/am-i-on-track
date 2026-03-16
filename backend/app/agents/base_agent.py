import time
import logging
from abc import ABC, abstractmethod
from app.models.schemas import AgentEvent, AgentName, AgentEventType

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Abstract base class for all agents."""

    name: AgentName
    display_name: str

    def emit(self, event_type: AgentEventType, message: str, step: int | None = None, data: dict | None = None) -> AgentEvent:
        return AgentEvent(
            agent=self.name,
            event_type=event_type,
            step=step,
            message=message,
            data=data,
            timestamp=time.time(),
        )

    @abstractmethod
    async def run(self, input_data: dict, emit: callable) -> dict:
        """Run the agent. emit() is a callback to send SSE events."""
        pass
