"""Sentiment Analyzer Agent — NLP-based community sentiment analysis.

Analyzes community discussions from forums, Discord, and Twitter to
gauge sentiment around governance proposals using NLP techniques.
"""

from __future__ import annotations

import logging
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from agents.base_agent import AgentResult, BaseAgent
from connectors.social import SocialConnector, SocialPost
from models.dao import Proposal
from utils.llm_client import LLMClient

logger = logging.getLogger(__name__)


@dataclass
class SentimentResult:
    """Aggregated sentiment analysis result."""
    dao_slug: str = ""
    proposal_id: str = ""
    overall_score: float = 0.0  # -1 to 1
    overall_label: str = "neutral"  # positive, negative, neutral, mixed
    confidence: float = 0.0
    total_posts_analyzed: int = 0
    positive_count: int = 0
    negative_count: int = 0
    neutral_count: int = 0
    key_topics: list[str] = field(default_factory=list)
    top_concerns: list[str] = field(default_factory=list)
    top_supporters: list[str] = field(default_factory=list)
    platform_breakdown: dict[str, float] = field(default_factory=dict)
    engagement_weighted_score: float = 0.0
    whale_sentiment: float = 0.0
    timestamp: Any = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_positive(self) -> bool:
        return self.overall_score > 0.2

    @property
    def is_negative(self) -> bool:
        return self.overall_score < -0.2

    @property
    def sentiment_strength(self) -> str:
        abs_score = abs(self.overall_score)
        if abs_score > 0.7:
            return "strong"
        if abs_score > 0.4:
            return "moderate"
        return "weak"


# Sentiment lexicon for governance-specific terms
GOVERNANCE_LEXICON = {
    # Positive terms
    "support": 0.6, "agree": 0.5, "bullish": 0.7, "yes": 0.4,
    "great": 0.6, "excellent": 0.7, "necessary": 0.4, "improvement": 0.5,
    "progress": 0.5, "beneficial": 0.6, "impressed": 0.6, "excited": 0.7,
    "innovative": 0.5, "solid": 0.4, "robust": 0.5, "forward": 0.3,
    "growth": 0.4, "sustainable": 0.4, "efficient": 0.4, "aligned": 0.4,
    # Negative terms
    "against": -0.6, "oppose": -0.7, "no": -0.4, "concerned": -0.4,
    "risky": -0.5, "dangerous": -0.7, "terrible": -0.8, "worried": -0.4,
    "oppose": -0.7, "reject": -0.6, "fail": -0.5, "bad": -0.5,
    "exploit": -0.8, "vulnerability": -0.6, "centralization": -0.5,
    "rug": -0.9, "scam": -0.9, "ponzi": -0.9, "dump": -0.6,
    "misallocation": -0.6, "waste": -0.5, "inflation": -0.4,
}

# Governance topic keywords
TOPIC_KEYWORDS = {
    "treasury": ["treasury", "fund", "budget", "spend", "allocation", "grant"],
    "tokenomics": ["token", "supply", "inflation", "emission", "burn", "mint"],
    "governance": ["vote", "quorum", "delegate", "proposal", "governor"],
    "security": ["security", "audit", "exploit", "vulnerability", "hack"],
    "partnerships": ["partner", "collaboration", "integration", "ecosystem"],
    "technical": ["upgrade", "migration", "contract", "protocol", "code"],
    "incentives": ["reward", "incentive", "staking", "yield", "liquidity"],
    "community": ["community", "ambassador", "education", "outreach"],
}


