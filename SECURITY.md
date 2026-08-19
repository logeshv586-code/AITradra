# Security Policy

AITradra handles market data, API credentials, broker keys and trading workflows. Security issues should be treated seriously.

## Supported versions

The `main` branch is the actively supported development branch.

## Report a vulnerability

Do not open a public issue for vulnerabilities involving:

- API keys or private keys
- Broker credential exposure
- Authentication/session bypass
- Remote code execution
- Data exfiltration
- Real-money trading bypass
- Unsafe live-trading gate behavior

Use GitHub's private vulnerability reporting if enabled. If it is not enabled, contact the repository owner privately before publishing details.

## Secret handling rules

- Never commit `.env` files with real credentials.
- Never commit broker private keys.
- Never paste API keys into issues, discussions, screenshots, logs or PRs.
- Use environment variables or the encrypted local connection store.
- Rotate exposed credentials immediately.

## Trading safety issues

A security-sensitive trading issue includes any change that could:

- Turn on live trading by default
- Bypass paper mode
- Submit orders without explicit user confirmation
- Allow autonomous trading to use manual broker credentials
- Open a position without stop-loss or take-profit
- Treat stale/unavailable data as live evidence
- Allow a HOLD/BLOCK signal to become an entry order
- Block reduce-only exits because of entry-only checks

## Disclosure expectation

Please give maintainers reasonable time to investigate and patch before public disclosure. AITradra prioritizes fail-closed behavior: if in doubt, disable real-money pathways until the issue is understood.
