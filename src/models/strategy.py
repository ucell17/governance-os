"""Voting strategy and outcome models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class StrategyType(Enum):
    """Types of voting strategies."""
    FOLLOW_MAJORITY = "follow_majority"
    CONTRARIAN = "contrarian"
    WHALE_TRACKING = "whale_tracking"
    SENTIMENT_BASED = "sentiment_based"
    GAME_THEORY_OPTIMAL = "game_theory_optimal"
    DELEGATION_RECOMMEND = "delegation_recommend"


class OutcomeScenario(Enum):
    """Proposal outcome scenarios."""
    BEST_CASE = "best_case"
    EXPECTED = "expected"
    WORST_CASE = "worst_case"
    BLACK_SWAN = "black_swan"


class RiskLevel(Enum):
    """Risk assessment levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class VotingStrategy:
    """Recommended voting strategy for a proposal."""
    proposal_id: str = ""
    dao_slug: str = ""
    strategy_type: StrategyType = StrategyType.GAME_THEORY_OPTIMAL
    recommended_vote: str = "for"  # for, against, abstain
    confidence: float = 0.0  # 0-1
    reasoning: str = ""
    expected_outcome: str = ""
    risk_level: RiskLevel = RiskLevel.MEDIUM
    key_factors: list[str] = field(default_factory=list)
    whale_positions: list[dict[str, Any]] = field(default_factory=list)
    sentiment_score: float = 0.0  # -1 to 1
    model_simulations: int = 0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_high_confidence(self) -> bool:
        return self.confidence >= 0.75

    @property
    def action_urgency(self) -> str:
        if self.risk_level == RiskLevel.CRITICAL and self.confidence > 0.8:
            return "immediate"
        if self.risk_level == RiskLevel.HIGH:
            return "urgent"
        return "normal"


@dataclass
class OutcomeScenarioResult:
    """Result of a single outcome scenario simulation."""
    scenario: OutcomeScenario = OutcomeScenario.EXPECTED
    probability: float = 0.0
    treasury_impact_usd: float = 0.0
    token_price_impact_pct: float = 0.0
    protocol_risk_score: float = 0.0
    description: str = ""
    key_changes: list[str] = field(default_factory=list)
    recovery_time_days: int = 0


@dataclass
class ImpactSimulation:
    """Full impact simulation result for a proposal."""
    proposal_id: str = ""
    dao_slug: str = ""
    scenarios: list[OutcomeScenarioResult] = field(default_factory=list)
    overall_risk: RiskLevel = RiskLevel.MEDIUM
    expected_treasury_impact_usd: float = 0.0
    expected_token_impact_pct: float = 0.0
    simulation_count: int = 0
    confidence_interval: tuple[float, float] = (0.0, 0.0)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def best_case(self) -> OutcomeScenarioResult | None:
        return next((s for s in self.scenarios if s.scenario == OutcomeScenario.BEST_CASE), None)

    @property
    def worst_case(self) -> OutcomeScenarioResult | None:
        return next((s for s in self.scenarios if s.scenario == OutcomeScenario.WORST_CASE), None)

    @property
    def expected(self) -> OutcomeScenarioResult | None:
        return next((s for s in self.scenarios if s.scenario == OutcomeScenario.EXPECTED), None)

    def risk_reward_ratio(self) -> float:
        """Calculate risk/reward ratio from scenarios."""
        best = self.best_case
        worst = self.worst_case
        if not best or not worst:
            return 0.0
        upside = best.treasury_impact_usd
        downside = abs(worst.treasury_impact_usd)
        return upside / downside if downside > 0 else float("inf")


@dataclass
class GovernanceBriefing:
    """Complete governance briefing report."""
    proposal_id: str = ""
    dao_slug: str = ""
    title: str = ""
    executive_summary: str = ""
    proposal_analysis: str = ""
    sentiment_analysis: str = ""
    voting_strategy: VotingStrategy | None = None
    impact_simulation: ImpactSimulation | None = None
    risk_assessment: str = ""
    recommendations: list[str] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.utcnow)
    token_count: int = 0
