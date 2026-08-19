import React, { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Coins,
  Loader2,
  Lock,
  Minus,
  Plus,
  RefreshCw,
  ShieldCheck,
  TrendingDown,
  TrendingUp,
  WalletCards,
} from "lucide-react";
import { API_BASE } from "../api_config";

const money = (value) => Number(value || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });

export default function VirtualPortfolioView({ onSelect }) {
  const [tab, setTab] = useState("practice");
  const [practice, setPractice] = useState(null);
  const [connections, setConnections] = useState([]);
  const [liveStatus, setLiveStatus] = useState(null);
  const [liveAccount, setLiveAccount] = useState(null);
  const [connectionId, setConnectionId] = useState("");
  const [ideas, setIdeas] = useState([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [practiceForm, setPracticeForm] = useState({ ticker: "AAPL", shares: "1" });
  const [startingBalance, setStartingBalance] = useState("100000");
  const [liveForm, setLiveForm] = useState({ ticker: "BTC", side: "buy", qty: "0.001", leverage: "1", stop_loss: "", take_profit: "", confirm_live: false });
  const [lastLiveResult, setLastLiveResult] = useState(null);

  const loadPractice = async () => {
    const response = await fetch(`${API_BASE}/api/simulation/status`);
    if (response.ok) {
      const payload = await response.json();
      setPractice(payload.status || payload);
    }
  };

  const loadConnectionsAndStatus = async () => {
    const [connectionResponse, statusResponse] = await Promise.all([
      fetch(`${API_BASE}/api/customer/connections`),
      fetch(`${API_BASE}/api/customer/trading/status`),
    ]);
    if (connectionResponse.ok) {
      const all = (await connectionResponse.json()).connections || [];
      const brokers = all.filter((item) => item.category === "broker" && item.enabled);
      setConnections(brokers);
      setConnectionId((current) => current || brokers[0]?.id || "");
    }
    if (statusResponse.ok) setLiveStatus(await statusResponse.json());
  };

  const loadIdeas = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/customer/daily-brief?limit=6`);
      if (response.ok) setIdeas((await response.json()).opportunities || []);
    } catch { /* research ideas are supplementary */ }
  };

  const loadLiveAccount = async (id = connectionId) => {
    if (!id) {
      setLiveAccount(null);
      return;
    }
    try {
      const response = await fetch(`${API_BASE}/api/customer/trading/account?connection_id=${encodeURIComponent(id)}`);
      if (response.ok) setLiveAccount(await response.json());
    } catch {
      setLiveAccount(null);
    }
  };

  useEffect(() => {
    Promise.all([loadPractice(), loadConnectionsAndStatus(), loadIdeas()]).catch(() => {});
  }, []);

  useEffect(() => {
    if (connectionId) loadLiveAccount(connectionId);
  }, [connectionId]);

  const initializePractice = async () => {
    setBusy(true);
    setMessage("");
    try {
      const response = await fetch(`${API_BASE}/api/simulation/init`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ initial_balance: Number(startingBalance) || 100000 }),
      });
      if (!response.ok) throw new Error("Could not create practice account");
      await loadPractice();
      setMessage("Practice account is ready. No real money is involved.");
    } catch (e) {
      setMessage(e.message || "Could not create practice account");
    } finally { setBusy(false); }
  };

  const practiceTrade = async (type, ticker = practiceForm.ticker, shares = practiceForm.shares) => {
    setBusy(true);
    setMessage("");
    try {
      const response = await fetch(`${API_BASE}/api/simulation/${type}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ticker: String(ticker).toUpperCase(), shares: Number(shares) }),
      });
      const result = await response.json();
      if (!response.ok || result.error) throw new Error(result.error || "Practice order failed");
      setPractice(result.status || result);
      setMessage(`${type === "buy" ? "Buy" : "Sell"} completed in the practice account.`);
    } catch (e) {
      setMessage(e.message || "Practice order failed");
    } finally { setBusy(false); }
  };

  const submitLive = async (event) => {
    event.preventDefault();
    setBusy(true);
    setMessage("AITradra is running a fresh multi-agent check before the real order…");
    setLastLiveResult(null);
    try {
      const response = await fetch(`${API_BASE}/api/customer/trading/order`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          connection_id: connectionId,
          ticker: liveForm.ticker.toUpperCase(),
          side: liveForm.side,
          qty: Number(liveForm.qty),
          leverage: Number(liveForm.leverage),
          stop_loss: Number(liveForm.stop_loss),
          take_profit: Number(liveForm.take_profit),
          confirm_live: Boolean(liveForm.confirm_live),
        }),
      });
      const result = await response.json();
      if (!response.ok) {
        const detail = typeof result.detail === "string" ? result.detail : result.detail?.message || "Real order was rejected";
        throw new Error(detail);
      }
      setLastLiveResult(result);
      setMessage(`Order status: ${result.order?.status || "submitted"}. Review the pre-trade analysis below.`);
      await Promise.all([loadLiveAccount(), loadConnectionsAndStatus()]);
    } catch (e) {
      setMessage(e.message || "Real order was not submitted");
    } finally { setBusy(false); }
  };

  const positions = Array.isArray(practice?.positions) ? practice.positions : Object.values(practice?.positions || {});
  const livePositions = liveAccount?.positions || [];
  const practiceReturn = Number(practice?.profit_loss_percentage || 0);
  const manualReady = Boolean(liveStatus?.real_money_ready);
  const blockers = liveStatus?.manual?.blockers || [];

  return (
    <div className="flex-1 overflow-y-auto w-full p-4 md:p-6 lg:p-8 max-w-[1440px] mx-auto animate-fade-in flex flex-col gap-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3"><Coins size={22} className="text-[var(--accent)]" /><h1 className="heading-1">Trading</h1></div>
          <p className="text-[13px] text-[var(--text-muted)] mt-2 max-w-2xl">Practice first, or use a separately unlocked real-money broker connection. AI research provides context; every manual real trade still requires your confirmation.</p>
        </div>
        <div className="inline-flex rounded-[var(--radius-md)] border border-[var(--border-color)] bg-[#171b22] p-1">
          <button onClick={() => setTab("practice")} className={`px-4 py-2 rounded-[var(--radius-sm)] text-[11px] ${tab === "practice" ? "bg-[var(--accent)] text-white" : "text-[var(--text-muted)]"}`}>Practice</button>
          <button onClick={() => setTab("live")} className={`px-4 py-2 rounded-[var(--radius-sm)] text-[11px] ${tab === "live" ? "bg-[var(--negative)] text-white" : "text-[var(--text-muted)]"}`}>Real trading</button>
        </div>
      </div>

      {message && <div className="surface-card p-4 text-[12px] text-[var(--text-muted)]">{busy && <Loader2 size={13} className="inline mr-2 animate-spin" />}{message}</div>}

      {tab === "practice" ? (
        <>
          {!practice?.initialized ? (
            <section className="surface-card max-w-xl p-6">
              <div className="flex items-start gap-3"><ShieldCheck size={19} className="text-[var(--positive)] mt-0.5" /><div><h2 className="heading-3">Create a practice account</h2><p className="text-[11px] text-[var(--text-muted)] mt-2">Use live/reference market prices with simulated cash, fees and slippage. Nothing here sends a real order.</p></div></div>
              <div className="flex gap-3 mt-5"><input type="number" min="1000" className="input-standard" value={startingBalance} onChange={(e) => setStartingBalance(e.target.value)} /><button onClick={initializePractice} disabled={busy} className="btn-primary px-5">Start practice</button></div>
            </section>
          ) : (
            <>
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <Stat label="Practice cash" value={`$${money(practice.available_cash)}`} />
                <Stat label="Account value" value={`$${money(practice.total_balance)}`} />
                <Stat label="Total P/L" value={`$${money(practice.total_profit_loss)}`} positive={Number(practice.total_profit_loss || 0) >= 0} />
                <Stat label="Return" value={`${practiceReturn >= 0 ? "+" : ""}${practiceReturn.toFixed(2)}%`} positive={practiceReturn >= 0} />
              </div>

              <section className="surface-card p-5">
                <div className="flex items-center gap-2 mb-4"><WalletCards size={16} className="text-[var(--accent)]" /><h2 className="heading-3">Practice order</h2></div>
                <div className="grid grid-cols-1 sm:grid-cols-[1fr_1fr_auto_auto] gap-3">
                  <input className="input-standard uppercase" value={practiceForm.ticker} onChange={(e) => setPracticeForm({ ...practiceForm, ticker: e.target.value.toUpperCase() })} placeholder="Ticker" />
                  <input type="number" min="0.0001" step="any" className="input-standard" value={practiceForm.shares} onChange={(e) => setPracticeForm({ ...practiceForm, shares: e.target.value })} placeholder="Quantity" />
                  <button disabled={busy} onClick={() => practiceTrade("buy")} className="btn-standard border-[var(--positive)] text-[var(--positive)]"><Plus size={13} /> Buy</button>
                  <button disabled={busy} onClick={() => practiceTrade("sell")} className="btn-standard border-[var(--negative)] text-[var(--negative)]"><Minus size={13} /> Sell</button>
                </div>
              </section>

              <PositionsTable positions={positions} practice onSell={(ticker, qty) => practiceTrade("sell", ticker, qty)} />
            </>
          )}
        </>
      ) : (
        <>
          <div className={`surface-card p-5 border ${manualReady ? "border-emerald-500/20" : "border-amber-500/20"}`}>
            <div className="flex items-start gap-3">
              {manualReady ? <CheckCircle2 size={18} className="text-[var(--positive)] mt-0.5" /> : <Lock size={18} className="text-amber-300 mt-0.5" />}
              <div className="flex-1"><h2 className="heading-3">{manualReady ? "Real-money manual trading is unlocked" : "Real-money trading is locked"}</h2><p className="text-[11px] text-[var(--text-muted)] mt-2">{liveStatus?.message || "The server owner must intentionally enable live mode. Adding a broker key alone cannot unlock trading."}</p></div>
            </div>
            {!manualReady && blockers.length > 0 && <div className="flex flex-wrap gap-2 mt-4">{blockers.map((item) => <span key={item} className="surface-badge text-amber-200">{item}</span>)}</div>}
          </div>

          <section className="surface-card p-5">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div><h2 className="heading-3">Broker account</h2><p className="text-[10px] text-[var(--text-muted)] mt-1">Broker keys are managed under Intelligence Status → Your data & broker connections.</p></div>
              <div className="flex gap-2"><select className="input-standard min-w-[220px]" value={connectionId} onChange={(e) => setConnectionId(e.target.value)}><option value="">Select broker</option>{connections.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select><button onClick={() => loadLiveAccount()} className="btn-standard"><RefreshCw size={12} /></button></div>
            </div>
            {liveAccount?.ready && <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mt-5"><Stat label="Account value" value={`$${money(liveAccount.balance?.total)}`} /><Stat label="Available" value={`$${money(liveAccount.balance?.available)}`} /><Stat label="Open positions" value={String(livePositions.length)} /><Stat label="Mode" value="REAL MONEY" positive={false} /></div>}
          </section>

          <form onSubmit={submitLive} className="surface-card p-5">
            <div className="flex items-start gap-3 mb-5"><AlertTriangle size={18} className="text-[var(--negative)] mt-0.5" /><div><h2 className="heading-3">Protected real order</h2><p className="text-[10px] text-[var(--text-muted)] mt-1">A fresh DEEP multi-agent analysis runs immediately before submission. Stop-loss and take-profit are mandatory for new positions.</p></div></div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
              <input className="input-standard uppercase" value={liveForm.ticker} onChange={(e) => setLiveForm({ ...liveForm, ticker: e.target.value.toUpperCase() })} placeholder="BTC" />
              <select className="input-standard" value={liveForm.side} onChange={(e) => setLiveForm({ ...liveForm, side: e.target.value })}><option value="buy">Buy / Long</option><option value="sell">Sell / Short</option></select>
              <input type="number" min="0" step="any" className="input-standard" value={liveForm.qty} onChange={(e) => setLiveForm({ ...liveForm, qty: e.target.value })} placeholder="Quantity" />
              <input type="number" min="1" max="10" className="input-standard" value={liveForm.leverage} onChange={(e) => setLiveForm({ ...liveForm, leverage: e.target.value })} placeholder="Leverage" />
              <input type="number" min="0" step="any" className="input-standard" value={liveForm.stop_loss} onChange={(e) => setLiveForm({ ...liveForm, stop_loss: e.target.value })} placeholder="Stop-loss price" />
              <input type="number" min="0" step="any" className="input-standard" value={liveForm.take_profit} onChange={(e) => setLiveForm({ ...liveForm, take_profit: e.target.value })} placeholder="Take-profit price" />
            </div>
            <label className="flex items-start gap-2 mt-5 cursor-pointer"><input type="checkbox" className="mt-0.5" checked={liveForm.confirm_live} onChange={(e) => setLiveForm({ ...liveForm, confirm_live: e.target.checked })} /><span className="text-[11px] text-[var(--text-muted)]">I understand this sends a <strong className="text-white">real-money order</strong> to my connected broker if all server safety checks pass.</span></label>
            <button type="submit" disabled={!manualReady || !connectionId || !liveForm.confirm_live || busy} className="btn-primary mt-5 px-5 py-3 bg-[var(--negative)] hover:opacity-90">{busy ? <Loader2 size={14} className="animate-spin" /> : <ShieldCheck size={14} />} Analyze & submit real order</button>
          </form>

          {liveAccount?.ready && <PositionsTable positions={livePositions} />}

          {lastLiveResult?.pre_trade_analysis && (
            <section className="surface-card p-5">
              <h2 className="heading-3">Pre-trade AI analysis</h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mt-4"><Stat label="AI view" value={lastLiveResult.pre_trade_analysis.prediction?.recommendation || "HOLD"} /><Stat label="Confidence" value={`${Number(lastLiveResult.pre_trade_analysis.prediction?.confidence || 0).toFixed(0)}%`} /><Stat label="Risk" value={lastLiveResult.pre_trade_analysis.risk?.level || "MEDIUM"} /></div>
              <p className="text-[11px] text-[var(--text-muted)] leading-relaxed mt-4">{lastLiveResult.pre_trade_analysis.why_it_moved?.summary}</p>
            </section>
          )}
        </>
      )}

      <section className="surface-card p-5">
        <div className="flex items-center justify-between"><div><h2 className="heading-3">Ideas to research</h2><p className="text-[10px] text-[var(--text-muted)] mt-1">These are research leads, not automatic orders.</p></div></div>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 mt-4">{ideas.slice(0, 6).map((idea) => <button key={idea.ticker} onClick={() => onSelect?.(idea.ticker)} className="rounded-[var(--radius-md)] border border-[var(--border-color)] bg-[#171b22] p-3 text-left hover:border-[var(--accent)]"><div className="text-[11px] font-semibold text-white">{idea.ticker}</div><div className="text-[9px] text-[var(--text-muted)] mt-1">{idea.recommendation || "HOLD"} • {Number(idea.confidence_score || 0).toFixed(0)}%</div></button>)}</div>
      </section>
    </div>
  );
}

function Stat({ label, value, positive }) {
  return <div className="surface-card p-4"><div className="text-[9px] uppercase tracking-wider text-[var(--text-muted)]">{label}</div><div className={`text-[15px] font-mono font-semibold mt-1 ${positive === true ? "text-[var(--positive)]" : positive === false ? "text-[var(--negative)]" : "text-white"}`}>{value}</div></div>;
}

function PositionsTable({ positions = [], practice = false, onSell }) {
  return (
    <section className="surface-card overflow-hidden">
      <div className="p-5 border-b border-[var(--border-color)] flex items-center justify-between"><h2 className="heading-3">Open positions</h2><span className="surface-badge">{positions.length}</span></div>
      {positions.length ? <div className="overflow-x-auto"><table className="table-standard min-w-[720px]"><thead><tr><th>Asset</th><th className="text-right">Quantity</th><th className="text-right">Entry</th><th className="text-right">Current</th><th className="text-right">P/L</th><th>Protection</th>{practice && <th>Action</th>}</tr></thead><tbody>{positions.map((p, index) => {
        const ticker = p.ticker || p.symbol;
        const qty = Number(p.quantity ?? p.qty ?? p.shares ?? 0);
        const entry = Number(p.buy_price ?? p.entry_price ?? p.avg_price ?? 0);
        const current = Number(p.current_price ?? entry);
        const pnl = Number(p.profit_loss ?? p.unrealized_pnl ?? 0);
        return <tr key={`${ticker}-${index}`}><td className="font-semibold text-white">{ticker}</td><td className="text-right font-mono">{qty.toFixed(4)}</td><td className="text-right font-mono">${money(entry)}</td><td className="text-right font-mono">${money(current)}</td><td className="text-right font-mono" style={{ color: pnl >= 0 ? "var(--positive)" : "var(--negative)" }}>{pnl >= 0 ? <TrendingUp size={11} className="inline mr-1" /> : <TrendingDown size={11} className="inline mr-1" />}${money(pnl)}</td><td className="text-[10px] text-[var(--text-muted)]">{p.stop_loss ? `SL ${p.stop_loss}` : "—"}{p.take_profit ? ` • TP ${p.take_profit}` : ""}</td>{practice && <td><button className="btn-standard h-8 px-3 text-[var(--negative)]" onClick={() => onSell?.(ticker, Math.abs(qty))}>Close</button></td>}</tr>;
      })}</tbody></table></div> : <div className="p-10 text-center text-[11px] text-[var(--text-muted)]">No open positions.</div>}
    </section>
  );
}
