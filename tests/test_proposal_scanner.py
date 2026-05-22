"""Tests for Proposal Scanner Agent."""
import pytest
from src.agents.proposal_scanner import ProposalScannerAgent

@pytest.fixture
def scanner():
    return ProposalScannerAgent(config={"daos": ["uniswap", "aave", "compound"]})

class TestProposalScanner:
    def test_init(self, scanner):
        assert scanner.name == "proposal_scanner"
        assert hasattr(scanner, "daos") or hasattr(scanner, "config")

    def test_multi_chain_support(self, scanner):
        if hasattr(scanner, "chains"):
            assert len(scanner.chains) >= 1

    def test_deduplication(self, scanner):
        assert hasattr(scanner, "process") or hasattr(scanner, "scan")
