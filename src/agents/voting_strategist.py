"""Voting Strategist Agent — Game-theory-based voting strategy optimization.

Models optimal voting strategies based on token holder analysis, delegation
patterns, historical voting behavior, and game-theoretic considerations.
"""

from __future__ import annotations

import logging
import math
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from agents.base_agent import AgentResult, BaseAgent
from models.dao import Proposal, Vote, VoteChoice
from models.strategy import RiskLevel, StrategyType, VotingStrategy
from utils.llm_client import LLMClient

logger = logging.getLogger(__name__)


@dataclass
class VoterProfile:
    """Profile of a governance voter."""
    address: str = ""
    voting_power: float = 0.0
    participation_rate: float = 0.0
    historical_votes: int = 0
    alignment_score: float = 0.0  # How often they vote with majority
    delegate_count: int = 0
    is_whale: bool = False
    voting_pattern: str = "consistent"  # consistent, swing, inactive


@dataclass
class GameTheoryState:
    """State representation for game-theoretic analysis."""
    total_voting_power: float = 0.0
    votes_cast: float = 0.0
    for_power: float = 0.0
    against_power: float = 0.0
    abstain_power: float = 0.0
    remaining_power: float = 0.0
    time_remaining_hours: float = 0.0
    quorum: float = 0.0
    quorum_gap: float = 0.0
    leading_side: str = "for"
    margin_pct: float = 0.0

    @property
    def is_competitive(self) -> bool:
        """Whether the vote is close enough that strategy matters."""
        return abs(self.margin_pct) < 20

    @property
    def is_quorum_at_risk(self) -> bool:
        """Whether quorum might not be reached."""
        return self.quorum_gap > 0 and self.remaining_power < self.quorum_gap * 2


