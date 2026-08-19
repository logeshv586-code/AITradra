# Pull Request

## Summary

What does this PR change?

## User impact

Who benefits from this change?

- [ ] Customer / non-developer user
- [ ] Developer contributor
- [ ] Maintainer/operator
- [ ] Investor/community reader
- [ ] Trading/risk workflow

## Safety checklist

- [ ] No API keys, private keys, tokens, `.env` files, account credentials, or private financial data are committed.
- [ ] If this touches trading, paper/practice mode remains the default.
- [ ] If this touches live trading, explicit authorization and confirmation gates remain required.
- [ ] If this touches entries, stop-loss/take-profit/risk checks remain enforced.
- [ ] If this touches exits, reduce-only risk-reducing exits are not blocked by entry-only checks.
- [ ] If this touches data, stale/unavailable data is labeled honestly and never presented as live.
- [ ] If this touches predictions, it does not claim guaranteed profit or guaranteed accuracy.

## Tests / validation

Describe what you ran:

- [ ] Python compile/tests
- [ ] Frontend build
- [ ] Live smoke / manual verification
- [ ] Not applicable, docs only

## Screenshots / evidence

Add screenshots, logs, or evidence where useful.

## Notes for reviewers

Anything reviewers should inspect carefully?
