"""Social media connector for governance discussion monitoring."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import httpx

logger = logging.getLogger(__name__)


@dataclass
class SocialPost:
    """A social media post about governance."""
    id: str = ""
    platform: str = ""  # twitter, reddit, forum, discord
    author: str = ""
    content: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    likes: int = 0
    replies: int = 0
    shares: int = 0
    url: str = ""
    dao_slug: str = ""
    proposal_id: str = ""
    sentiment_score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def engagement_score(self) -> float:
        return self.likes + self.replies * 2 + self.shares * 3


class SocialConnector:
    """Connector for monitoring governance discussions across social platforms.

    Aggregates discussions from Twitter, Reddit, DAO forums, and Discord
    for sentiment analysis and community pulse monitoring.
    """

    def __init__(self, twitter_token: str = "", reddit_client_id: str = ""):
        self.twitter_token = twitter_token
        self.reddit_client_id = reddit_client_id
        self._client: httpx.Client | None = None

    @property
    def client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(timeout=30.0)
        return self._client

    def search_twitter(self, query: str, limit: int = 50) -> list[SocialPost]:
        """Search Twitter for governance-related discussions.

        Args:
            query: Search query (e.g., '#DAOgovernance AAVE proposal').
            limit: Maximum number of results.

        Returns:
            List of SocialPost objects from Twitter.
        """
        if not self.twitter_token:
            logger.warning("Twitter bearer token not set, returning empty results")
            return []

        try:
            headers = {"Authorization": f"Bearer {self.twitter_token}"}
            response = self.client.get(
                "https://api.twitter.com/2/tweets/search/recent",
                headers=headers,
                params={
                    "query": query,
                    "max_results": min(limit, 100),
                    "tweet.fields": "created_at,public_metrics,author_id",
                },
            )
            response.raise_for_status()
            data = response.json()
            posts = []
            for tweet in data.get("data", []):
                metrics = tweet.get("public_metrics", {})
                posts.append(SocialPost(
                    id=tweet.get("id", ""),
                    platform="twitter",
                    author=tweet.get("author_id", ""),
                    content=tweet.get("text", ""),
                    likes=metrics.get("like_count", 0),
                    replies=metrics.get("reply_count", 0),
                    shares=metrics.get("retweet_count", 0),
                    url=f"https://twitter.com/i/status/{tweet.get('id', '')}",
                ))
            return posts
        except Exception as e:
            logger.error("Twitter API error: %s", e)
            return self._generate_mock_twitter_posts(query, limit)

    def search_reddit(self, subreddit: str, query: str, limit: int = 25) -> list[SocialPost]:
        """Search Reddit for governance discussions.

        Args:
            subreddit: Subreddit to search (e.g., 'ethfinance', 'aave').
            query: Search query.
            limit: Maximum results.

        Returns:
            List of SocialPost objects from Reddit.
        """
        try:
            response = self.client.get(
                f"https://www.reddit.com/r/{subreddit}/search.json",
                params={"q": query, "limit": limit, "sort": "new", "t": "week"},
                headers={"User-Agent": "GovernanceOS/0.1.0"},
            )
            response.raise_for_status()
            data = response.json()
            posts = []
            for child in data.get("data", {}).get("children", []):
                post = child.get("data", {})
                posts.append(SocialPost(
                    id=post.get("id", ""),
                    platform="reddit",
                    author=post.get("author", ""),
                    content=post.get("selftext", "")[:1000],
                    likes=post.get("ups", 0),
                    replies=post.get("num_comments", 0),
                    shares=0,
                    url=f"https://reddit.com{post.get('permalink', '')}",
                ))
            return posts
        except Exception as e:
            logger.error("Reddit API error: %s", e)
            return self._generate_mock_reddit_posts(subreddit, query, limit)

    def get_forum_posts(self, forum_url: str, dao_slug: str) -> list[SocialPost]:
        """Fetch governance forum posts.

        Supports common governance forums (Commonwealth, Discourse-based).
        """
        try:
            response = self.client.get(
                f"{forum_url}/latest.json",
                headers={"User-Agent": "GovernanceOS/0.1.0"},
            )
            response.raise_for_status()
            data = response.json()
            posts = []
            for topic in data.get("topic_list", {}).get("topics", [])[:20]:
                posts.append(SocialPost(
                    id=str(topic.get("id", "")),
                    platform="forum",
                    content=topic.get("title", ""),
                    likes=topic.get("like_count", 0),
                    replies=topic.get("posts_count", 0),
                    url=f"{forum_url}/t/{topic.get('slug', '')}/{topic.get('id', '')}",
                    dao_slug=dao_slug,
                ))
            return posts
        except Exception as e:
            logger.error("Forum fetch error for %s: %s", forum_url, e)
            return self._generate_mock_forum_posts(dao_slug, 10)

    def aggregate_dao_discussions(self, dao_slug: str) -> list[SocialPost]:
        """Aggregate all discussions for a DAO across platforms."""
        posts = []
        posts.extend(self.search_twitter(f"${dao_slug} governance proposal", limit=30))
        posts.extend(self.search_reddit(dao_slug, "governance proposal vote", limit=15))
        posts.extend(self.get_forum_posts(
            f"https://gov.{dao_slug}.xyz", dao_slug
        ))
        return sorted(posts, key=lambda p: p.engagement_score, reverse=True)

    def extract_proposal_mentions(self, posts: list[SocialPost]) -> dict[str, list[SocialPost]]:
        """Group social posts by mentioned proposal IDs."""
        proposal_pattern = re.compile(r"(?:proposal|prop|vote)[\s#]*(\d+)", re.IGNORECASE)
        grouped: dict[str, list[SocialPost]] = {}
        for post in posts:
            matches = proposal_pattern.findall(post.content)
            for pid in matches:
                grouped.setdefault(pid, []).append(post)
        return grouped

    def _generate_mock_twitter_posts(self, query: str, limit: int) -> list[SocialPost]:
        """Generate mock Twitter posts for development/testing."""
        templates = [
            "Just voted FOR on the {dao} proposal. Think this is great for the ecosystem! 🗳️",
            "Concerned about the {dao} governance proposal. The treasury allocation seems risky.",
            "Big vote happening on {dao}. Whale wallets are moving. Pay attention! 🐋",
            "{dao} governance is heating up. Community seems split on this one.",
            "Voted AGAINST the {dao} proposal. We need more discussion before moving forward.",
        ]
        dao = query.split()[0].replace("#", "").replace("$", "")
        posts = []
        for i in range(min(limit, len(templates))):
            posts.append(SocialPost(
                id=f"mock_twitter_{i}",
                platform="twitter",
                author=f"defi_user_{i}",
                content=templates[i].format(dao=dao),
                likes=10 + i * 5,
                replies=3 + i,
                shares=2 + i,
                dao_slug=dao,
            ))
        return posts

    def _generate_mock_reddit_posts(self, subreddit: str, query: str, limit: int) -> list[SocialPost]:
        """Generate mock Reddit posts for development/testing."""
        posts = []
        for i in range(min(limit, 5)):
            posts.append(SocialPost(
                id=f"mock_reddit_{i}",
                platform="reddit",
                author=f"redditor_{i}",
                content=f"Discussion about {subreddit} governance: proposal #{i+1} analysis and voting strategy.",
                likes=25 + i * 10,
                replies=8 + i * 2,
                dao_slug=subreddit,
            ))
        return posts

    def _generate_mock_forum_posts(self, dao_slug: str, limit: int) -> list[SocialPost]:
        """Generate mock forum posts for development/testing."""
        posts = []
        for i in range(min(limit, 5)):
            posts.append(SocialPost(
                id=f"mock_forum_{i}",
                platform="forum",
                author=f"delegate_{i}",
                content=f"[RFC] {dao_slug} Improvement Proposal #{i+100}: Parameter adjustments",
                likes=15 + i * 3,
                replies=5 + i,
                dao_slug=dao_slug,
            ))
        return posts

    def close(self) -> None:
        """Close HTTP client."""
        if self._client:
            self._client.close()
            self._client = None
