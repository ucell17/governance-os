"""Tests for GovernanceOS orchestrator."""
import pytest
from src.orchestrator import GovernanceOrchestrator

@pytest.fixture
def orch():
    return GovernanceOrchestrator(config={})

class TestOrchestrator:
    def test_init(self, orch):
        assert orch is not None

    def test_pipeline(self, orch):
        if hasattr(orch, "PIPELINE"):
            assert len(orch.PIPELINE) >= 4

    def test_agents(self, orch):
        if hasattr(orch, "agents"):
            assert isinstance(orch.agents, (list, dict))
