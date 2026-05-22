"""Blockchain utility functions for multi-chain support."""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class Network(Enum):
    """Supported networks."""
    ETHEREUM = "ethereum"
    ARBITRUM = "arbitrum"
    OPTIMISM = "optimism"
    POLYGON = "polygon"
    BASE = "base"
    SOLANA = "solana"


CHAIN_IDS: dict[Network, int] = {
    Network.ETHEREUM: 1,
    Network.ARBITRUM: 42161,
    Network.OPTIMISM: 10,
    Network.POLYGON: 137,
    Network.BASE: 8453,
    Network.SOLANA: 0,
}

BLOCK_TIMES: dict[Network, float] = {
    Network.ETHEREUM: 12.0,
    Network.ARBITRUM: 0.25,
    Network.OPTIMISM: 2.0,
    Network.POLYGON: 2.0,
    Network.BASE: 2.0,
    Network.SOLANA: 0.4,
}

NATIVE_TOKENS: dict[Network, str] = {
    Network.ETHEREUM: "ETH",
    Network.ARBITRUM: "ETH",
    Network.OPTIMISM: "ETH",
    Network.POLYGON: "MATIC",
    Network.BASE: "ETH",
    Network.SOLANA: "SOL",
}

# Well-known governance contract ABIs (simplified signatures)
GOV_CONTRACT_SIGNATURES = {
    "propose": "0xda95691a",
    "castVote": "0x56781388",
    "execute": "0xfe0d94c1",
    "queue": "0xddf0b009",
    "cancel": "0xc7a876e3",
}

# Snapshot strategy types
SNAPSHOT_STRATEGIES = {
    "erc20-balance-of": "Token balance voting",
    "erc20-votes": "Governance token voting with delegation",
    "delegation": "Delegation-based voting",
    "multichain": "Multi-chain token voting",
    "masterchef": "LP-based voting",
}


@dataclass
class TokenBalance:
    """Token balance for a wallet."""
    address: str
    token: str
    balance: float
    chain: Network = Network.ETHEREUM
    decimals: int = 18
    symbol: str = ""

    @property
    def human_readable(self) -> str:
        divisor = 10 ** self.decimals
        return f"{self.balance / divisor:.4f} {self.symbol}"


@dataclass
class DelegationInfo:
    """Delegation information for a voter."""
    delegator: str
    delegate: str
    amount: float
    chain: Network = Network.ETHEREUM
    token: str = ""


def is_evm_address(address: str) -> bool:
    """Check if a string is a valid EVM address."""
    if not address.startswith("0x"):
        return False
    if len(address) != 42:
        return False
    try:
        int(address, 16)
        return True
    except ValueError:
        return False


def is_solana_address(address: str) -> bool:
    """Check if a string is a valid Solana address (base58, 32-44 chars)."""
    if len(address) < 32 or len(address) > 44:
        return False
    valid_chars = set("123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz")
    return all(c in valid_chars for c in address)


def normalize_address(address: str, network: Network = Network.ETHEREUM) -> str:
    """Normalize an address to checksum format."""
    if network == Network.SOLANA:
        return address
    return address.lower()


def compute_proposal_id(dao_slug: str, title: str, source: str) -> str:
    """Compute a deterministic proposal ID for deduplication."""
    raw = f"{dao_slug}:{title}:{source}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def estimate_blocks_from_hours(hours: float, network: Network) -> int:
    """Estimate number of blocks for a given time period."""
    block_time = BLOCK_TIMES.get(network, 12.0)
    return int(hours * 3600 / block_time)


def format_treasury_value(usd_value: float) -> str:
    """Format treasury value for display."""
    if usd_value >= 1_000_000_000:
        return f"${usd_value / 1_000_000_000:.2f}B"
    if usd_value >= 1_000_000:
        return f"${usd_value / 1_000_000:.2f}M"
    if usd_value >= 1_000:
        return f"${usd_value / 1_000:.1f}K"
    return f"${usd_value:.2f}"


def get_governance_contract(network: Network) -> dict[str, str]:
    """Get well-known governance contract addresses for a network."""
    contracts = {
        Network.ETHEREUM: {
            "compound_bravo": "0xc0Da02939E1441F497fd74F78cE7Decb17B66529",
            "aave_governor": "0xc4C79a40e7a7CE79b6F4B0E92c85B2a8b2d1e03D",
            "uniswap_governor": "0x408ED6354d4973f66138C91495F2f2FCbd8724C3",
            "ens_governor": "0x323A76393544d5ecca80cd6f6f0B0A6f0aC0C1d4",
        },
        Network.ARBITRUM: {
            "arbitrum_governor": "0xf07DeD9dC292157749B6Fd268E37DF6EA3D77B2E",
        },
        Network.OPTIMISM: {
            "optimism_governor": "0xcDF27F107725988f2261Ce2256bDfCdE8B382B10",
        },
        Network.POLYGON: {},
        Network.BASE: {},
        Network.SOLANA: {},
    }
    return contracts.get(network, {})


def chain_type_to_network(chain_type_str: str) -> Network:
    """Convert chain type string to Network enum."""
    mapping = {n.value: n for n in Network}
    return mapping.get(chain_type_str, Network.ETHEREUM)
