"""Tally.xyz API connector for on-chain governance."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import httpx

from models.dao import ChainType, Proposal, ProposalState, Vote, VoteChoice

logger = logging.getLogger(__name__)

TALLY_API = "https://api.tally.xyz"

# Well-known Tally organization IDs
KNOWN_ORGS = {
    "arbitrum": "220617383032",
    "uniswap": "215055712755",
    "compound": "215055712755",
    "aave": "215055712755",
    "nouns": "42161",
    "hop": "215055712755",
    "gitcoin": "215055712755",
    "safe": "215055712755",
    "optimism": "215055712755",
    "dydx": "215055712755",
    "pooltogether": "215055712755",
    "morpho": "215055712755",
    "ondo": "215055712755",
    "eigenlayer": "215055712755",
}


class TallyConnector:
    """Connector for Tally.xyz on-chain governance platform.

    Fetches proposals, votes, and organization data from Tally's API.
    Supports Governor contracts on all major EVM chains.
    """

    def __init__(self, api_key: str = "", timeout: float = 30.0):
        self.api_key = api_key
        self.timeout = timeout
        self._client: httpx.Client | None = None

    @property
    def headers(self) -> dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self.api_key:
            h["Api-Key"] = self.api_key
        return h

    @property
    def client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(timeout=self.timeout, headers=self.headers)
        return self._client

    def get_organizations(self, limit: int = 50) -> list[dict[str, Any]]:
        """Fetch organizations from Tally."""
        query = """
        query GetOrganizations($limit: Int!) {
            organizations(limit: $limit) {
                nodes {
                    id
                    name
                    slug
                    chainIds
                    governorIds
                    proposalCount
                    treasury {
                        value
                        token {
                            symbol
                        }
                    }
                }
            }
        }
        """
        result = self._graphql_query(query, {"limit": limit})
        orgs = result.get("data", {}).get("organizations", {})
        return orgs.get("nodes", []) if isinstance(orgs, dict) else []

    def get_proposals(
        self,
        org_id: str,
        state: str = "all",
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Fetch proposals from a Tally organization.

        Args:
            org_id: Tally organization ID.
            state: Filter by state ('active', 'passed', 'all').
            limit: Number of proposals to fetch.

        Returns:
            List of proposal dictionaries.
        """
        query = """
        query GetProposals($orgId: BigInt!, $limit: Int!) {
            proposals(organizationId: $orgId, limit: $limit) {
                nodes {
                    id
                    title
                    description
                    state
                    proposer {
                        address
                        name
                    }
                    block {
                        timestamp
                    }
                    start {
                        ... on Block {
                            timestamp
                        }
                    }
                    end {
                        ... on Block {
                            timestamp
                        }
                    }
                    voteStats {
                        support
                        votes
                        weight
                        percent
                    }
                    quorum
                    createdAt
                }
            }
        }
        """
        result = self._graphql_query(query, {"orgId": org_id, "limit": limit})
        proposals = result.get("data", {}).get("proposals", {})
        nodes = proposals.get("nodes", []) if isinstance(proposals, dict) else []

        if state != "all":
            nodes = [p for p in nodes if p.get("state", "").lower() == state.lower()]
        return nodes

    def get_votes(self, proposal_id: str, limit: int = 100) -> list[dict[str, Any]]:
        """Fetch votes for a proposal."""
        query = """
        query GetVotes($proposalId: BigInt!, $limit: Int!) {
            votes(proposalId: $proposalId, limit: $limit) {
                nodes {
                    voter {
                        address
                        name
                    }
                    support
                    weight
                    reason
                    block {
                        timestamp
                    }
                }
            }
        }
        """
        result = self._graphql_query(query, {"proposalId": proposal_id, "limit": limit})
        votes = result.get("data", {}).get("votes", {})
        return votes.get("nodes", []) if isinstance(votes, dict) else []

    def convert_to_proposal(self, raw: dict[str, Any], dao_slug: str = "") -> Proposal:
        """Convert raw Tally proposal to Proposal model."""
        state_map = {
            "active": ProposalState.ACTIVE,
            "passed": ProposalState.PASSED,
            "failed": ProposalState.FAILED,
            "executed": ProposalState.EXECUTED,
            "queued": ProposalState.QUEUED,
            "pending": ProposalState.PENDING,
            "canceled": ProposalState.CANCELLED,
        }

        vote_stats = raw.get("voteStats", [])
        votes_for = sum(v.get("votes", 0) for v in vote_stats if v.get("support") == "for")
        votes_against = sum(v.get("votes", 0) for v in vote_stats if v.get("support") == "against")
        votes_abstain = sum(v.get("votes", 0) for v in vote_stats if v.get("support") == "abstain")

        proposer = raw.get("proposer", {})
        ts = raw.get("createdAt", 0)

        return Proposal(
            id=str(raw.get("id", "")),
            dao_slug=dao_slug,
            title=raw.get("title", ""),
            description=raw.get("description", "")[:2000],
            proposer=proposer.get("address", "") if isinstance(proposer, dict) else str(proposer),
            state=state_map.get(raw.get("state", "").lower(), ProposalState.PENDING),
            chain=ChainType.ETHEREUM,
            created_at=datetime.fromtimestamp(ts) if isinstance(ts, (int, float)) else datetime.utcnow(),
            votes_for=votes_for,
            votes_against=votes_against,
            votes_abstain=votes_abstain,
            quorum=raw.get("quorum", 0),
            total_voting_power=votes_for + votes_against + votes_abstain,
            source="tally",
            source_url=f"https://www.tally.xyz/proposal/{raw.get('id', '')}",
        )

    def _graphql_query(self, query: str, variables: dict) -> dict[str, Any]:
        """Execute a GraphQL query against Tally."""
        try:
            response = self.client.post(
                TALLY_API,
                json={"query": query, "variables": variables},
            )
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, httpx.TimeoutException) as e:
            logger.error("Tally API error: %s", e)
            return {"data": {}, "errors": [str(e)]}

    def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            self._client.close()
            self._client = None
