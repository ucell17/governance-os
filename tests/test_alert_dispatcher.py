"""Tests for Alert Dispatcher Agent."""
import pytest
from src.agents.alert_dispatcher import AlertDispatcherAgent
from src.models.dao import Proposal

@pytest.fixture
def dispatcher():
    return AlertDispatcherAgent()

class TestAlertDispatcher:
    def test_init(self, dispatcher):
        assert dispatcher.name == "alert_dispatcher"
        assert len(dispatcher.rules) >= 1

    def test_high_impact_alert(self, dispatcher):
        p = Proposal(id="1", title="Emergency", description="Urgent treasury allocation", dao_name="DAO", status="active", impact_level="high")
        import asyncio
        alerts = asyncio.get_event_loop().run_until_complete(dispatcher.process(p))
        assert len(alerts) >= 1

    def test_no_alert_low_impact(self, dispatcher):
        p = Proposal(id="2", title="Typo fix", description="Fix typo in docs", dao_name="DAO", status="active", impact_level="low")
        import asyncio
        alerts = asyncio.get_event_loop().run_until_complete(dispatcher.process(p))
        assert len(alerts) == 0

    def test_stats(self, dispatcher):
        stats = dispatcher.get_stats()
        assert "total_dispatched" in stats
