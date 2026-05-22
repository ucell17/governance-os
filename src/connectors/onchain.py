"""On-chain governance contract connector."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from models.dao import ChainType, Proposal, ProposalState, Vote, VoteChoice

logger = logging.getLogger(__name__)

# Standard Governor Bravo event signatures
EVENT_PROPOSAL_CREATED = "ProposalCreated(uint256,address,address[],uint256[],string[],bytes[],uint256,uint256,string)"
EVENT_VOTE_CAST = "VoteCast(address,uint256,uint8,uint256,string)"
EVENT_PROPOSAL_EXECUTED = "ProposalExecuted(uint256)"
EVENT_PROPOSAL_CANCELED = "ProposalCanceled(uint256)"

# ABI fragments for Governor contracts
GOVERNOR_ABI = [
    {
        "name": "proposalCount",
        "type": "function",
        "stateMutability": "view",
        "inputs": [],
        "outputs": [{"type": "uint256"}],
    },
    {
        "name": "proposals",
        "type": "function",
        "stateMutability": "view",
        "inputs": [{"name": "proposalId", "type": "uint256"}],
        "outputs": [
            {"name": "id", "type": "uint256"},
            {"name": "proposer", "type": "address"},
            {"name": "eta", "type": "uint256"},
            {"name": "startBlock", "type": "uint256"},
            {"name": "endBlock", "type": "uint256"},
            {"name": "forVotes", "type": "uint256"},
            {"name": "againstVotes", "type": "uint256"},
            {"name": "abstainVotes", "type": "uint256"},
            {"name": "canceled", "type": "bool"},
            {"name": "executed", "type": "bool"},
        ],
    },
    {
        "name": "state",
        "type": "function",
        "stateMutability": "view",
        "inputs": [{"name": "proposalId", "type": "uint256"}],
        "outputs": [{"type": "uint8"}],
    },
    {
        "name": "getReceipt",
        "type": "function",
        "stateMutability": "view",
        "inputs": [
            {"name": "proposalId", "type": "uint256"},
            {"name": "voter", "type": "address"},
        ],
        "outputs": [
            {"name": "hasVoted", "type": "bool"},
            {"name": "support", "type": "uint8"},
            {"name": "votes", "type": "uint256"},
        ],
    },
]

# On-chain governance state mapping
ONCHAIN_STATE_MAP = {
    0: ProposalState.PENDING,
    1: ProposalState.ACTIVE,
    2: ProposalState.CANCELLED,
    3: ProposalState.PASSED,  # Defeated in some implementations
    4: ProposalState.PASSED,  # Succeeded
    5: ProposalState.QUEUED,
    6: ProposalState.EXPIRED,
    7: ProposalState.EXECUTED,
}


class OnchainConnector:
    """Connector for on-chain governance contracts.

    Reads governance proposals and votes directly from smart contracts.
    Supports Governor Bravo, OpenZeppelin Governor, and similar patterns.
    """

    def __init__(self, rpc_url: str = "", chain: ChainType = ChainType.ETHEREUM):
        self.rpc_url = rpc_url
        self.chain = chain
        self._web3 = None

    def get_proposal(self, contract_address: str, proposal_id: int) -> dict[str, Any]:
        """Fetch on-chain proposal data from governance contract.

        Args:
            contract_address: Address of the Governor contract.
            proposal_id: On-chain proposal ID.

        Returns:
            Dictionary with proposal data from the contract.
        """
        try:
            result = self._eth_call(
                contract_address,
                "proposals(uint256)",
                [proposal_id],
            )
            if not result:
                return {}

            return {
                "id": proposal_id,
                "proposer": result[1] if len(result) > 1 else "",
                "start_block": result[3] if len(result) > 3 else 0,
                "end_block": result[4] if len(result) > 4 else 0,
                "for_votes": result[5] if len(result) > 5 else 0,
                "against_votes": result[6] if len(result) > 6 else 0,
                "abstain_votes": result[7] if len(result) > 7 else 0,
                "canceled": result[8] if len(result) > 8 else False,
                "executed": result[9] if len(result) > 9 else False,
            }
        except Exception as e:
            logger.error("Failed to fetch on-chain proposal %d: %s", proposal_id, e)
            return {}

    def get_proposal_state(self, contract_address: str, proposal_id: int) -> int:
        """Get the current state of an on-chain proposal."""
        try:
            result = self._eth_call(
                contract_address,
                "state(uint256)",
                [proposal_id],
            )
            return result[0] if result else -1
        except Exception as e:
            logger.error("Failed to get proposal state: %s", e)
            return -1

    def get_vote_receipt(
        self, contract_address: str, proposal_id: int, voter: str
    ) -> dict[str, Any]:
        """Get vote receipt for a specific voter on a proposal."""
        try:
            result = self._eth_call(
                contract_address,
                "getReceipt(uint256,address)",
                [proposal_id, voter],
            )
            if not result:
                return {}
            return {
                "has_voted": result[0],
                "support": result[1],
                "votes": result[2],
            }
        except Exception as e:
            logger.error("Failed to get vote receipt: %s", e)
            return {}

    def get_proposal_count(self, contract_address: str) -> int:
        """Get total number of proposals from governance contract."""
        try:
            result = self._eth_call(contract_address, "proposalCount()", [])
            return result[0] if result else 0
        except Exception as e:
            logger.error("Failed to get proposal count: %s", e)
            return 0

    def convert_to_proposal(
        self, raw: dict[str, Any], dao_slug: str = "", title: str = ""
    ) -> Proposal:
        """Convert on-chain data to Proposal model."""
        state_int = raw.get("state", 1)
        state = ONCHAIN_STATE_MAP.get(state_int, ProposalState.ACTIVE)

        return Proposal(
            id=f"onchain-{raw.get('id', 0)}",
            dao_slug=dao_slug,
            title=title or f"Proposal #{raw.get('id', 0)}",
            description="On-chain governance proposal",
            proposer=raw.get("proposer", ""),
            state=state,
            chain=self.chain,
            created_at=datetime.utcnow(),
            votes_for=float(raw.get("for_votes", 0)) / 1e18,
            votes_against=float(raw.get("against_votes", 0)) / 1e18,
            votes_abstain=float(raw.get("abstain_votes", 0)) / 1e18,
            source="onchain",
        )

    def _eth_call(
        self, contract: str, function_sig: str, params: list
    ) -> list[Any]:
        """Execute an eth_call to a contract.

        In production, this would use web3.py. For now, returns mock data.
        """
        logger.debug(
            "eth_call: contract=%s function=%s chain=%s",
            contract, function_sig, self.chain.value,
        )
        # Mock response for development
        if "proposalCount" in function_sig:
            return [150]
        if "proposals" in function_sig:
            return [
                params[0] if params else 1,
                "0x0000000000000000000000000000000000000001",
                0, 0, 0, 1000000 * 10**18, 500000 * 10**18, 100000 * 10**18,
                False, False,
            ]
        if "state" in function_sig:
            return [1]
        return []

    def close(self) -> None:
        """Close connections."""
        self._web3 = None
