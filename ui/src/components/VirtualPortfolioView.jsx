import React, { useState, useEffect } from "react";
import {
  Coins,
  Loader2,
  Plus,
  Minus,
  Search,
  ShieldCheck,
  TrendingUp,
  TrendingDown,
  Info,
} from "lucide-react";
import { API_BASE } from "../api_config";

const money = (value) =>
  Number(value || 0).toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

export default function VirtualPortfolioView({ onSelect }) {
  const [data, setData] = useState(null);
  const [intel, setIntel] = useState(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [startingBalance, setStartingBalance] = useState("100000");
  const [order, setOrder] = useState({ ticker: "", shares: "" });
  const [sellQuantities, setSellQuantities] = useState({});
  const [notice, setNotice] = useState(null);

  const loadData = async () => {
    try {
      const [portfolioResponse, intelResponse] = await Promise.all([
        fetch(`${API_BASE}/api/simulation/status`),
        fetch(`${API_BASE}/api/intel/overview`),
      ]);
      if (portfolioResponse.ok) {
        const json = await portfolioResponse.json();
        setData(json.status || json);
      }
      if (intelResponse.ok) setIntel(await intelResponse.json());
    } catch {
      setNotice({ type: "error", text: "Practice account data is temporarily unavailable." });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const timer = setInterval(loadData, 10_000);
    return () => clearInterval(timer);
  }, []);

  const initialize = async () => {
    const balance = Number(startingBalance);
    if (!Number.isFinite(balance) || balance <= 0) {
      setNotice({ type: "error", text: "Enter a starting balance greater than zero." });
      return;
    }
    setActionLoading(true);
    setNotice(null);
    try {
      const response = await fetch(`${API_BASE}/api/simulation/init`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ initial_balance: balance }),
      });
      const result = await response.json();
      if (!response.ok || result?.error) throw new Error(result?.error || "Could not create practice account");
      setData(result);
      setNotice({ type: "success", text: "Practice account is ready. No real money is connected." });
    } catch (error) {
      setNotice({ type: "error", text: error.message });
    } finally {
      setActionLoading(false);
    }
  };

  const trade = async (type, ticker, shares) => {
    const cleanTicker = String(ticker || "").trim().toUpperCase();
    const quantity = Number(shares);
    if (!cleanTicker) {
      setNotice({ type: "error", text: "Enter a ticker, for example AAPL or BTC-USD." });
      return;
    }
    if (!Number.isFinite(quantity) || quantity <= 0) {
      setNotice({ type: "error", text: "Enter a share or unit quantity greater than zero." });
      return;
    }

    setActionLoading(true);
    setNotice(null);
    try {
      const response = await fetch(`${API_BASE}/api/simulation/${type}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ticker: cleanTicker, shares: quantity }),
      });
      const result = await response.json();
      if (!response.ok || result?.error) throw new Error(result?.error || "Practice order could not be completed");
      setData(result);
      setNotice({
        type: "success",
        text: `${type === "buy" ? "Bought" : "Sold"} ${quantity} ${cleanTicker} in your practice account.`,
      });
      if (type === "buy") setOrder({ ticker: "", shares: "" });
      if (type === "sell") {
        setSellQuantities((previous) => ({ ...previous, [cleanTicker]: "" }));
      }
    } catch (error) {
      setNotice({ type: "error", text: error.message });
    } finally {
      setActionLoading(false);
    }
  };

  if (loading && !data) {
    return (
      <div className="h-full flex flex-col items-center justify-center gap-4 bg-[var(--app-bg)] w-full">
        <Loader2 size={24} className="text-[var(--accent)] animate-spin" />
        <span className="text-[12px] text-[var(--text-muted)]">Loading your practice account…</span>
      </div>
    );
  }

  if (!data?.initialized) {
    return (
      <div className="h-full overflow-y-auto flex items-center justify-center p-6 bg-[var(--app-bg)] w-full">
        <div className="surface-card max-w-lg w-full p-8 text-center flex flex-col items-center border border-[var(--border-color)]">
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-[#1e232b] border border-[var(--border-color)] mb-5">
            <Coins size={30} className="text-[var(--accent)]" />
          </div>
          <span className="surface-badge mb-3 text-[var(--positive)]">Practice mode • No real money</span>
          <h2 className="heading-2">Create a practice account</h2>
          <p className="mt-3 text-[13px] text-[var(--text-muted)] leading-relaxed">
            Try ideas with current market prices before risking capital. Simulated fills include configurable slippage and fees so results are less idealized.
          </p>
          <div className="w-full mt-7 text-left">
            <label className="text-small-caps block mb-2">Starting balance</label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-muted)]">$</span>
              <input
                type="number"
                min="1"
                value={startingBalance}
                onChange={(event) => setStartingBalance(event.target.value)}
                className="input-standard w-full !pl-7 font-mono"
              />
            </div>
          </div>
          {notice && (
            <div className="mt-4 w-full text-left text-[12px] text-[var(--negative)]">{notice.text}</div>
          )}
          <button onClick={initialize} disabled={actionLoading} className="btn-primary w-full py-3 text-[13px] mt-5">
            {actionLoading ? <><Loader2 size={14} className="animate-spin" /> Creating…</> : "Start practicing"}
          </button>
          <div className="mt-5 flex gap-2 text-left text-[11px] text-[var(--text-muted)] leading-relaxed">
            <ShieldCheck size={14} className="text-[var(--positive)] shrink-0 mt-0.5" />
            This account is for learning and testing. A profitable practice result does not guarantee the same result with real money.
          </div>
        </div>
      </div>
    );
  }

  const cash = Number(data.available_cash || 0);
  const equity = Number(data.total_balance || 0);
  const pnl = Number(data.total_profit_loss || 0);
  const returnPct = Number(data.profit_loss_percentage || 0);
  const fees = Number(data.fees_paid || 0);
  const positions = Array.isArray(data.positions) ? data.positions : Object.values(data.positions || {});
  const positive = returnPct >= 0;
  const opportunities = (intel?.top_opportunities || []).slice(0, 5);
  const assumptions = data.execution_assumptions || {};

  return (
    <div className="flex-1 overflow-y-auto w-full p-4 md:p-6 lg:p-8 max-w-[1440px] mx-auto animate-fade-in flex flex-col gap-6">
      <div className="flex flex-col lg:flex-row gap-5 justify-between lg:items-center">
        <div>
          <div className="flex items-center gap-3">
            <Coins size={20} className="text-[var(--accent)]" />
            <h1 className="heading-1">Paper Trading</h1>
            <span className="surface-badge text-[var(--positive)]">Practice only</span>
          </div>
          <p className="text-[13px] text-[var(--text-muted)] mt-2 max-w-2xl">
            Test your decisions with current prices and realistic execution assumptions. Nothing on this page sends a real-money order.
          </p>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <Metric label="Cash" value={`$${money(cash)}`} />
          <Metric label="Account value" value={`$${money(equity)}`} />
          <Metric label="Total P/L" value={`${pnl >= 0 ? "+" : ""}$${money(pnl)}`} positive={pnl >= 0} />
          <Metric label="Return" value={`${positive ? "+" : ""}${returnPct.toFixed(2)}%`} positive={positive} />
        </div>
      </div>

      {notice && (
        <div className={`rounded-[var(--radius-md)] border px-4 py-3 text-[12px] ${
          notice.type === "success"
            ? "border-[#10b98140] bg-[#10b98110] text-[var(--positive)]"
            : "border-[#ef444440] bg-[#ef444410] text-[var(--negative)]"
        }`}>
          {notice.text}
        </div>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-[1fr_330px] gap-6">
        <div className="flex flex-col gap-6">
          <section className="surface-card p-5 md:p-6">
            <div className="flex items-start justify-between gap-4 mb-5">
              <div>
                <h2 className="heading-3">Place a practice order</h2>
                <p className="text-[11px] text-[var(--text-muted)] mt-1">Use the same symbols you see elsewhere in AITradra.</p>
              </div>
              <span className="surface-badge">No real funds</span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-[1fr_180px_auto] gap-3">
              <div className="relative">
                <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-muted)]" />
                <input
                  value={order.ticker}
                  onChange={(event) => setOrder((previous) => ({ ...previous, ticker: event.target.value.toUpperCase() }))}
                  placeholder="Ticker, e.g. AAPL"
                  className="input-standard w-full !pl-9 font-mono"
                />
              </div>
              <input
                type="number"
                min="0"
                step="any"
                value={order.shares}
                onChange={(event) => setOrder((previous) => ({ ...previous, shares: event.target.value }))}
                placeholder="Shares / units"
                className="input-standard w-full font-mono"
              />
              <button
                onClick={() => trade("buy", order.ticker, order.shares)}
                disabled={actionLoading}
                className="btn-standard border-[var(--positive)] text-[var(--positive)] hover:bg-[#10b98115] justify-center"
              >
                {actionLoading ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />} Buy
              </button>
            </div>
          </section>

          <section className="surface-card overflow-hidden">
            <div className="p-5 border-b border-[var(--border-color)] flex items-center justify-between">
              <div>
                <h2 className="heading-3">Open practice positions</h2>
                <p className="text-[11px] text-[var(--text-muted)] mt-1">Values refresh automatically from market data.</p>
              </div>
              <span className="surface-badge">{positions.length} open</span>
            </div>
            {positions.length ? (
              <div className="overflow-x-auto">
                <table className="table-standard min-w-[760px]">
                  <thead>
                    <tr>
                      <th>Symbol</th>
                      <th className="text-right">Quantity</th>
                      <th className="text-right">Average fill</th>
                      <th className="text-right">Current</th>
                      <th className="text-right">P/L</th>
                      <th className="text-center">Sell</th>
                    </tr>
                  </thead>
                  <tbody>
                    {positions.map((position) => {
                      const ticker = position.ticker;
                      const quantity = Number(position.quantity || position.shares || 0);
                      const avg = Number(position.buy_price || position.avg_price || 0);
                      const current = Number(position.current_price || avg);
                      const positionPnl = Number(position.profit_loss || 0);
                      const positionReturn = Number(position.profit_loss_pct || 0);
                      const isPositive = positionReturn >= 0;
                      return (
                        <tr key={ticker}>
                          <td>
                            <button onClick={() => onSelect?.(ticker)} className="font-semibold text-white hover:text-[var(--accent)]">
                              {ticker}
                            </button>
                          </td>
                          <td className="text-right font-mono text-[var(--text-muted)]">{quantity.toFixed(quantity % 1 === 0 ? 0 : 4)}</td>
                          <td className="text-right font-mono">${money(avg)}</td>
                          <td className="text-right font-mono text-white">${money(current)}</td>
                          <td className={`text-right font-mono ${isPositive ? "text-[var(--positive)]" : "text-[var(--negative)]"}`}>
                            <div>{isPositive ? "+" : ""}{positionReturn.toFixed(2)}%</div>
                            <div className="text-[10px] opacity-75">{positionPnl >= 0 ? "+" : ""}${money(positionPnl)}</div>
                          </td>
                          <td>
                            <div className="flex items-center justify-center gap-2">
                              <input
                                type="number"
                                min="0"
                                step="any"
                                max={quantity}
                                value={sellQuantities[ticker] || ""}
                                onChange={(event) => setSellQuantities((previous) => ({ ...previous, [ticker]: event.target.value }))}
                                placeholder="Qty"
                                className="input-standard !w-20 !p-1.5 text-center"
                              />
                              <button
                                onClick={() => trade("sell", ticker, sellQuantities[ticker] || quantity)}
                                disabled={actionLoading}
                                className="btn-standard !px-2.5 !py-1.5 border-[var(--negative)] text-[var(--negative)] hover:bg-[#ef444415]"
                              >
                                <Minus size={12} /> Sell
                              </button>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="p-10 text-center text-[13px] text-[var(--text-muted)]">
                You do not have any practice positions yet. Try a small order above.
              </div>
            )}
          </section>

          <section className="surface-card overflow-hidden">
            <div className="p-5 border-b border-[var(--border-color)] flex items-center justify-between">
              <h2 className="heading-3">Practice activity</h2>
              <span className="surface-badge">{data.history?.length || 0} orders</span>
            </div>
            {data.history?.length ? (
              <div className="overflow-x-auto max-h-[320px] no-scrollbar">
                <table className="table-standard min-w-[720px]">
                  <thead>
                    <tr>
                      <th>Time</th>
                      <th>Action</th>
                      <th>Symbol</th>
                      <th className="text-right">Quantity</th>
                      <th className="text-right">Fill</th>
                      <th className="text-right">Fee</th>
                      <th className="text-right">P/L</th>
                    </tr>
                  </thead>
                  <tbody>
                    {[...data.history].reverse().slice(0, 50).map((item, index) => (
                      <tr key={`${item.timestamp}-${index}`}>
                        <td className="text-[11px] text-[var(--text-muted)] font-mono">
                          {new Date(item.timestamp).toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}
                        </td>
                        <td>
                          <span className={`text-[10px] font-bold px-2 py-1 rounded ${item.type === "BUY" ? "bg-[#10b98120] text-[var(--positive)]" : "bg-[#ef444420] text-[var(--negative)]"}`}>
                            {item.type}
                          </span>
                        </td>
                        <td className="font-semibold text-white">{item.ticker}</td>
                        <td className="text-right font-mono">{Number(item.quantity || 0).toFixed(4)}</td>
                        <td className="text-right font-mono">${money(item.price)}</td>
                        <td className="text-right font-mono text-[var(--text-muted)]">${money(item.fee)}</td>
                        <td className={`text-right font-mono ${Number(item.profit_loss || 0) >= 0 ? "text-[var(--positive)]" : "text-[var(--negative)]"}`}>
                          {item.type === "SELL" ? `${Number(item.profit_loss || 0) >= 0 ? "+" : ""}$${money(item.profit_loss)}` : "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="p-8 text-center text-[13px] text-[var(--text-muted)]">Your practice order history will appear here.</div>
            )}
          </section>
        </div>

        <aside className="flex flex-col gap-5">
          <section className="surface-card p-5">
            <div className="flex items-center gap-2 mb-4">
              <ShieldCheck size={16} className="text-[var(--positive)]" />
              <h3 className="heading-3">How practice fills work</h3>
            </div>
            <div className="space-y-3 text-[12px] text-[var(--text-muted)] leading-relaxed">
              <p>Orders use the latest market reference price available to AITradra.</p>
              <div className="flex justify-between"><span>Estimated slippage</span><span className="font-mono text-white">{Number(assumptions.slippage_bps || 0).toFixed(1)} bps</span></div>
              <div className="flex justify-between"><span>Estimated trading fee</span><span className="font-mono text-white">{Number(assumptions.fee_bps || 0).toFixed(1)} bps</span></div>
              <div className="flex justify-between"><span>Fees paid so far</span><span className="font-mono text-white">${money(fees)}</span></div>
            </div>
          </section>

          <section className="surface-card p-5">
            <div className="flex items-center justify-between mb-4">
              <h3 className="heading-3">Ideas to research</h3>
              <Info size={14} className="text-[var(--text-muted)]" />
            </div>
            <p className="text-[11px] text-[var(--text-muted)] mb-4">These are research leads, not automatic orders.</p>
            <div className="space-y-2">
              {opportunities.length ? opportunities.map((item) => {
                const ticker = item.ticker || item.id;
                const direction = item.prediction_direction || item.direction;
                const up = direction === "UP" || String(item.recommendation || "").includes("BUY");
                return (
                  <button
                    key={ticker}
                    onClick={() => onSelect?.(ticker)}
                    className="w-full flex items-center justify-between gap-3 rounded-[var(--radius-md)] border border-[var(--border-color)] bg-[#171b22] px-3 py-3 hover:border-[var(--accent)] transition text-left"
                  >
                    <div>
                      <div className="font-semibold text-white text-[12px]">{ticker}</div>
                      <div className="text-[10px] text-[var(--text-muted)] mt-1">{item.recommendation || "Research"} • {Number(item.confidence_score || item.confidence || 0).toFixed(0)}% confidence</div>
                    </div>
                    {up ? <TrendingUp size={15} className="text-[var(--positive)]" /> : <TrendingDown size={15} className="text-[var(--negative)]" />}
                  </button>
                );
              }) : (
                <div className="text-[12px] text-[var(--text-muted)]">Research ideas will appear after market intelligence finishes loading.</div>
              )}
            </div>
          </section>

          <section className="rounded-[var(--radius-lg)] border border-amber-400/20 bg-amber-400/5 p-5">
            <div className="flex items-start gap-2">
              <Info size={15} className="text-amber-300 shrink-0 mt-0.5" />
              <p className="text-[11px] text-[var(--text-muted)] leading-relaxed">
                Use practice results to learn how a strategy behaves across many trades and market conditions. One winning trade—or even a winning month—is not enough evidence that a strategy will remain profitable.
              </p>
            </div>
          </section>
        </aside>
      </div>
    </div>
  );
}

function Metric({ label, value, positive }) {
  return (
    <div className="surface-card min-w-[130px] px-4 py-3">
      <span className="text-small-caps block mb-1">{label}</span>
      <span
        className={`font-mono text-[14px] font-semibold ${
          positive === undefined ? "text-white" : positive ? "text-[var(--positive)]" : "text-[var(--negative)]"
        }`}
      >
        {value}
      </span>
    </div>
  );
}
