"""Alert Dispatcher Agent — sends real-time alerts for high-impact proposals."""

import logging
from datetime import datetime
from typing import Optional
from .base_agent import BaseAgent
from ..models.alert import Alert, AlertRule

logger = logging.getLogger(__name__)


class AlertDispatcherAgent(BaseAgent):
    """Agent 6: Dispatches real-time alerts for governance events via multiple channels."""

    DEFAULT_RULES = [
        AlertRule(name="high_impact", condition="impact_level == 'high'", channels=["telegram", "email"], priority=1),
        AlertRule(name="new_proposal", condition="status == 'active'", channels=["telegram"], priority=3),
        AlertRule(name="voting_ending", condition="hours_remaining < 24", channels=["telegram", "email"], priority=2),
    ]

    def __init__(self, config=None):
        super().__init__(name="alert_dispatcher", config=config)
        self.rules: list[AlertRule] = list(self.DEFAULT_RULES)
        self.dispatched: list[Alert] = []
        self.rate_limit = {"telegram": 0, "email": 0, "max_per_hour": 20}

    async def process(self, proposal, impact_analysis=None) -> list[Alert]:
        """Evaluate proposal against alert rules and dispatch notifications."""
        self.log_action("evaluating alerts", proposal.title[:40])
        alerts = []

        for rule in self.rules:
            if self._matches_rule(proposal, rule, impact_analysis):
                alert = Alert(
                    rule_name=rule.name,
                    proposal_id=proposal.id,
                    title=f"[{rule.name.upper()}] {proposal.title[:60]}",
                    message=self._format_alert(proposal, rule, impact_analysis),
                    channels=rule.channels,
                    priority=rule.priority,
                    dispatched_at=datetime.utcnow().isoformat()
                )

                if self._can_dispatch(alert):
                    alerts.append(alert)
                    self.dispatched.append(alert)
                    for ch in alert.channels:
                        self.rate_limit[ch] = self.rate_limit.get(ch, 0) + 1

        return alerts

    def _matches_rule(self, proposal, rule: AlertRule, impact) -> bool:
        if rule.name == "high_impact":
            return getattr(proposal, "impact_level", "") == "high"
        if rule.name == "new_proposal":
            return getattr(proposal, "status", "") == "active"
        if rule.name == "voting_ending":
            return getattr(proposal, "hours_remaining", 999) < 24
        return False

    def _can_dispatch(self, alert: Alert) -> bool:
        for ch in alert.channels:
            if self.rate_limit.get(ch, 0) >= self.rate_limit.get("max_per_hour", 20):
                logger.warning(f"Rate limit reached for {ch}")
                return False
        return True

    def _format_alert(self, proposal, rule, impact) -> str:
        parts = [
            f"🚨 {rule.name.replace('_', ' ').title()} Alert",
            f"DAO: {proposal.dao_name}",
            f"Proposal: {proposal.title[:80]}",
            f"Status: {proposal.status}",
        ]
        if impact:
            parts.append(f"Risk: {impact.risk_level}")
        return "\n".join(parts)

    def get_stats(self) -> dict:
        return {
            "total_dispatched": len(self.dispatched),
            "rules_active": len(self.rules),
            "rate_limits": {k: v for k, v in self.rate_limit.items() if k != "max_per_hour"}
        }
