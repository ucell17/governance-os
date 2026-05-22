"""Tests for Impact Modeler Agent."""
import pytest
from src.agents.impact_modeler import ImpactModelerAgent
from src.models.dao import Proposal

@pytest.fixture
def modeler():
    return ImpactModelerAgent()

class TestImpactModeler:
    def test_init(self, modeler):
        assert modeler.name == "impact_modeler"

    def test_treasury_impact(self, modeler):
        p = Proposal(id="1", title="Treasury Spend", description="Allocate 100K USDC for grants", dao_name="TestDAO", status="active")
        import asyncio
        result = asyncio.get_event_loop().run_until_complete(modeler.process(p))
        assert result.proposal_id == "1"
        assert result.risk_level in ["low", "medium", "high"]

    def test_scenarios(self, modeler):
        p = Proposal(id="2", title="Test", description="Simple upgrade", dao_name="DAO", status="active")
        import asyncio
        result = asyncio.get_event_loop().run_until_complete(modeler.process(p))
        assert len(result.scenarios) == 3
        assert sum(s["probability"] for s in result.scenarios) == pytest.approx(1.0)
