"""Tests for DAO connectors."""
import pytest
from src.connectors.snapshot import SnapshotConnector
from src.connectors.tally import TallyConnector

class TestSnapshotConnector:
    def test_init(self):
        c = SnapshotConnector()
        assert c is not None

    def test_api_url(self):
        c = SnapshotConnector()
        if hasattr(c, "api_url"):
            assert "snapshot" in c.api_url.lower() or "hub" in c.api_url.lower()

class TestTallyConnector:
    def test_init(self):
        c = TallyConnector()
        assert c is not None
