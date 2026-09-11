# Buy, sell and wait guidance

AITradra cannot offer risk-free trading, guaranteed profit percentages or zero-loss execution. This update makes conditional trade returns and the reasons for waiting visible in the customer stock detail screen.

## What the customer sees

- BUY or SELL only when a consistent signal has complete protective levels, a positive risk-approved size, adequate confidence, a fresh quote near the reviewed entry, and acceptable reward/risk after estimated costs.
- WAIT when any of those requirements is missing. A basic research-only snapshot therefore normally shows WAIT until a complete risk review is available. The stock brief no longer treats price freshness alone as sufficient to recommend an entry.
- Entry reference, target, stop, conditional net target return, estimated stop loss, and net reward/risk.
- The configured fee and adverse slippage assumptions for each side of the trade.
- SELL means a bearish/short setup. Closing an existing holding is a separate reduce-only action and remains possible without research or entry checks.

The card is for paper evaluation. It never authorizes an order, and model confidence is not a measured probability of profit. Directional hit rate also does not establish net profitability.

For a paper sizing review, enter a hypothetical account value next to **Run full AI research**. This explicitly assumes an empty cash-only paper account in the asset's quote currency. Leaving the field empty performs research without assuming your balance; incomplete risk reviews show WAIT. Paper-scenario approvals are rejected if submitted to funded qualification.

## Calculation and sizing

For each unit, entry and exit prices include adverse slippage. Fees are charged on both adjusted fills. Net target and stop returns are divided by the original entry reference price, so displayed percentages are unlevered returns on position notional, not returns on account equity or leveraged margin.

Default assumptions:

| Setting | Default | Meaning |
|---|---:|---|
| `TRADE_FEE_BPS` | 6 | Estimated fee per side |
| `TRADE_SLIPPAGE_BPS` | 10 | Estimated adverse slippage per side |
| `MIN_NET_REWARD_RISK` | 1.5 | Minimum net target profit divided by estimated stop loss |
| `MAX_TRADE_RISK_PCT` | 0.005 | Planned loss at the stop as a fraction of account equity |

These are configurable screening assumptions, not a claim about any venue's current fees or achievable fills. Funding, borrow charges, taxes, liquidity limitations and liquidation costs are excluded. Set venue-appropriate costs and validate with paper evidence before funded use. Stops can fill beyond the planned price or fail; the risk budget is not a maximum-loss guarantee.

Risk Manager caps position notional by the stop-loss budget after costs, in addition to existing position and cash caps. Manual entry checks now reject missing/invalid equity or available cash, excessive planned stop loss, insufficient reserves, disallowed add-ons and inadequate net reward/risk. Existing live authorization and broker controls still apply.

## Correctness fixes

- Reject non-finite financial inputs and confidence outside 0–100.
- Parse exact BUY/SELL labels, rejecting contradictory fields or arbitrary text such as “DO NOT BUY”.
- Evaluate emergency exits before entry-only position-count and daily-loss breakers.
- Recheck cost economics at the qualification boundary, even if the optional protection setting is disabled.
- Pass the latest reaggregated signal to Risk Manager after Quantic validation.
- Construct the autonomous order side from the qualified signal, rather than the earlier agent direction.

## Verification

Run `tests/test_trade_plan.py` and `tests/test_trade_plan_routes.py` with the existing trading-safety, precision, customer, price-session and research-boundary suites. Route tests execute production endpoint bodies with fake balances, research and broker services; they never submit funded trades. Safety CI also runs these suites and builds the frontend.

Passing tests demonstrates these software controls, not live profitability. This change does not establish a production readiness or profitability certification for the entire application. Venue execution, market gaps, full data-provider freshness/cross-check integration, portfolio concurrency and measured forward strategy performance still require operational validation.
