"""DAO, Proposal, and Vote data models."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class ProposalState(Enum):
    """Proposal lifecycle states."""
    PENDING = "pending"
    ACTIVE = "active"
    PASSED = "passed"
    FAILED = "failed"
    EXECUTED = "executed"
    CANCELLED = "cancelled"
    QUEUED = "queued"
    EXPIRED = "expired"


class VoteChoice(Enum):
    """Vote options."""
    FOR = "for"
    AGAINST = "against"
    ABSTAIN = "abstain"


class ChainType(Enum):
    """Supported blockchain types."""
    ETHEREUM = "ethereum"
    ARBITRUM = "arbitrum"
    OPTIMISM = "optimism"
    POLYGON = "polygon"
    BASE = "base"
    SOLANA = "solana"


@dataclass
class Vote:
    """A single vote on a proposal."""
    voter: str
    choice: VoteChoice
    weight: float
    timestamp: datetime | None = None
    reason: str = ""
    tx_hash: str = ""
    delegated_power: float = 0.0

    def effective_weight(self) -> float:
        """Calculate effective voting weight including delegation."""
        return self.weight + self.delegated_power


@dataclass
class Proposal:
    """A governance proposal."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    dao_slug: str = ""
    title: str = ""
    description: str = ""
    proposer: str = ""
    state: ProposalState = ProposalState.PENDING
    chain: ChainType = ChainType.ETHEREUM
    created_at: datetime = field(default_factory=datetime.utcnow)
    start_time: datetime | None = None
    end_time: datetime | None = None
    votes_for: float = 0.0
    votes_against: float = 0.0
    votes_abstain: float = 0.0
    quorum: float = 0.0
    total_voting_power: float = 0.0
    votes: list[Vote] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    source: str = ""  # snapshot, tally, onchain
    source_url: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def total_votes(self) -> float:
        return self.votes_for + self.votes_against + self.votes_abstain

    @property
    def approval_rate(self) -> float:
        total = self.votes_for + self.votes_against
        if total == 0:
            return 0.0
        return self.votes_for / total

    @property
    def quorum_reached(self) -> bool:
        return self.total_votes >= self.quorum

    @property
    def is_active(self) -> bool:
        return self.state == ProposalState.ACTIVE

    @property
    def time_remaining_hours(self) -> float:
        if not self.end_time:
            return 0.0
        delta = self.end_time - datetime.utcnow()
        return max(0, delta.total_seconds() / 3600)

    def top_voters(self, n: int = 10) -> list[Vote]:
        """Get top N voters by weight."""
        return sorted(self.votes, key=lambda v: v.effective_weight(), reverse=True)[:n]

    def whale_concentration(self) -> float:
        """Calculate what % of votes are from top 10 voters."""
        if not self.votes:
            return 0.0
        top = sum(v.effective_weight() for v in self.top_voters(10))
        total = sum(v.effective_weight() for v in self.votes)
        return top / total if total > 0 else 0.0


@dataclass
class DAO:
    """A DAO entity."""
    slug: str = ""
    name: str = ""
    chain: ChainType = ChainType.ETHEREUM
    snapshot_space: str = ""
    tally_org_id: str = ""
    governance_contract: str = ""
    token_address: str = ""
    token_symbol: str = ""
    total_supply: float = 0.0
    treasury_address: str = ""
    treasury_value_usd: float = 0.0
    total_proposals: int = 0
    active_proposals: int = 0
    forum_url: str = ""
    discord_url: str = ""
    twitter_handle: str = ""
    website: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def proposal_activity_rate(self) -> float:
        """Proposals per day (rough metric)."""
        if self.total_proposals == 0:
            return 0.0
        return self.total_proposals / 365.0


@dataclass
class DAOSnapshot:
    """Point-in-time snapshot of DAO state."""
    dao_slug: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    treasury_usd: float = 0.0
    token_price_usd: float = 0.0
    active_proposals: int = 0
    voter_participation_rate: float = 0.0
    top_holders: list[dict[str, Any]] = field(default_factory=list)
    recent_outcomes: list[str] = field(default_factory=list)
