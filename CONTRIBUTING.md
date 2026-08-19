# Contributing to AITradra

Thank you for helping improve AITradra. This project is an open-source, customer-first multi-agent market intelligence and risk-gated trading platform.

AITradra is not a guaranteed-profit trading bot. Contributions should make research, data quality, risk management, explainability, testing, and customer usability better.

## Good first contribution paths

Start with one of these areas:

1. Documentation improvements
2. UI copy and customer explanations
3. Data-source adapters
4. Paper-trading realism
5. Risk and safety tests
6. Prediction evaluation dashboards
7. Broker integrations kept fail-closed by default

Look for issues marked `good first issue` or `help wanted`.

## Local setup

```bash
git clone https://github.com/logeshv586-code/AITradra.git
cd AITradra
```

Backend and frontend setup may vary by environment. Check the README and `docs/DEVELOPMENT.md` before opening a PR.

## Safety principles

All trading-related contributions must follow these rules:

- Practice/paper mode is the default.
- Real-money execution must remain fail-closed.
- Broker keys must never be committed.
- New live entries must require explicit confirmation, fresh price data, stop-loss, take-profit, risk gates, and position limits.
- Reduce-only exits should not be blocked by entry-only checks.
- Missing data must be shown as unavailable or stale, never fabricated as live/neutral.
- Do not claim guaranteed profits, accuracy, or investment returns.

## Pull request checklist

Before submitting a PR:

- [ ] The change has a clear user/customer benefit.
- [ ] No API keys, private keys, secrets, tokens, or credentials are committed.
- [ ] Trading changes keep paper mode as the default.
- [ ] Real-money paths remain explicitly gated.
- [ ] Data provenance is preserved.
- [ ] New behavior has tests when practical.
- [ ] Documentation is updated if the user flow changes.
- [ ] The production UI build still passes.

## Coding style

- Prefer simple, readable code over clever abstractions.
- Make errors customer-readable where they reach the UI.
- Keep internal/developer terminology out of customer screens unless it helps trust.
- Keep risk logic deterministic and auditable.
- Keep LLM/model outputs advisory; do not let model text bypass risk gates.

## Issue quality

A good issue should include:

- What problem the user faces
- Where in the app it appears
- Expected behavior
- Current behavior
- Screenshots or logs when available
- Safety impact if the issue touches trading, data, or predictions

## Responsible contribution note

AITradra is financial software. Even research-only code can influence decisions. Please be careful, transparent, and conservative when proposing features that affect predictions, risk, or execution.
