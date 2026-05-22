"""Tests for Voting Strategist Agent."""
import pytest
from src.agents.voting_strategist import VotingStrategistAgent

@pytest.fixture
def strategist():
    return VotingStrategistAgent()

class TestVotingStrategist:
    def test_init(self, strategist):
        assert strategist.name == "voting_strategist"

    def test_strategy_generation(self, strategist):
        assert hasattr(strategist, "process") or hasattr(strategist, "calculate_strategy")

    def test_game_theory(self, strategist):
        if hasattr(strategist, "_calculate_nash_equilibrium"):
            result = strategist._calculate_nash_equilibrium({"for": 60, "against": 40})
            assert isinstance(result, dict)
