"""Simulation engine for governance proposal outcome modeling."""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from typing import Any

from models.strategy import (
    ImpactSimulation,
    OutcomeScenario,
    OutcomeScenarioResult,
    RiskLevel,
)

logger = logging.getLogger(__name__)


@dataclass
class SimulationParams:
    """Parameters for running a governance simulation."""
    proposal_id: str = ""
    dao_slug: str = ""
    treasury_usd: float = 0.0
    token_price_usd: float = 0.0
    total_supply: float = 0.0
    current_approval_rate: float = 0.5
    voter_participation: float = 0.1
    whale_concentration: float = 0.3
    proposal_type: str = "parameter_change"
    num_simulations: int = 1000
    metadata: dict[str, Any] = field(default_factory=dict)


class MonteCarloSimulator:
    """Monte Carlo simulation engine for governance proposals.

    Runs thousands of simulations to model potential outcomes based on
    current voting patterns, market conditions, and historical data.
    """

    def __init__(self, seed: int | None = None):
        self.rng = random.Random(seed)
        self.simulation_count = 0

    def simulate(self, params: SimulationParams) -> ImpactSimulation:
        """Run Monte Carlo simulation for a proposal.

        Args:
            params: Simulation parameters including DAO state and proposal details.

        Returns:
            ImpactSimulation with scenario results and risk assessment.
        """
        logger.info(
            "Running %d simulations for proposal %s (DAO: %s)",
            params.num_simulations, params.proposal_id, params.dao_slug,
        )

        outcomes: list[dict[str, float]] = []

        for _ in range(params.num_simulations):
            outcome = self._run_single_simulation(params)
            outcomes.append(outcome)

        self.simulation_count += params.num_simulations

        scenarios = self._aggregate_outcomes(outcomes, params)
        overall_risk = self._assess_risk(scenarios, params)

        expected_treasury = sum(o["treasury_impact"] for o in outcomes) / len(outcomes)
        expected_token = sum(o["token_impact"] for o in outcomes) / len(outcomes)

        treasury_sorted = sorted(o["treasury_impact"] for o in outcomes)
        ci_low = treasury_sorted[int(0.05 * len(treasury_sorted))]
        ci_high = treasury_sorted[int(0.95 * len(treasury_sorted))]

        return ImpactSimulation(
            proposal_id=params.proposal_id,
            dao_slug=params.dao_slug,
            scenarios=scenarios,
            overall_risk=overall_risk,
            expected_treasury_impact_usd=expected_treasury,
            expected_token_impact_pct=expected_token,
            simulation_count=params.num_simulations,
            confidence_interval=(ci_low, ci_high),
        )

    def _run_single_simulation(self, params: SimulationParams) -> dict[str, float]:
        """Run a single Monte Carlo iteration."""
        # Model vote outcome uncertainty
        vote_noise = self.rng.gauss(0, 0.1)
        final_approval = max(0, min(1, params.current_approval_rate + vote_noise))

        # Model participation uncertainty
        participation_noise = self.rng.gauss(0, 0.05)
        final_participation = max(0, min(1, params.voter_participation + participation_noise))

        # Model treasury impact based on proposal type
        base_impact = self._calculate_base_impact(params.proposal_type, params.treasury_usd)
        market_factor = self.rng.gauss(1.0, 0.15)
        treasury_impact = base_impact * market_factor * final_approval

        # Model token price impact
        token_impact_base = self._calculate_token_impact(params.proposal_type, final_approval)
        token_impact = token_impact_base * self.rng.gauss(1.0, 0.2)

        # Risk score
        risk_score = (
            (1 - final_participation) * 0.3
            + params.whale_concentration * 0.3
            + abs(token_impact) / 10 * 0.2
            + (1 if params.proposal_type in ["treasury", "upgrade"] else 0) * 0.2
        )

        return {
            "treasury_impact": treasury_impact,
            "token_impact": token_impact,
            "approval": final_approval,
            "participation": final_participation,
            "risk_score": min(1, risk_score),
        }

    def _calculate_base_impact(self, proposal_type: str, treasury: float) -> float:
        """Calculate base treasury impact by proposal type."""
        impact_rates = {
            "parameter_change": 0.0,
            "treasury": 0.05,
            "upgrade": 0.02,
            "grant": 0.01,
            "fee_change": 0.005,
            "incentive": 0.008,
            "partnership": 0.003,
        }
        rate = impact_rates.get(proposal_type, 0.01)
        return treasury * rate * self.rng.choice([-1, 1])

    def _calculate_token_impact(self, proposal_type: str, approval: float) -> float:
        """Calculate token price impact percentage."""
        base = {
            "parameter_change": 0.5,
            "treasury": 2.0,
            "upgrade": 3.0,
            "grant": 0.3,
            "fee_change": 1.5,
            "incentive": 1.0,
            "partnership": 0.8,
        }.get(proposal_type, 1.0)
        direction = 1 if approval > 0.5 else -1
        return base * direction * self.rng.uniform(0.5, 1.5)

    def _aggregate_outcomes(
        self, outcomes: list[dict[str, float]], params: SimulationParams
    ) -> list[OutcomeScenarioResult]:
        """Aggregate simulation outcomes into scenario results."""
        treasury_impacts = sorted(o["treasury_impact"] for o in outcomes)
        token_impacts = sorted(o["token_impact"] for o in outcomes)
        n = len(outcomes)

        scenarios = []

        # Best case (90th percentile)
        scenarios.append(OutcomeScenarioResult(
            scenario=OutcomeScenario.BEST_CASE,
            probability=0.15,
            treasury_impact_usd=treasury_impacts[int(0.9 * n)],
            token_price_impact_pct=token_impacts[int(0.9 * n)],
            protocol_risk_score=outcomes[int(0.1 * n)]["risk_score"],
            description="Optimal outcome with favorable market conditions",
            key_changes=["High voter participation", "Strong community support"],
            recovery_time_days=0,
        ))

        # Expected (median)
        scenarios.append(OutcomeScenarioResult(
            scenario=OutcomeScenario.EXPECTED,
            probability=0.50,
            treasury_impact_usd=treasury_impacts[int(0.5 * n)],
            token_price_impact_pct=token_impacts[int(0.5 * n)],
            protocol_risk_score=outcomes[int(0.5 * n)]["risk_score"],
            description="Most likely outcome based on current trends",
            key_changes=["Moderate participation", "Expected approval rate"],
            recovery_time_days=7,
        ))

        # Worst case (10th percentile)
        scenarios.append(OutcomeScenarioResult(
            scenario=OutcomeScenario.WORST_CASE,
            probability=0.15,
            treasury_impact_usd=treasury_impacts[int(0.1 * n)],
            token_price_impact_pct=token_impacts[int(0.1 * n)],
            protocol_risk_score=outcomes[int(0.9 * n)]["risk_score"],
            description="Adverse outcome requiring mitigation",
            key_changes=["Low participation", "Whale opposition"],
            recovery_time_days=30,
        ))

        # Black swan (1st percentile)
        scenarios.append(OutcomeScenarioResult(
            scenario=OutcomeScenario.BLACK_SWAN,
            probability=0.02,
            treasury_impact_usd=treasury_impacts[0],
            token_price_impact_pct=token_impacts[0],
            protocol_risk_score=1.0,
            description="Extreme tail risk event",
            key_changes=["Governance attack", "Critical vulnerability"],
            recovery_time_days=90,
        ))

        return scenarios

    def _assess_risk(
        self, scenarios: list[OutcomeScenarioResult], params: SimulationParams
    ) -> RiskLevel:
        """Assess overall risk level from simulation results."""
        worst = next(s for s in scenarios if s.scenario == OutcomeScenario.WORST_CASE)
        black_swan = next(s for s in scenarios if s.scenario == OutcomeScenario.BLACK_SWAN)

        risk_score = (
            worst.protocol_risk_score * 0.4
            + params.whale_concentration * 0.3
            + (abs(worst.treasury_impact_usd) / max(params.treasury_usd, 1)) * 0.3
        )

        if risk_score > 0.8 or black_swan.protocol_risk_score > 0.9:
            return RiskLevel.CRITICAL
        if risk_score > 0.6:
            return RiskLevel.HIGH
        if risk_score > 0.3:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW


class SensitivityAnalyzer:
    """Analyze sensitivity of outcomes to parameter changes."""

    @staticmethod
    def analyze_parameter_sensitivity(
        base_params: SimulationParams,
        param_name: str,
        values: list[float],
        simulator: MonteCarloSimulator,
    ) -> list[ImpactSimulation]:
        """Run sensitivity analysis on a single parameter."""
        results = []
        for value in values:
            modified = SimulationParams(
                proposal_id=base_params.proposal_id,
                dao_slug=base_params.dao_slug,
                treasury_usd=base_params.treasury_usd,
                token_price_usd=base_params.token_price_usd,
                total_supply=base_params.total_supply,
                current_approval_rate=(
                    value if param_name == "current_approval_rate"
                    else base_params.current_approval_rate
                ),
                voter_participation=(
                    value if param_name == "voter_participation"
                    else base_params.voter_participation
                ),
                whale_concentration=(
                    value if param_name == "whale_concentration"
                    else base_params.whale_concentration
                ),
                proposal_type=base_params.proposal_type,
                num_simulations=min(base_params.num_simulations, 100),
            )
            results.append(simulator.simulate(modified))
        return results
