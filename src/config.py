"""GovernanceOS configuration management."""

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ChainConfig:
    """Configuration for a blockchain network."""
    name: str
    chain_id: int
    rpc_url: str
    explorer_url: str
    governance_contracts: list[str] = field(default_factory=list)
    snapshot_space: str = ""
    tally_org_id: str = ""


@dataclass
class AgentConfig:
    """Configuration for agent behavior."""
    max_proposals_per_scan: int = 100
    sentiment_threshold: float = 0.3
    alert_threshold: float = 0.7
    simulation_scenarios: int = 5
    report_max_length: int = 5000
    poll_interval_seconds: int = 300
    llm_model: str = "gpt-4"
    llm_temperature: float = 0.3
    max_tokens_per_request: int = 4096


@dataclass
class SocialConfig:
    """Configuration for social media monitoring."""
    twitter_bearer_token: str = ""
    reddit_client_id: str = ""
    reddit_client_secret: str = ""
    discord_bot_token: str = ""
    forum_urls: list[str] = field(default_factory=list)


@dataclass
class AlertConfig:
    """Configuration for alert dispatch."""
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    twitter_api_key: str = ""
    twitter_api_secret: str = ""
    webhook_urls: list[str] = field(default_factory=list)
    min_severity: str = "high"


@dataclass
class Config:
    """Main GovernanceOS configuration."""
    chains: list[ChainConfig] = field(default_factory=list)
    agent: AgentConfig = field(default_factory=AgentConfig)
    social: SocialConfig = field(default_factory=SocialConfig)
    alerts: AlertConfig = field(default_factory=AlertConfig)
    monitored_daos: list[str] = field(default_factory=list)
    data_dir: str = "./data"
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        chains = [
            ChainConfig(
                name="ethereum",
                chain_id=1,
                rpc_url=os.getenv("ETH_RPC_URL", "https://eth.llamarpc.com"),
                explorer_url="https://etherscan.io",
                snapshot_space=os.getenv("ETH_SNAPSHOT_SPACE", "ens.eth"),
                tally_org_id=os.getenv("ETH_TALLY_ORG", ""),
            ),
            ChainConfig(
                name="arbitrum",
                chain_id=42161,
                rpc_url=os.getenv("ARB_RPC_URL", "https://arb1.arbitrum.io/rpc"),
                explorer_url="https://arbiscan.io",
                snapshot_space=os.getenv("ARB_SNAPSHOT_SPACE", "arbitrumfoundation.eth"),
            ),
            ChainConfig(
                name="optimism",
                chain_id=10,
                rpc_url=os.getenv("OP_RPC_URL", "https://mainnet.optimism.io"),
                explorer_url="https://optimistic.etherscan.io",
                snapshot_space=os.getenv("OP_SNAPSHOT_SPACE", "opcollective.eth"),
            ),
            ChainConfig(
                name="polygon",
                chain_id=137,
                rpc_url=os.getenv("POLYGON_RPC_URL", "https://polygon-rpc.com"),
                explorer_url="https://polygonscan.com",
                snapshot_space=os.getenv("POLYGON_SNAPSHOT_SPACE", "polygon-gov.eth"),
            ),
            ChainConfig(
                name="base",
                chain_id=8453,
                rpc_url=os.getenv("BASE_RPC_URL", "https://mainnet.base.org"),
                explorer_url="https://basescan.org",
                snapshot_space=os.getenv("BASE_SNAPSHOT_SPACE", ""),
            ),
            ChainConfig(
                name="solana",
                chain_id=0,
                rpc_url=os.getenv("SOL_RPC_URL", "https://api.mainnet-beta.solana.com"),
                explorer_url="https://solscan.io",
            ),
        ]

        monitored = os.getenv(
            "MONITORED_DAOS",
            "ens,aave,uniswap,compound,gitcoin,arbitrum,optimism,lido,curve,makerdao"
        ).split(",")

        return cls(
            chains=chains,
            agent=AgentConfig(
                llm_model=os.getenv("LLM_MODEL", "gpt-4"),
                poll_interval_seconds=int(os.getenv("POLL_INTERVAL", "300")),
            ),
            social=SocialConfig(
                twitter_bearer_token=os.getenv("TWITTER_BEARER_TOKEN", ""),
                reddit_client_id=os.getenv("REDDIT_CLIENT_ID", ""),
                reddit_client_secret=os.getenv("REDDIT_CLIENT_SECRET", ""),
                discord_bot_token=os.getenv("DISCORD_BOT_TOKEN", ""),
            ),
            alerts=AlertConfig(
                telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
                telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID", ""),
                min_severity=os.getenv("ALERT_MIN_SEVERITY", "high"),
            ),
            monitored_daos=monitored,
            data_dir=os.getenv("GOVOS_DATA_DIR", "./data"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )

    def get_chain(self, name: str) -> ChainConfig | None:
        """Get chain config by name."""
        for chain in self.chains:
            if chain.name == name:
                return chain
        return None

    def get_evm_chains(self) -> list[ChainConfig]:
        """Get all EVM-compatible chains."""
        return [c for c in self.chains if c.chain_id > 0]

    def get_solana_chains(self) -> list[ChainConfig]:
        """Get Solana chains."""
        return [c for c in self.chains if c.chain_id == 0]
