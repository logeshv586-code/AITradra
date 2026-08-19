# AITradra v0.1.0 Release Draft

Use this as the first public release description after the repository metadata and demo video are ready.

## Title

AITradra v0.1.0 — Public Alpha

## Summary

AITradra is an open-source, customer-first multi-agent market intelligence platform for explainable stock/crypto research, prediction tracking, risk analysis, paper trading and safety-gated execution workflows.

This public alpha focuses on **research, transparency and safety**. It does not guarantee returns or signal accuracy.

## Highlights

- Customer-friendly market intelligence UI
- Multi-agent research architecture
- Technical, macro, sentiment, risk and catalyst-style analysis
- Market data and OHLCV collection
- RSS/news evidence collection
- Social-provider provenance handling
- Prediction direction and confidence summaries
- Risk analysis and risk-manager gating
- Practice trading with fees and slippage
- Customer data/API connection support
- Hyperliquid manual trading path behind explicit gates
- Autonomous trading disabled by default
- Safety CI and live-system smoke verification

## Safety model

- Practice mode is default.
- Real-money trading is fail-closed.
- Manual live trading and autonomous trading use separate authorization paths.
- New real entries require fresh price data, explicit confirmation, stop-loss, take-profit and risk checks.
- Missing or stale data is labeled honestly.
- HOLD/BLOCK signals must not become autonomous entries.

## Who should try this release

- AI/ML developers interested in financial agents
- Fintech builders
- Quant/trading-tool developers
- Students learning algorithmic trading systems
- Market researchers who want explainable AI workflows
- Contributors interested in data adapters, broker adapters, evaluation and UI polish

## Not recommended for

- Users looking for guaranteed profits
- Users who want to enable autonomous live trading without understanding the code
- Users who cannot review financial and execution risk

## Next roadmap

- One-command local setup
- More data adapters
- More broker adapters
- Prediction evaluation dashboard
- Playwright E2E tests
- Better India/NSE coverage
- Hosted demo path

## Call to action

Star the repo, try the public alpha, open issues, suggest adapters, and contribute to the roadmap.

GitHub: https://github.com/logeshv586-code/AITradra
