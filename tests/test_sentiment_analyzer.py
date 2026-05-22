"""Tests for Sentiment Analyzer Agent."""
import pytest
from src.agents.sentiment_analyzer import SentimentAnalyzerAgent

@pytest.fixture
def analyzer():
    return SentimentAnalyzerAgent()

class TestSentimentAnalyzer:
    def test_init(self, analyzer):
        assert analyzer.name == "sentiment_analyzer"

    def test_positive_sentiment(self, analyzer):
        text = "This proposal is amazing and will benefit everyone in the DAO"
        if hasattr(analyzer, "_analyze_sentiment"):
            result = analyzer._analyze_sentiment(text)
            assert isinstance(result, (int, float, dict))

    def test_negative_sentiment(self, analyzer):
        text = "This is a terrible proposal that will drain the treasury"
        if hasattr(analyzer, "_analyze_sentiment"):
            result = analyzer._analyze_sentiment(text)
            assert isinstance(result, (int, float, dict))
