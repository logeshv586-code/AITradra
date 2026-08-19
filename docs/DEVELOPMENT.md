# AITradra Development Guide

This guide helps new contributors understand the project quickly.

## Project purpose

AITradra combines market data, news, social evidence, multi-agent reasoning, prediction tracking, risk controls, paper trading and gated broker execution into a customer-friendly product.

The project should be useful even when live trading is never enabled.

## High-level structure

```text
agents/       Multi-agent research, signal, risk and orchestration logic
brokers/      Broker abstractions and Hyperliquid adapters
core/         Config, scoring, safety and shared infrastructure
gateway/      FastAPI routes, data engine, stores and customer services
memory/       Memory/RAG support
scripts/      Operational and verification scripts
tests/        Safety, customer and integrity tests
ui/           React customer application
```

## Important safety defaults

- `PAPER_TRADE_MODE=true`
- `AUTOTRADE_ENABLED=false`
- `MANUAL_LIVE_TRADING_ENABLED=false`
- Live trading requires explicit server-side authorization.
- Broker keys must be supplied outside Git.

## Common contributor workflows

### Documentation-only change

1. Edit Markdown docs.
2. Check that links and instructions are clear.
3. Open a PR using the template.

### Frontend/UI change

1. Keep the global shell/sidebar stable unless the issue explicitly asks for navigation changes.
2. Prefer customer-readable language.
3. Avoid developer-only model/provider jargon on customer pages.
4. Run the UI build before merging.

### Backend/data change

1. Preserve data provenance.
2. Treat stale/unavailable data as stale/unavailable.
3. Add tests for new adapters or edge cases.
4. Never make a fallback look like a verified live source.

### Trading/risk change

Trading changes require extra care.

Must preserve:

- Paper mode default
- Explicit real-money confirmation
- Manual and autonomous credential separation
- Position limits
- Daily-loss checks
- Stop-loss and take-profit requirements
- Risk-manager veto path
- Reduce-only exit behavior

## Useful test commands

The CI currently validates core safety paths. Local commands may vary by environment, but contributors should aim to run:

```bash
python -m compileall -q core brokers gateway agents
python -m pytest -q tests/test_trading_safety.py tests/test_customer_experience.py tests/test_live_integrity.py
```

Frontend:

```bash
cd ui
npm ci
npm run build
```

## Data-source adapter guidelines

A good adapter should return:

- price
- timestamp
- source name
- stale/fresh flag
- OHLCV history where possible
- error/unavailable state when it fails

Do not silently substitute old data without exposing its age.

## Broker adapter guidelines

A broker adapter must fail closed by default.

New entries should require:

- explicit user confirmation
- valid quantity
- fresh reference price
- stop-loss
- take-profit
- risk-gate approval
- position-limit checks

Reduce-only exits should be able to close risk even when research data is unavailable.

## Review expectations

A PR is easier to review when it includes:

- Small scope
- Clear problem statement
- Screenshots for UI changes
- Test evidence
- Safety explanation for trading/data changes
