# Broker Integration Reference

## Broker Router Architecture

```
BrokerRouter.execute(order, asset_class)
    ↓
asset_class == "crypto"?
    YES → HyperliquidBroker (perps) OR CCXTBroker (spot)
    NO  → PaperBroker (all equities, default)
```

## Order Object

```python
from brokers.broker_router import Order, OrderSide, OrderType

order = Order(
    ticker="BTC",            # Symbol (no -USD for Hyperliquid)
    side=OrderSide.BUY,      # OrderSide.BUY or OrderSide.SELL
    qty=0.01,                # Quantity
    order_type=OrderType.MARKET,  # MARKET or LIMIT
    limit_price=None,        # Required if LIMIT
    stop_loss=42000.0,       # Optional
    take_profit=55000.0,     # Optional
)
```

## PaperBroker (Default — No Real Money)

```python
from brokers.broker_router import PaperBroker

broker = PaperBroker()
# Starts with $100,000 virtual cash
# All orders filled instantly at limit_price or 100.0 if market

result = await broker.place_order(order)
# Returns: {"order_id": "PAPER-1", "status": "FILLED", "fill_price": 100.0, "broker": "paper"}

positions = await broker.get_positions()
# Returns: [{"ticker": "BTC", "qty": 0.01}]

balance = await broker.get_balance()
# Returns: {"cash": 99900.0, "positions": 1, "trade_count": 1}
```

## HyperliquidBroker (Live Crypto Perps)

```python
from brokers.hyperliquid_broker import HyperliquidBroker

# REQUIRES: HYPERLIQUID_PRIVATE_KEY in environment
broker = HyperliquidBroker(
    private_key=settings.HYPERLIQUID_PRIVATE_KEY,
    vault_address=settings.HYPERLIQUID_VAULT_ADDRESS  # Optional
)

# Fetch balance (USDC)
balance = await broker.get_balance()
# {"total": 10000.0, "withdrawable": 8500.0, "cash": 8500.0}

# Fetch positions
positions = await broker.get_positions()
# [{"ticker": "BTC", "qty": 0.01, "entry_price": 45000.0, "unrealized_pnl": 150.0}]

# Place market order
result = await broker.place_order(order)
# {"status": "FILLED", "order_id": "12345", "broker": "hyperliquid"}

# Fetch candles for TA
candles = await broker.get_candles("BTC", interval="5m", limit=100)
# [{"timestamp": ms, "open": ..., "high": ..., "low": ..., "close": ..., "volume": ...}]
```

**Important Hyperliquid Notes:**
- Tickers are without `-USD` suffix: `"BTC"` not `"BTC-USD"`
- SDK methods are synchronous — wrapped with `asyncio.to_thread()`
- `PAPER_TRADE_MODE=True` always returns fake fill without SDK call
- Vault address routes orders through a Hyperliquid vault (institutional)

## CCXTBroker (Multi-Exchange Crypto Spot)

```python
from brokers.broker_router import CCXTBroker

broker = CCXTBroker(
    exchange_name="binance",  # binance | bybit | okx
    api_key=settings.CCXT_API_KEY,
    secret=settings.CCXT_SECRET,
    paper=True  # Use testnet/sandbox
)

# Symbol format: "BTC/USDT" (CCXT format)
order = Order(ticker="BTC/USDT", side=OrderSide.BUY, qty=0.01)
result = await broker.place_order(order)
```

## BrokerRouter (Unified Entry Point)

```python
from brokers.broker_router import BrokerRouter, Order, OrderSide

router = BrokerRouter(config={
    "CCXT_EXCHANGE": "binance",
    "CCXT_API_KEY": "...",
    "CCXT_SECRET": "...",
    "PAPER_TRADING": True,
    "HYPERLIQUID_PRIVATE_KEY": "...",
})

# Execute order (routes automatically)
result = await router.execute(order, asset_class="crypto")  # → HyperliquidBroker
result = await router.execute(order, asset_class="equity")  # → PaperBroker

# Get all positions across brokers
all_positions = await router.get_all_positions()
# {"paper": [...], "ccxt": [...]}
```

---

## HyperliquidTradingAgent Integration

```python
from agents.hyperliquid_agent import HyperliquidTradingAgent
from agents.base_agent import AgentContext

agent = HyperliquidTradingAgent()

ctx = AgentContext(
    task="Analyze BTC for trading",
    ticker="BTC",
    observations={
        "indicators": {
            "RSI_14": 35.2,
            "MACD_12_26_9": 125.5,
            "MACDh_12_26_9": 45.2,
        },
        "portfolio": {
            "cash": 5000.0,
            "total_value": 10000.0,
        }
    }
)

result = await agent.run(ctx)
# result.result = {
#   "decision": "LONG",
#   "reasoning": "...",
#   "leverage": 3,
#   "confidence": 0.78,
#   "take_profit_price": 52000.0,
#   "stop_loss_price": 41000.0
# }
```

---

## Full Trade Execution Flow

```python
async def execute_trade(ticker: str, verdict: str, confidence: float, portfolio: dict):
    """Complete trade execution pipeline with all safety checks."""
    from brokers.broker_router import BrokerRouter, Order, OrderSide, OrderType
    from core.config import settings
    
    # 1. Safety check — paper mode
    if settings.PAPER_TRADE_MODE:
        print(f"[PAPER] Would {verdict} {ticker} with confidence {confidence}")
        return {"status": "PAPER", "would_trade": True}
    
    # 2. Determine asset class
    is_crypto = any(c in ticker for c in ["-USD", "BTC", "ETH", "SOL"])
    asset_class = "crypto" if is_crypto else "equity"
    
    # 3. Calculate position size (from RiskManagerAgent output)
    portfolio_value = portfolio.get("total_value", 0)
    position_size_usd = portfolio_value * settings.MAX_POSITION_PCT
    
    # 4. Get current price to calculate quantity
    from gateway.data_engine import data_engine
    price_data = await data_engine.get_price_data(ticker)
    current_price = price_data.get("px", 0)
    if not current_price:
        return {"status": "ERROR", "error": "Could not fetch price"}
    
    qty = position_size_usd / current_price
    
    # 5. Build and execute order
    side = OrderSide.BUY if verdict == "BUY" else OrderSide.SELL
    order = Order(ticker=ticker, side=side, qty=qty, order_type=OrderType.MARKET)
    
    router = BrokerRouter()
    result = await router.execute(order, asset_class=asset_class)
    
    return result
```

---

## Order Status Handling

```python
result = await broker.place_order(order)

if result["status"] == "FILLED":
    # Trade succeeded
    order_id = result["order_id"]
    broker_name = result["broker"]
    
elif result["status"] == "REJECTED":
    # Broker rejected (insufficient funds, etc.)
    reason = result["reason"]
    
elif result["status"] == "ERROR":
    # Technical error
    error = result["error"]
    
elif result["status"] == "PAPER":
    # Paper trade — logged only
    pass
```
