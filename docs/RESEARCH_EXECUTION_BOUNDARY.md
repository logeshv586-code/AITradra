# AITradra Research → Qualification → Execution Boundary

## Purpose

AITradra deliberately separates **research quality** from **trading permission**.
A strong research result is evidence for further analysis; it is never an order
authorization.

This separation prevents a persuasive LLM debate, a high research confidence,
a backtest chart, or a robustness score from accidentally becoming permission to
place a funded order.

## Clean architecture

```text
Market / news / specialist evidence
              │
              ▼
      Research Council V2
  point-in-time + provenance
  dedupe + contradiction + coverage
              │
              ▼
   Research Scorecard / Robustness Lab
  forward outcomes + walk-forward + regime
         + source/category ablation
              │
              │  advisory information only
              ▼
      Signal Aggregator
              │
              ▼
       Risk Manager
 deterministic capital/risk veto
              │
              ▼
    Trade Qualification Firewall
  signal + risk + protective orders
  + execution authorization
  + strategy validation (live)
  + empirical precision evidence (live)
              │
              ▼
        Execution Adapter
              │
              ▼
             Broker
```

## Domain ownership

### 1. Research domain

Research owns:

- evidence collection and point-in-time replay;
- provenance, freshness and source diversity;
- bull/bear contradiction analysis;
- specialist coverage;
- benchmark-relative context;
- forward research scorecards;
- walk-forward robustness;
- regime analysis;
- source/category ablation;
- calibration and statistical confidence reporting.

Research does **not** own:

- broker credentials;
- order construction;
- order submission;
- live mode authorization;
- strategy deployment approval;
- autonomous live precision eligibility.

Every Research Council result remains advisory with:

- `execution_authority = false`
- `live_gate_eligible = false`

### 2. Qualification domain

`core/trade_qualification.py` is the single pre-order permission boundary.

It accepts only:

- a concrete Signal Aggregator result;
- a deterministic Risk Manager result;
- execution-mode authorization state;
- protective-order state;
- strategy validation state for live execution;
- empirical precision validation state for live execution.

It intentionally accepts **no ResearchDecision or Research Council object**.

Qualification returns one of:

- `EXECUTE_PAPER`
- `EXECUTE_LIVE`
- `BLOCK`

A research confidence of 99% cannot override a weak current signal, a Risk
Manager veto, missing protective orders, stale strategy validation, inadequate
precision evidence, paper mode, or missing live authorization.

### 3. Execution domain

Execution adapters may construct and submit orders only after a successful
`TradeQualification` result.

Broker integrations must never be imported by research modules.

## Paper vs live

Paper execution can proceed after current signal/risk/protection checks without
pretending that live authorization is present. This allows the system to gather
forward evidence safely.

Live execution requires all paper-safe checks **plus**:

1. server-side live authorization;
2. current live-signal confidence threshold;
3. approved and fresh strategy validation;
4. empirical precision evidence meeting configured sample/precision/statistical
   lower-bound requirements;
5. broker credential/acknowledgement requirements enforced by execution safety.

## Statistical independence

Shared statistical mathematics belongs in neutral modules such as
`core/statistical_bounds.py`.

Research must not import the live precision-gate module merely to reuse a formula.
Both research diagnostics and live gates may depend on neutral statistics without
depending on one another.

## CI architecture rules

`tests/test_research_execution_boundary.py` fails when:

- research modules import brokers or execution/qualification modules;
- the qualification API starts accepting research objects;
- ResearchDecision loses its advisory-only defaults;
- the autonomous service bypasses the centralized qualification firewall;
- paper and live permission become conflated;
- a research-like confidence field is able to bypass the actual live signal gate.

## Claims

Research robustness, directional hit rate, Brier score, alpha, Sharpe, backtests,
or configured precision thresholds do not guarantee future profitability or
future accuracy.

The autonomous precision target is an **eligibility threshold**, not a promise.
A funded live trade should only be claimed when broker/execution evidence proves
that an order was actually submitted or filled.