class SentimentAnalyzerAgent(BaseAgent):
    """Agent for analyzing community sentiment around governance proposals.

    Combines lexicon-based analysis, engagement weighting, and LLM-powered
    deep analysis to produce comprehensive sentiment scores.
    """

    def __init__(self, config: Any = None):
        super().__init__(name="SentimentAnalyzer", config=config)
        self.social = SocialConnector()
        self.llm = LLMClient()
        self.lexicon = GOVERNANCE_LEXICON.copy()

    def execute(self, input_data: dict[str, Any]) -> AgentResult:
        """Analyze sentiment for proposals or a DAO.

        Args:
            input_data: Must contain 'proposals' list or 'dao_slug'.

        Returns:
            AgentResult with list of SentimentResult objects.
        """
        proposals = input_data.get("proposals", [])
        dao_slug = input_data.get("dao_slug", "")

        if not proposals and not dao_slug:
            return AgentResult(success=False, errors=["No proposals or dao_slug provided"])

        results: list[SentimentResult] = []

        if proposals:
            for proposal in proposals:
                result = self.analyze_proposal_sentiment(proposal)
                results.append(result)
        elif dao_slug:
            result = self.analyze_dao_sentiment(dao_slug)
            results.append(result)

        return AgentResult(
            success=True,
            data=results,
            tokens_used=self.llm.total_tokens_used,
        )

    def analyze_proposal_sentiment(self, proposal: Proposal) -> SentimentResult:
        """Analyze sentiment for a specific proposal.

        Collects social posts mentioning the proposal, scores them using
        the governance lexicon, and optionally runs LLM analysis.
        """
        self.logger.info("Analyzing sentiment for proposal: %s", proposal.title[:50])

        # Collect social discussions
        posts = self.social.aggregate_dao_discussions(proposal.dao_slug)
        proposal_posts = [p for p in posts if self._mentions_proposal(p, proposal)]

        if not proposal_posts:
            proposal_posts = posts[:20]  # Fall back to general DAO discussions

        return self._compute_sentiment(proposal_posts, proposal.dao_slug, proposal.id)

    def analyze_dao_sentiment(self, dao_slug: str) -> SentimentResult:
        """Analyze overall sentiment for a DAO."""
        self.logger.info("Analyzing sentiment for DAO: %s", dao_slug)
        posts = self.social.aggregate_dao_discussions(dao_slug)
        return self._compute_sentiment(posts, dao_slug)

    def _compute_sentiment(
        self,
        posts: list[SocialPost],
        dao_slug: str = "",
        proposal_id: str = "",
    ) -> SentimentResult:
        """Compute aggregate sentiment from a list of social posts."""
        if not posts:
            return SentimentResult(
                dao_slug=dao_slug,
                proposal_id=proposal_id,
                overall_score=0.0,
                overall_label="neutral",
                confidence=0.0,
            )

        scores: list[float] = []
        platform_scores: dict[str, list[float]] = {}
        engagement_scores: list[tuple[float, float]] = []
        topics: Counter = Counter()
        concerns: list[str] = []
        support_phrases: list[str] = []

        for post in posts:
            # Lexicon-based scoring
            score = self._score_text(post.content)
            scores.append(score)
            post.sentiment_score = score

            # Platform breakdown
            platform_scores.setdefault(post.platform, []).append(score)

            # Engagement-weighted scoring
            engagement = max(1, post.engagement_score)
            engagement_scores.append((score, engagement))

            # Extract topics
            for topic, keywords in TOPIC_KEYWORDS.items():
                if any(kw in post.content.lower() for kw in keywords):
                    topics[topic] += 1

            # Extract concerns and support
            if score < -0.3:
                concerns.append(post.content[:100])
            elif score > 0.3:
                support_phrases.append(post.content[:100])

        # Compute overall score
        overall = sum(scores) / len(scores) if scores else 0.0

        # Compute engagement-weighted score
        total_engagement = sum(e for _, e in engagement_scores)
        if total_engagement > 0:
            weighted = sum(s * e for s, e in engagement_scores) / total_engagement
        else:
            weighted = overall

        # Determine label
        if overall > 0.2:
            label = "positive"
        elif overall < -0.2:
            label = "negative"
        elif abs(overall) < 0.1:
            label = "neutral"
        else:
            label = "mixed"

        # Platform breakdown averages
        platform_avg = {
            p: sum(s) / len(s) for p, s in platform_scores.items()
        }

        # Confidence based on volume and consistency
        consistency = 1 - (max(scores) - min(scores)) / 2 if scores else 0
        volume_factor = min(1.0, len(posts) / 20)
        confidence = consistency * 0.6 + volume_factor * 0.4

        result = SentimentResult(
            dao_slug=dao_slug,
            proposal_id=proposal_id,
            overall_score=round(overall, 4),
            overall_label=label,
            confidence=round(confidence, 3),
            total_posts_analyzed=len(posts),
            positive_count=sum(1 for s in scores if s > 0.2),
            negative_count=sum(1 for s in scores if s < -0.2),
            neutral_count=sum(1 for s in scores if -0.2 <= s <= 0.2),
            key_topics=[t for t, _ in topics.most_common(5)],
            top_concerns=concerns[:5],
            top_supporters=support_phrases[:5],
            platform_breakdown=platform_avg,
            engagement_weighted_score=round(weighted, 4),
        )

        self.logger.info(
            "Sentiment for %s: score=%.3f label=%s posts=%d confidence=%.2f",
            dao_slug, overall, label, len(posts), confidence,
        )
        return result

    def _score_text(self, text: str) -> float:
        """Score a single text using the governance lexicon.

        Returns a score between -1 (very negative) and 1 (very positive).
        """
        if not text:
            return 0.0

        words = re.findall(r'\b\w+\b', text.lower())
        if not words:
            return 0.0

        total_score = 0.0
        matched = 0

        for word in words:
            if word in self.lexicon:
                total_score += self.lexicon[word]
                matched += 1

        if matched == 0:
            return 0.0

        # Normalize to -1 to 1 range
        raw = total_score / matched
        return max(-1.0, min(1.0, raw))

    def _mentions_proposal(self, post: SocialPost, proposal: Proposal) -> bool:
        """Check if a social post mentions a specific proposal."""
        text = post.content.lower()
        title_words = proposal.title.lower().split()
        # Check if key title words appear in the post
        matches = sum(1 for w in title_words if len(w) > 3 and w in text)
        return matches >= 2 or proposal.id in text

    def analyze_batch(self, texts: list[str]) -> list[dict[str, float]]:
        """Analyze sentiment for a batch of texts."""
        return [
            {"text": t[:100], "score": self._score_text(t)}
            for t in texts
        ]

    def get_trending_topics(self, dao_slug: str) -> list[dict[str, Any]]:
        """Get trending governance topics for a DAO."""
        posts = self.social.aggregate_dao_discussions(dao_slug)
        topics: Counter = Counter()
        for post in posts:
            for topic, keywords in TOPIC_KEYWORDS.items():
                if any(kw in post.content.lower() for kw in keywords):
                    topics[topic] += 1
        return [{"topic": t, "mentions": c} for t, c in topics.most_common(10)]

    def close(self) -> None:
        """Close connectors."""
        self.social.close()
