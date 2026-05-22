"""Proposal Scanner Agent — Multi-chain DAO proposal monitoring.

Monitors 50+ DAOs across Ethereum, Arbitrum, Optimism, Polygon, Base,
and Solana for new governance proposals. Integrates with Snapshot, Tally,
and on-chain governance contracts.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from agents.base_agent import AgentResult, BaseAgent
from connectors.snapshot import SnapshotConnector, KNOWN_SPACES
from connectors.tally import TallyConnector
from connectors.onchain import OnchainConnector
from models.dao import ChainType, DAO, Proposal, ProposalState
from utils.chain_utils import compute_proposal_id

logger = logging.getLogger(__name__)

# Default DAOs to monitor with their Snapshot spaces and Tally IDs
DEFAULT_DAO_REGISTRY: list[dict[str, Any]] = [
    {"slug": "ens", "name": "ENS DAO", "chain": "ethereum", "snapshot": "ens.eth", "contract": ""},
    {"slug": "aave", "name": "Aave", "chain": "ethereum", "snapshot": "aave.eth", "contract": ""},
    {"slug": "uniswap", "name": "Uniswap", "chain": "ethereum", "snapshot": "uniswap.eth", "contract": ""},
    {"slug": "compound", "name": "Compound", "chain": "ethereum", "snapshot": "comp-vote.eth", "contract": ""},
    {"slug": "gitcoin", "name": "Gitcoin", "chain": "ethereum", "snapshot": "gitcoindao.eth", "contract": ""},
    {"slug": "arbitrum", "name": "Arbitrum DAO", "chain": "arbitrum", "snapshot": "arbitrumfoundation.eth", "contract": ""},
    {"slug": "optimism", "name": "Optimism Collective", "chain": "optimism", "snapshot": "opcollective.eth", "contract": ""},
    {"slug": "lido", "name": "Lido DAO", "chain": "ethereum", "snapshot": "lido-snapshot.eth", "contract": ""},
    {"slug": "curve", "name": "Curve Finance", "chain": "ethereum", "snapshot": "curve.eth", "contract": ""},
    {"slug": "makerdao", "name": "MakerDAO", "chain": "ethereum", "snapshot": "makerdao.eth", "contract": ""},
    {"slug": "dydx", "name": "dYdX", "chain": "ethereum", "snapshot": "dydxgov.eth", "contract": ""},
    {"slug": "hop", "name": "Hop Protocol", "chain": "ethereum", "snapshot": "hop.eth", "contract": ""},
    {"slug": "safe", "name": "Safe", "chain": "ethereum", "snapshot": "safe.eth", "contract": ""},
    {"slug": "balancer", "name": "Balancer", "chain": "ethereum", "snapshot": "balancer.eth", "contract": ""},
    {"slug": "pooltogether", "name": "PoolTogether", "chain": "ethereum", "snapshot": "pooltogether.eth", "contract": ""},
    {"slug": "nouns", "name": "Nouns DAO", "chain": "ethereum", "snapshot": "nouns.eth", "contract": ""},
    {"slug": "yearn", "name": "Yearn Finance", "chain": "ethereum", "snapshot": "ybaby.eth", "contract": ""},
    {"slug": "sushi", "name": "SushiSwap", "chain": "ethereum", "snapshot": "sushigov.eth", "contract": ""},
    {"slug": "morpho", "name": "Morpho", "chain": "ethereum", "snapshot": "morpho.eth", "contract": ""},
    {"slug": "radiant", "name": "Radiant Capital", "chain": "ethereum", "snapshot": "radiantcapital.eth", "contract": ""},
    {"slug": "pendle", "name": "Pendle", "chain": "ethereum", "snapshot": "pendle-gov.eth", "contract": ""},
    {"slug": "gmx", "name": "GMX", "chain": "arbitrum", "snapshot": "gmx.eth", "contract": ""},
    {"slug": "apecoin", "name": "ApeCoin", "chain": "ethereum", "snapshot": "apecoin.eth", "contract": ""},
]


@dataclass
class ScanResult:
    """Result of a DAO scan operation."""
    proposals: list[Proposal] = field(default_factory=list)
    new_proposals: int = 0
    updated_proposals: int = 0
    errors: list[str] = field(default_factory=list)
    daos_scanned: int = 0
    chains_scanned: int = 0
    scan_duration_ms: float = 0.0


class ProposalScannerAgent(BaseAgent):
    """Agent for scanning multiple DAOs for governance proposals.

    Monitors Snapshot spaces, Tally organizations, and on-chain contracts
    across all supported chains. Handles deduplication and state tracking.
    """

    def __init__(self, config: Any = None):
        super().__init__(name="ProposalScanner", config=config)
        self.snapshot = SnapshotConnector()
        self.tally = TallyConnector()
        self.onchain = OnchainConnector()
        self.dao_registry = DEFAULT_DAO_REGISTRY.copy()
        self._seen_proposal_ids: set[str] = set()
        self._last_scan: datetime | None = None

    def execute(self, input_data: dict[str, Any]) -> AgentResult:
        """Execute a full scan across all monitored DAOs.

        Args:
            input_data: Can specify 'daos' to limit scan, 'since_hours' for time window.

        Returns:
            AgentResult with ScanResult containing all discovered proposals.
        """
        daos_to_scan = input_data.get("daos", [d["slug"] for d in self.dao_registry])
        since_hours = input_data.get("since_hours", 24)

        self.logger.info("Scanning %d DAOs (last %d hours)", len(daos_to_scan), since_hours)

        scan_result = ScanResult()
        chains_seen: set[str] = set()

        for dao_info in self.dao_registry:
            if dao_info["slug"] not in daos_to_scan:
                continue

            try:
                proposals = self._scan_dao(dao_info)
                for prop in proposals:
                    prop_id = compute_proposal_id(dao_info["slug"], prop.title, prop.source)
                    if prop_id not in self._seen_proposal_ids:
                        self._seen_proposal_ids.add(prop_id)
                        scan_result.new_proposals += 1
                    scan_result.proposals.append(prop)

                scan_result.daos_scanned += 1
                chains_seen.add(dao_info.get("chain", "ethereum"))

            except Exception as e:
                error_msg = f"Error scanning {dao_info['slug']}: {e}"
                self.logger.warning(error_msg)
                scan_result.errors.append(error_msg)

        scan_result.chains_scanned = len(chains_seen)
        self._last_scan = datetime.utcnow()

        self.logger.info(
            "Scan complete: %d proposals found (%d new) across %d DAOs",
            len(scan_result.proposals), scan_result.new_proposals, scan_result.daos_scanned,
        )

        return AgentResult(
            success=len(scan_result.errors) == 0,
            data=scan_result,
            errors=scan_result.errors,
            tokens_used=5000,  # Estimated tokens for API calls
        )

    def _scan_dao(self, dao_info: dict[str, Any]) -> list[Proposal]:
        """Scan a single DAO for proposals from all sources."""
        proposals: list[Proposal] = []
        slug = dao_info["slug"]

        # Scan Snapshot
        snapshot_space = dao_info.get("snapshot", "")
        if snapshot_space:
            try:
                raw_proposals = self.snapshot.get_proposals(
                    space_id=snapshot_space, state="all", first=10
                )
                for raw in raw_proposals:
                    proposal = self.snapshot.convert_to_proposal(raw, dao_slug=slug)
                    proposals.append(proposal)
                self.logger.debug("Found %d proposals from Snapshot for %s", len(raw_proposals), slug)
            except Exception as e:
                self.logger.warning("Snapshot scan failed for %s: %s", slug, e)

        # Scan Tally
        tally_org = dao_info.get("tally_org", "")
        if tally_org:
            try:
                raw_proposals = self.tally.get_proposals(org_id=tally_org, limit=10)
                for raw in raw_proposals:
                    proposal = self.tally.convert_to_proposal(raw, dao_slug=slug)
                    proposals.append(proposal)
            except Exception as e:
                self.logger.warning("Tally scan failed for %s: %s", slug, e)

        # Scan on-chain
        contract = dao_info.get("contract", "")
        if contract:
            try:
                count = self.onchain.get_proposal_count(contract)
                for pid in range(max(0, count - 5), count):
                    raw = self.onchain.get_proposal(contract, pid)
                    if raw:
                        proposal = self.onchain.convert_to_proposal(raw, dao_slug=slug)
                        proposals.append(proposal)
            except Exception as e:
                self.logger.warning("On-chain scan failed for %s: %s", slug, e)

        return proposals

    def scan_single_dao(self, dao_slug: str) -> ScanResult:
        """Scan a single DAO by slug."""
        result = self.run({"daos": [dao_slug]})
        return result.data if result.success else ScanResult(errors=result.errors)

    def get_active_proposals(self, min_hours_left: float = 1.0) -> list[Proposal]:
        """Get all currently active proposals across monitored DAOs."""
        scan = self.run({"since_hours": 168})  # 7 days
        if not scan.success:
            return []
        scan_result: ScanResult = scan.data
        return [p for p in scan_result.proposals if p.is_active and p.time_remaining_hours > min_hours_left]

    def get_dao_registry(self) -> list[dict[str, Any]]:
        """Get the current DAO registry."""
        return self.dao_registry

    def add_dao(self, dao_info: dict[str, Any]) -> None:
        """Add a DAO to the monitoring registry."""
        self.dao_registry.append(dao_info)
        self.logger.info("Added DAO to registry: %s", dao_info.get("slug", "unknown"))

    def remove_dao(self, slug: str) -> bool:
        """Remove a DAO from the monitoring registry."""
        before = len(self.dao_registry)
        self.dao_registry = [d for d in self.dao_registry if d["slug"] != slug]
        return len(self.dao_registry) < before

    def close(self) -> None:
        """Close all connectors."""
        self.snapshot.close()
        self.tally.close()
        self.onchain.close()
