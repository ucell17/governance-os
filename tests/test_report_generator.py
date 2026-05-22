"""Tests for Report Generator Agent."""
import pytest
from src.agents.report_generator import ReportGeneratorAgent
from src.models.dao import Proposal

@pytest.fixture
def reporter():
    return ReportGeneratorAgent()

class TestReportGenerator:
    def test_init(self, reporter):
        assert reporter.name == "report_generator"

    def test_briefing_generation(self, reporter):
        proposals = [Proposal(id="1", title="Test", description="D", dao_name="DAO", status="active")]
        import asyncio
        briefing = asyncio.get_event_loop().run_until_complete(reporter.process(proposals))
        assert briefing.total_proposals == 1
        assert "Governance" in briefing.markdown

    def test_stats(self, reporter):
        stats = reporter.get_stats()
        assert "reports_generated" in stats
