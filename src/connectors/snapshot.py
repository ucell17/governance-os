"""Snapshot.org GraphQL API connector."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import httpx

from models.dao import ChainType, DAO, Proposal, ProposalState, Vote, VoteChoice

logger = logging.getLogger(__name__)

SNAPSHOT_API = "https://hub.snapshot.org/graphql"

# Well-known Snapshot spaces for major DAOs
KNOWN_SPACES = {
    "ens": "ens.eth",
    "aave": "aave.eth",
    "uniswap": "uniswap.eth",
    "compound": "comp-vote.eth",
    "gitcoin": "gitcoindao.eth",
    "arbitrum": "arbitrumfoundation.eth",
    "optimism": "opcollective.eth",
    "lido": "lido-snapshot.eth",
    "curve": "curve.eth",
    "makerdao": "makerdao.eth",
    "dydx": "dydxgov.eth",
    "hop": "hop.eth",
    "safe": "safe.eth",
    "balancer": "balancer.eth",
    "pooltogether": "pooltogether.eth",
    "nouns": "nouns.eth",
    "ens-governance": "ens.eth",
    "yearn": "ybaby.eth",
    "sushi": "sushigov.eth",
    "morpho": "morpho.eth",
    "radiant": "radiantcapital.eth",
    "pendle": "pendle-gov.eth",
    "gmx": "gmx.eth",
    "apecoin": "apecoin.eth",
    "optimism-grants": "opgrants.eth",
}


class SnapshotConnector:
    """Connector for Snapshot.org governance platform.

    Fetches proposals, votes, and space data via Snapshot's GraphQL API.
    Supports all Snapshot-based DAOs across 10+ chains.
    """

    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout
        self._client: httpx.Client | None = None

    @property
    def client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(timeout=self.timeout)
        return self._client

    def get_space(self, space_id: str) -> dict[str, Any]:
        """Get Snapshot space details."""
        query = """
        query GetSpace($id: String!) {
            space(id: $id) {
                id
                name
                about
                network
                symbol
                members
                followersCount
                proposalsCount
                voting {
                    delay
                    period
                    type
                    quorum
                }
            }
        }
        """
        result = self._graphql_query(query, {"id": space_id})
        return result.get("data", {}).get("space", {})

    def get_proposals(
        self,
        space_id: str,
        state: str = "all",
        first: int = 20,
        skip: int = 0,
    ) -> list[dict[str, Any]]:
        """Fetch proposals from a Snapshot space.

        Args:
            space_id: Snapshot space identifier (e.g., 'ens.eth').
            state: Filter by state ('active', 'closed', 'all').
            first: Number of proposals to fetch.
            skip: Pagination offset.

        Returns:
            List of proposal dictionaries from Snapshot API.
        """
        query = """
        query GetProposals($space: String!, $state: String, $first: Int, $skip: Int) {
            proposals(
                where: { space: $space, state: $state }
                orderBy: "created"
                orderDirection: desc
                first: $first
                skip: $skip
            ) {
                id
                title
                body
                choices
                start
                end
                snapshot
                state
                author
                scores
                scores_total
                quorum
                votes
                created
                type
                space {
                    id
                    name
                    network
                }
                votes(orderBy: "vp", orderDirection: desc, first: 20) {
                    voter
                    choice
                    vp
                    reason
                    created
                }
            }
        }
        """
        variables = {"space": space_id, "state": state, "first": first, "skip": skip}
        result = self._graphql_query(query, variables)
        return result.get("data", {}).get("proposals", [])

    def get_proposal(self, proposal_id: str) -> dict[str, Any]:
        """Fetch a single proposal by ID."""
        query = """
        query GetProposal($id: String!) {
            proposal(id: $id) {
                id
                title
                body
                choices
                start
                end
                snapshot
                state
                author
                scores
                scores_total
                quorum
                votes
                created
                type
                space {
                    id
                    name
                    network
                }
            }
        }
        """
        result = self._graphql_query(query, {"id": proposal_id})
        return result.get("data", {}).get("proposal", {})

    def get_votes(self, proposal_id: str, first: int = 1000) -> list[dict[str, Any]]:
        """Fetch all votes for a proposal."""
        query = """
        query GetVotes($proposal: String!, $first: Int) {
            votes(
                where: { proposal: $proposal }
                orderBy: "vp"
                orderDirection: desc
                first: $first
            ) {
                voter
                choice
                vp
                reason
                created
            }
        }
        """
        result = self._graphql_query(query, {"proposal": proposal_id, "first": first})
        return result.get("data", {}).get("votes", [])

    def convert_to_proposal(self, raw: dict[str, Any], dao_slug: str = "") -> Proposal:
        """Convert raw Snapshot proposal to Proposal model."""
        state_map = {
            "active": ProposalState.ACTIVE,
            "closed": ProposalState.PASSED,
            "pending": ProposalState.PENDING,
        }
        choice_map = {1: VoteChoice.FOR, 2: VoteChoice.AGAINST, 3: VoteChoice.ABSTAIN}

        votes = []
        for v in raw.get("votes", []):
            choice_val = v.get("choice", 1)
            if isinstance(choice_val, list):
                choice_val = choice_val[0] if choice_val else 1
            votes.append(Vote(
                voter=v.get("voter", ""),
                choice=choice_map.get(choice_val, VoteChoice.FOR),
                weight=v.get("vp", 0),
                reason=v.get("reason", ""),
                timestamp=datetime.fromtimestamp(v.get("created", 0)),
            ))

        scores = raw.get("scores", [])
        space = raw.get("space", {})

        return Proposal(
            id=raw.get("id", ""),
            dao_slug=dao_slug or space.get("id", ""),
            title=raw.get("title", ""),
            description=raw.get("body", "")[:2000],
            proposer=raw.get("author", ""),
            state=state_map.get(raw.get("state", ""), ProposalState.PENDING),
            chain=ChainType.ETHEREUM,
            created_at=datetime.fromtimestamp(raw.get("created", 0)),
            start_time=datetime.fromtimestamp(raw.get("start", 0)),
            end_time=datetime.fromtimestamp(raw.get("end", 0)),
            votes_for=scores[0] if len(scores) > 0 else 0,
            votes_against=scores[1] if len(scores) > 1 else 0,
            votes_abstain=scores[2] if len(scores) > 2 else 0,
            quorum=raw.get("quorum", 0),
            total_voting_power=raw.get("scores_total", 0),
            votes=votes,
            source="snapshot",
            source_url=f"https://snapshot.org/#/proposal/{raw.get('id', '')}",
        )

    def _graphql_query(self, query: str, variables: dict) -> dict[str, Any]:
        """Execute a GraphQL query against Snapshot."""
        try:
            response = self.client.post(
                SNAPSHOT_API,
                json={"query": query, "variables": variables},
            )
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, httpx.TimeoutException) as e:
            logger.error("Snapshot API error: %s", e)
            return {"data": {}, "errors": [str(e)]}

    def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            self._client.close()
            self._client = None
