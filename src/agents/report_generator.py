"""Report Generator Agent — creates comprehensive governance briefings."""

import logging
from datetime import datetime
from typing import Optional
from .base_agent import BaseAgent
from ..models.dao import Proposal, GovernanceBriefing

logger = logging.getLogger(__name__)


class ReportGeneratorAgent(BaseAgent):
    """Agent 5: Creates comprehensive governance briefings and analysis reports."""

    def __init__(self, config=None):
        super().__init__(name="report_generator", config=config)
        self.generated_reports: list[GovernanceBriefing] = []

    async def process(self, proposals: list[Proposal], sentiment_data: dict = None, impact_data: dict = None) -> GovernanceBriefing:
        """Generate a governance briefing for a set of proposals."""
        self.log_action("generating report", f"{len(proposals)} proposals")

        briefing = GovernanceBriefing(
            generated_at=datetime.utcnow().isoformat(),
            total_proposals=len(proposals),
            active_proposals=[p for p in proposals if p.status == "active"],
            passed_proposals=[p for p in proposals if p.status == "passed"],
            high_impact=[p for p in proposals if p.impact_level == "high"],
            summary=self._generate_summary(proposals),
            recommendations=self._generate_recommendations(proposals, impact_data),
            markdown=self._generate_markdown(proposals, sentiment_data, impact_data)
        )

        self.generated_reports.append(briefing)
        return briefing

    def _generate_summary(self, proposals: list[Proposal]) -> str:
        active = len([p for p in proposals if p.status == "active"])
        high = len([p for p in proposals if p.impact_level == "high"])
        if high > 0:
            return f"{active} active proposals with {high} high-impact items requiring immediate attention."
        return f"{active} active proposals. No high-impact items detected."

    def _generate_recommendations(self, proposals: list, impact_data: dict) -> list[str]:
        recs = []
        for p in proposals:
            if p.impact_level == "high":
                recs.append(f"Review {p.title[:50]} — high treasury impact expected")
        return recs or ["No urgent recommendations. Monitor active proposals."]

    def _generate_markdown(self, proposals, sentiment, impact) -> str:
        lines = [
            "# Governance Intelligence Briefing",
            f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
            "",
            f"## Summary: {len(proposals)} Proposals Tracked",
            "",
            "## Active Proposals",
        ]
        for p in proposals[:10]:
            lines.append(f"- **{p.title[:60]}** ({p.dao_name}) — Status: {p.status}")

        if sentiment:
            lines.extend(["", "## Sentiment Analysis", str(sentiment)])
        if impact:
            lines.extend(["", "## Impact Assessment", str(impact)])

        return "\n".join(lines)

    def get_stats(self) -> dict:
        return {"reports_generated": len(self.generated_reports)}
