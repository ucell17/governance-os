# GovernanceOS

A multi-agent DAO governance intelligence and strategy platform.

## Architecture

6-agent pipeline:

1. **Proposal Scanner** — monitors 50+ DAOs across Ethereum, Arbitrum, Optimism, Polygon, Base, Solana
2. **Sentiment Analyzer** — NLP analysis of community discussions from forums, Discord, Twitter
3. **Voting Strategist** — game-theory-based optimal voting strategy calculation
4. **Impact Modeler** — simulates proposal outcomes, treasury impact, protocol changes
5. **Report Generator** — creates comprehensive governance briefings with risk assessment
6. **Alert Dispatcher** — real-time Telegram/X alerts for high-impact proposals

## CLI

```bash
govos scan                   # Scan all monitored DAOs for new proposals
govos analyze <dao-slug>    # Run full pipeline for a specific DAO
govos report <proposal-id>  # Generate governance report for a proposal
govos watch                 # Continuous monitoring mode
govos config show           # Show current configuration
```

## Installation

```bash
pip install -e .
```

## Token Consumption

~12M tokens/day — continuous DAO monitoring across 10 chains, deep sentiment analysis, multi-scenario simulation.

## Built With

- Python 3.10+
- Snapshot GraphQL API
- Tally.xyz API
- Multi-chain support (EVM + Solana)

## License

MIT