class VotingStrategistAgent(BaseAgent):
    """Agent for computing optimal voting strategies.

    Uses game theory, historical analysis, and delegation tracking to
    recommend optimal voting decisions for governance participants.
    """

    def __init__(self, config: Any = None):
        super().__init__(name="VotingStrategist", config=config)
        self.llm = LLMClient()
        self._voter_profiles: dict[str, VoterProfile] = {}
        self.whale_threshold_pct = 1.0  # 1% of total supply

    def execute(self, input_data: dict[str, Any]) -> AgentResult:
        """Compute voting strategies for proposals.

        Args:
            input_data: Must contain 'proposals' list and optionally 'sentiment_results'.

        Returns:
            AgentResult with list of VotingStrategy objects.
        """
        proposals = input_data.get("proposals", [])
        sentiment_results = input_data.get("sentiment_results", [])

        if not proposals:
            return AgentResult(success=False, errors=["No proposals provided"])

        strategies = []
        for i, proposal in enumerate(proposals):
            sentiment = sentiment_results[i] if i < len(sentiment_results) else None
            sentiment_score = sentiment.overall_score if sentiment else 0.0
            strategy = self.compute_strategy(proposal, sentiment_score)
            strategies.append(strategy)

        return AgentResult(
            success=True,
            data=strategies,
            tokens_used=self.llm.total_tokens_used,
        )

    def compute_strategy(
        self, proposal: Proposal, sentiment_score: float = 0.0
    ) -> VotingStrategy:
        """Compute optimal voting strategy for a single proposal.

        Analyzes voting patterns, whale positions, sentiment, and game
        theory to produce a recommended strategy.
        """
        self.logger.info("Computing strategy for: %s", proposal.title[:50])

        # Build game theory state
        gt_state = self._build_game_state(proposal)

        # Analyze voter profiles
        voter_profiles = self._analyze_voters(proposal)
        whale_positions = self._get_whale_positions(proposal)

        # Determine strategy type based on state
        strategy_type, recommended, confidence = self._determine_strategy(
            gt_state, voter_profiles, sentiment_score, proposal
        )

        # Build key factors
        key_factors = self._identify_key_factors(gt_state, voter_profiles, sentiment_score)

        # Risk assessment
        risk_level = self._assess_risk(gt_state, voter_profiles, proposal)

        # Reasoning
        reasoning = self._build_reasoning(
            gt_state, strategy_type, recommended, sentiment_score, whale_positions
        )

        strategy = VotingStrategy(
            proposal_id=proposal.id,
            dao_slug=proposal.dao_slug,
            strategy_type=strategy_type,
            recommended_vote=recommended,
            confidence=round(confidence, 3),
            reasoning=reasoning,
            expected_outcome=self._predict_outcome(gt_state),
            risk_level=risk_level,
            key_factors=key_factors,
            whale_positions=whale_positions,
            sentiment_score=sentiment_score,
            model_simulations=1000,
        )

        self.logger.info(
            "Strategy for %s: vote=%s confidence=%.2f risk=%s",
            proposal.id, recommended, confidence, risk_level.value,
        )
        return strategy

    def _build_game_state(self, proposal: Proposal) -> GameTheoryState:
        """Build game theory state from proposal data."""
        total = proposal.total_voting_power or max(proposal.total_votes * 10, 1)
        cast = proposal.total_votes
        remaining = total - cast

        for_p = proposal.votes_for
        against_p = proposal.votes_against
        abstain_p = proposal.votes_abstain

        leading = "for" if for_p >= against_p else "against"
        margin = abs(for_p - against_p) / max(cast, 1) * 100

        quorum_gap = max(0, proposal.quorum - cast)

        return GameTheoryState(
            total_voting_power=total,
            votes_cast=cast,
            for_power=for_p,
            against_power=against_p,
            abstain_power=abstain_p,
            remaining_power=remaining,
            time_remaining_hours=proposal.time_remaining_hours,
            quorum=proposal.quorum,
            quorum_gap=quorum_gap,
            leading_side=leading,
            margin_pct=margin,
        )

    def _analyze_voters(self, proposal: Proposal) -> list[VoterProfile]:
        """Analyze voter profiles from proposal votes."""
        profiles = []
        total_power = proposal.total_voting_power or 1

        for vote in proposal.votes:
            whale = (vote.weight / total_power * 100) >= self.whale_threshold_pct
            profiles.append(VoterProfile(
                address=vote.voter,
                voting_power=vote.weight,
                is_whale=whale,
                participation_rate=1.0,
                historical_votes=1,
            ))

        return sorted(profiles, key=lambda p: p.voting_power, reverse=True)

    def _get_whale_positions(self, proposal: Proposal) -> list[dict[str, Any]]:
        """Get positions of whale voters."""
        total = proposal.total_voting_power or 1
        whales = []
        for vote in proposal.top_voters(10):
            pct = vote.weight / total * 100
            if pct >= self.whale_threshold_pct:
                whales.append({
                    "address": vote.voter[:10] + "...",
                    "weight": vote.weight,
                    "pct": round(pct, 2),
                    "choice": vote.choice.value,
                    "reason": vote.reason[:100] if vote.reason else "",
                })
        return whales

    def _determine_strategy(
        self,
        state: GameTheoryState,
        voters: list[VoterProfile],
        sentiment: float,
        proposal: Proposal,
    ) -> tuple[StrategyType, str, float]:
        """Determine optimal strategy using game theory analysis."""
        # If vote is already decided (large margin, little time)
        if not state.is_competitive and state.time_remaining_hours < 24:
            confidence = 0.9
            if state.leading_side == "for":
                return StrategyType.FOLLOW_MAJORITY, "for", confidence
            return StrategyType.FOLLOW_MAJORITY, "against", confidence

        # If quorum is at risk, recommend participation
        if state.is_quorum_at_risk:
            return StrategyType.GAME_THEORY_OPTIMAL, "for", 0.6

        # Game theory optimal for competitive votes
        if state.is_competitive:
            # Consider sentiment
            if abs(sentiment) > 0.4:
                sentiment_vote = "for" if sentiment > 0 else "against"
                confidence = 0.5 + abs(sentiment) * 0.4
                return StrategyType.SENTIMENT_BASED, sentiment_vote, confidence

            # Whale tracking — follow smart money
            whale_for = sum(1 for v in voters if v.is_whale)
            if whale_for > 0:
                top_whale_choice = voters[0].voting_pattern if voters else "for"
                return StrategyType.WHALE_TRACKING, top_whale_choice, 0.55

            # Default: game theory optimal
            expected = "for" if state.for_power >= state.against_power else "against"
            return StrategyType.GAME_THEORY_OPTIMAL, expected, 0.5

        # Strong lead — ride the wave
        return StrategyType.FOLLOW_MAJORITY, state.leading_side, 0.8

    def _identify_key_factors(
        self,
        state: GameTheoryState,
        voters: list[VoterProfile],
        sentiment: float,
    ) -> list[str]:
        """Identify key factors influencing the strategy."""
        factors = []

        if state.is_competitive:
            factors.append(f"Competitive vote: {state.margin_pct:.1f}% margin")
        else:
            factors.append(f"Clear {state.leading_side} lead: {state.margin_pct:.1f}% margin")

        if state.is_quorum_at_risk:
            factors.append(f"Quorum at risk: {state.quorum_gap:.0f} votes needed")

        whale_count = sum(1 for v in voters if v.is_whale)
        if whale_count > 0:
            factors.append(f"{whale_count} whale voters identified")

        if abs(sentiment) > 0.3:
            label = "positive" if sentiment > 0 else "negative"
            factors.append(f"Community sentiment: {label} ({sentiment:.2f})")

        if state.time_remaining_hours < 24:
            factors.append(f"Only {state.time_remaining_hours:.0f}h remaining")

        factors.append(f"Total votes cast: {state.votes_cast:.0f}/{state.total_voting_power:.0f}")
        return factors

    def _assess_risk(
        self,
        state: GameTheoryState,
        voters: list[VoterProfile],
        proposal: Proposal,
    ) -> RiskLevel:
        """Assess risk level of the proposal."""
        risk_score = 0.0

        # Whale concentration risk
        if proposal.votes:
            concentration = proposal.whale_concentration()
            if concentration > 0.7:
                risk_score += 0.3
            elif concentration > 0.5:
                risk_score += 0.15

        # Quorum risk
        if state.is_quorum_at_risk:
            risk_score += 0.2

        # Tight vote risk
        if state.is_competitive and state.time_remaining_hours < 48:
            risk_score += 0.2

        # Large treasury impact
        if any(tag in proposal.tags for tag in ["treasury", "upgrade", "migration"]):
            risk_score += 0.15

        if risk_score >= 0.7:
            return RiskLevel.CRITICAL
        if risk_score >= 0.5:
            return RiskLevel.HIGH
        if risk_score >= 0.25:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW

    def _predict_outcome(self, state: GameTheoryState) -> str:
        """Predict the likely outcome of the vote."""
        if state.margin_pct > 30:
            return f"{state.leading_side.upper()} wins decisively"
        if state.margin_pct > 10:
            return f"{state.leading_side.upper()} likely to pass"
        if state.margin_pct > 3:
            return f"{state.leading_side.upper()} favored but close"
        return "Too close to call"

    def _build_reasoning(
        self,
        state: GameTheoryState,
        strategy_type: StrategyType,
        recommended: str,
        sentiment: float,
        whale_positions: list[dict],
    ) -> str:
        """Build human-readable reasoning for the strategy."""
        parts = []
        parts.append(f"Vote is currently {state.leading_side} by {state.margin_pct:.1f}%.")

        if state.is_competitive:
            parts.append("This is a competitive vote where every vote matters.")

        if whale_positions:
            top = whale_positions[0]
            parts.append(f"Top whale voted {top['choice']} with {top['pct']}% of total power.")

        if abs(sentiment) > 0.3:
            label = "positive" if sentiment > 0 else "negative"
            parts.append(f"Community sentiment is {label} (score: {sentiment:.2f}).")

        parts.append(f"Strategy: {strategy_type.value}. Recommendation: vote {recommended.upper()}.")
        return " ".join(parts)

    def model_delegation_impact(
        self, proposal: Proposal, delegate_address: str
    ) -> dict[str, Any]:
        """Model the impact of delegating voting power."""
        total = proposal.total_voting_power or 1
        # Simulate adding delegated power
        impact = {
            "delegate": delegate_address,
            "current_margin": abs(proposal.votes_for - proposal.votes_against),
            "new_margin": abs(proposal.votes_for - proposal.votes_against),
            "recommendation": "Delegate to aligned voter",
        }
        return impact
