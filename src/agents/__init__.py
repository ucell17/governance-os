"""GovernanceOS agents package."""
from agents.proposal_scanner import ProposalScannerAgent
from agents.sentiment_analyzer import SentimentAnalyzerAgent
from agents.voting_strategist import VotingStrategistAgent
from agents.impact_modeler import ImpactModelerAgent
from agents.report_generator import ReportGeneratorAgent
from agents.alert_dispatcher import AlertDispatcherAgent

__all__ = [
    "ProposalScannerAgent",
    "SentimentAnalyzerAgent",
    "VotingStrategistAgent",
    "ImpactModelerAgent",
    "ReportGeneratorAgent",
    "AlertDispatcherAgent",
]
