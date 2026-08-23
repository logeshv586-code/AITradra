# AITradra Research Architecture Benchmark

This document records the architectural review behind **Research Council V2**.
It is a design comparison, not a claim that AITradra reproduces or outperforms
any referenced project.

## Projects reviewed

| Project | Pattern studied | AITradra adaptation |
|---|---|---|
| TauricResearch/TradingAgents | Fundamental/news/sentiment/technical analysts, bull-vs-bear researchers, Research Manager, trader, aggressive/neutral/conservative risk debate, Portfolio Manager, persistent lessons, checkpointing and structured outputs | Keep AITradra's existing DebateEngine/ReflectionMemory, but put them behind a provenance-weighted Research Council that can fail closed before rhetoric can dominate weak evidence |
| microsoft/qlib | Point-in-time quantitative research, data/model/backtest/portfolio/execution separation, benchmark-aware analysis | Add `as_of` research replay, benchmark alpha context and explicit separation of research evidence from execution permission |
| freqtrade/freqtrade | Dry-run/backtest separation, protections, exported evidence and look-ahead analysis | Add regression tests that prove future news/insights cannot leak into historical research and keep replay tooling broker-free |
| nautechsystems/nautilus_trader | Data integrity, fail-fast invariants, Data -> Risk -> Execution engine boundaries | Reject invalid/future research timestamps, expose uncertainty/coverage, and retain AITradra's independent Risk Manager and execution gates |
| AI4Finance-Foundation/FinGPT | Finance-specialized NLP and sentiment research | Treat sentiment as one evidence category rather than allowing NLP sentiment alone to determine a trade |

## Why not simply copy TradingAgents?

AITradra already contains a TradingAgents-inspired adversarial debate and
post-outcome reflection memory. The missing problem was **evidence discipline**.
A debate can sound convincing while still being based on duplicated headlines,
stale insights, incomplete specialist coverage or information that was not
available at the historical decision timestamp.

Research Council V2 therefore makes the evidence contract primary and the LLM
debate secondary.

```text
POINT-IN-TIME DATA
      |
      v
Typed Evidence Objects
(timestamp + source + URL + confidence + relevance)
      |
      v
Deduplicate -> Freshness -> Provenance -> Coverage
      |
      +-----------------------------+
      |                             |
      v                             v
Weighted Bull Evidence         Weighted Bear Evidence
      |                             |
      +-------------+---------------+
                    v
        Contradiction / Quality Metrics
                    |
                    v
        Deterministic Research Floor
                    |
       insufficient? ---- yes ----> HOLD
                    |
                    no
                    v
          Bounded Bull/Bear Debate
                    |
            conflict? -> HOLD
                    |
                    v
  BUY / OVERWEIGHT / HOLD / UNDERWEIGHT / SELL
                    |
                    v
     Advisory Exposure Ceiling Only
                    |
                    X
          NO EXECUTION AUTHORITY

Separate execution path:
Signal Aggregator -> Risk Manager -> Strategy Validation
-> Empirical Precision Gate -> Explicit Broker Authorization
```

## Research correctness invariants

1. **No future evidence.** Historical `as_of` research may consume only data
   observed at or before that timestamp.
2. **No duplicate voting.** Repeated URLs/content cannot create multiple votes.
3. **Source quality matters.** Evidence with traceable provenance receives more
   weight than unverifiable text.
4. **Freshness matters.** Old evidence decays rather than retaining full weight.
5. **Coverage matters.** A large number of technical signals cannot masquerade
   as broad multi-factor agreement.
6. **Contradiction matters.** Strong bull and bear evidence lowers confidence.
7. **Benchmarks matter.** Absolute price movement is not automatically alpha.
8. **The LLM cannot rescue bad evidence.** An insufficient deterministic
   research floor remains HOLD even if the debate model argues aggressively.
9. **Research cannot authorize money movement.** Research Council always emits
   `execution_authority=false` and `live_gate_eligible=false`.
10. **Outcome claims remain empirical.** A research rating is not evidence of
    future profitability and the configured precision target is not a promise.

## What should be added next

The next research-quality milestones should be measured rather than rhetorical:

- forward research scorecards by horizon and market regime;
- calibration curves comparing confidence with realized directional outcomes;
- benchmark-relative hit rate and alpha distribution;
- walk-forward strategy validation with transaction-cost assumptions;
- source/agent ablation tests to detect evidence sources that add noise;
- regime-aware specialist weights learned only from out-of-sample outcomes;
- a paper-trade ledger that links each executed practice trade back to the exact
  immutable research decision and evidence snapshot.

These should remain separate from autonomous live permission until enough
fresh, audited evidence exists.

## License note

The implementation in AITradra is original integration code based on general
architectural ideas. TradingAgents is Apache-2.0 licensed; each other referenced
repository retains its own license and attribution requirements. Do not copy
source code into AITradra without reviewing the upstream license and preserving
required notices.
