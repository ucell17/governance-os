"""Alert and alert rule models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class AlertSeverity(Enum):
    """Alert severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertChannel(Enum):
    """Alert delivery channels."""
    TELEGRAM = "telegram"
    TWITTER = "twitter"
    WEBHOOK = "webhook"
    EMAIL = "email"
    CONSOLE = "console"


class AlertType(Enum):
    """Types of governance alerts."""
    NEW_PROPOSAL = "new_proposal"
    PROPOSAL_PASSED = "proposal_passed"
    PROPOSAL_FAILED = "proposal_failed"
    WHALE_VOTE = "whale_vote"
    QUORUM_REACHED = "quorum_reached"
    SENTIMENT_SHIFT = "sentiment_shift"
    HIGH_IMPACT = "high_impact"
    TREASURY_CHANGE = "treasury_change"
    EXECUTION = "execution"


@dataclass
class Alert:
    """A governance alert."""
    id: str = ""
    alert_type: AlertType = AlertType.NEW_PROPOSAL
    severity: AlertSeverity = AlertSeverity.MEDIUM
    dao_slug: str = ""
    proposal_id: str = ""
    title: str = ""
    message: str = ""
    channels: list[AlertChannel] = field(default_factory=list)
    sent: bool = False
    sent_at: datetime | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_critical(self) -> bool:
        return self.severity == AlertSeverity.CRITICAL

    @property
    def formatted_message(self) -> str:
        severity_emoji = {
            AlertSeverity.LOW: "ℹ️",
            AlertSeverity.MEDIUM: "⚠️",
            AlertSeverity.HIGH: "🔶",
            AlertSeverity.CRITICAL: "🚨",
        }
        emoji = severity_emoji.get(self.severity, "📢")
        return f"{emoji} [{self.severity.value.upper()}] {self.title}\n\n{self.message}"


@dataclass
class AlertRule:
    """Rule for triggering alerts."""
    id: str = ""
    name: str = ""
    alert_type: AlertType = AlertType.NEW_PROPOSAL
    severity: AlertSeverity = AlertSeverity.MEDIUM
    channels: list[AlertChannel] = field(default_factory=list)
    conditions: dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    cooldown_minutes: int = 60
    last_triggered: datetime | None = None

    def should_trigger(self, context: dict[str, Any]) -> bool:
        """Check if alert rule conditions are met."""
        if not self.enabled:
            return False
        if self.last_triggered:
            elapsed = (datetime.utcnow() - self.last_triggered).total_seconds() / 60
            if elapsed < self.cooldown_minutes:
                return False
        for key, threshold in self.conditions.items():
            value = context.get(key, 0)
            if isinstance(threshold, (int, float)) and isinstance(value, (int, float)):
                if value < threshold:
                    return False
        return True
