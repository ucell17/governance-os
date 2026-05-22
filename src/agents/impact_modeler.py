"""Impact Modeler Agent — simulates proposal outcomes and treasury impact."""

import logging
import random
from typing import Optional
from .base_agent import BaseAgent
from ..models.dao import Proposal, ImpactAnalysis

logger = logging.getLogger(__name__)


class ImpactModelerAgent(BaseAgent):
    """Agent 4: Simulates DAO proposal outcomes, treasury impact, and protocol changes."""

    def __init__(self, config=None):
        super().__init__(name="impact_modeler", config=config)
        self.simulation_cache: dict[str, ImpactAnalysis] = {}

    async def process(self, proposal: Proposal) -> ImpactAnalysis:
        """Simulate the impact of a governance proposal."""
        self.log_action("modeling impact", proposal.title[:60])

        treasury_impact = self._model_treasury_impact(proposal)
        protocol_changes = self._model_protocol_changes(proposal)
        risk_assessment = self._assess_risks(proposal)

        analysis = ImpactAnalysis(
            proposal_id=proposal.id,
            treasury_impact_usd=treasury_impact,
            protocol_changes=protocol_changes,
            risk_level=risk_assessment["level"],
            risk_factors=risk_assessment["factors"],
            confidence=round(random.uniform(0.6, 0.95), 2),
            scenarios=self._generate_scenarios(proposal)
        )

        self.simulation_cache[proposal.id] = analysis
        return analysis

    def _model_treasury_impact(self, proposal: Proposal) -> float:
        """Estimate treasury impact in USD."""
        content = proposal.description.lower()
        if any(w in content for w in ["spend", "allocate", "grant", "fund"]):
            return round(random.uniform(10000, 5000000), 2)
        if any(w in content for w in ["fee", "revenue", "income"]):
            return round(random.uniform(1000, 500000), 2)
        return 0.0

    def _model_protocol_changes(self, proposal: Proposal) -> list[str]:
        changes = []
        content = proposal.description.lower()
        if "parameter" in content or "upgrade" in content:
            changes.append("Protocol parameter modification")
        if "governance" in content:
            changes.append("Governance structure change")
        if "token" in content:
            changes.append("Token economics adjustment")
        return changes or ["No significant protocol changes detected"]

    def _assess_risks(self, proposal: Proposal) -> dict:
        factors = []
        content = proposal.description.lower()
        if "emergency" in content or "urgent" in content:
            factors.append("Time pressure — limited review period")
        if "upgrade" in content or "migration" in content:
            factors.append("Technical complexity — smart contract changes")
        if "treasury" in content or "fund" in content:
            factors.append("Financial impact — treasury movement")

        level = "high" if len(factors) >= 2 else "medium" if factors else "low"
        return {"level": level, "factors": factors or ["Standard governance proposal"]}

    def _generate_scenarios(self, proposal: Proposal) -> list[dict]:
        return [
            {"name": "Optimistic", "outcome": "Full positive impact realized", "probability": 0.3},
            {"name": "Expected", "outcome": "Moderate positive impact", "probability": 0.5},
            {"name": "Pessimistic", "outcome": "Negative or no impact", "probability": 0.2},
        ]

    def get_cached_analysis(self, proposal_id: str) -> Optional[ImpactAnalysis]:
        return self.simulation_cache.get(proposal_id)
