"""Base agent class for GovernanceOS pipeline agents."""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class AgentResult:
    """Result from an agent execution."""
    agent_name: str = ""
    success: bool = True
    data: Any = None
    errors: list[str] = field(default_factory=list)
    tokens_used: int = 0
    duration_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_error(self, error: str) -> None:
        self.errors.append(error)
        self.success = False


class BaseAgent(ABC):
    """Base class for all GovernanceOS agents.

    Provides common functionality for logging, error handling, metrics
    tracking, and pipeline integration. All agents inherit from this
    and implement the `execute` method.
    """

    def __init__(self, name: str = "", config: Any = None):
        self.name = name or self.__class__.__name__
        self.config = config
        self.logger = logging.getLogger(f"govos.{self.name}")
        self._execution_count = 0
        self._total_duration_ms = 0.0
        self._total_tokens = 0
        self._errors: list[str] = []

    @abstractmethod
    def execute(self, input_data: dict[str, Any]) -> AgentResult:
        """Execute the agent's primary task.

        Args:
            input_data: Dictionary containing input from previous agent or CLI.

        Returns:
            AgentResult with processed data, metrics, and any errors.
        """
        ...

    def run(self, input_data: dict[str, Any] | None = None) -> AgentResult:
        """Run the agent with timing and error handling.

        Wraps execute() with automatic timing, error handling, and metrics.
        """
        input_data = input_data or {}
        start = time.time()

        self.logger.info("Starting %s execution", self.name)

        try:
            result = self.execute(input_data)
        except Exception as e:
            self.logger.error("%s failed: %s", self.name, str(e), exc_info=True)
            result = AgentResult(agent_name=self.name, success=False)
            result.add_error(str(e))
            self._errors.append(str(e))

        duration = (time.time() - start) * 1000
        result.duration_ms = duration
        result.agent_name = self.name

        self._execution_count += 1
        self._total_duration_ms += duration
        self._total_tokens += result.tokens_used

        self.logger.info(
            "%s completed: success=%s duration=%.1fms tokens=%d",
            self.name, result.success, duration, result.tokens_used,
        )
        return result

    def get_metrics(self) -> dict[str, Any]:
        """Get agent performance metrics."""
        return {
            "name": self.name,
            "executions": self._execution_count,
            "total_duration_ms": self._total_duration_ms,
            "avg_duration_ms": (
                self._total_duration_ms / self._execution_count
                if self._execution_count > 0 else 0
            ),
            "total_tokens": self._total_tokens,
            "total_errors": len(self._errors),
            "recent_errors": self._errors[-5:],
        }

    def reset_metrics(self) -> None:
        """Reset all metrics counters."""
        self._execution_count = 0
        self._total_duration_ms = 0.0
        self._total_tokens = 0
        self._errors.clear()
