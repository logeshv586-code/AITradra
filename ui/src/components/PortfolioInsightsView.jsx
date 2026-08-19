import React, { useEffect, useState } from "react";
import { Coins, Loader2, Lock, PieChart, RefreshCw, ShieldCheck, WalletCards } from "lucide-react";
import { API_BASE } from "../api_config";

const money = (value) => Number(value || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });

export default function PortfolioInsightsView() {
  const [practice, setPractice] = useState(null);
  const [connections, setConnections] = useState([]);
  const [connectionId, setConnectionId] = useState("");
  const [live, setLive] = useState(null);
  const [market, setMarket] = useState(null);
  const [loading, setLoading] = useState(true);

  const loadBase = async () => {
    try {
      const [practiceRes, connectionsRes, marketRes] = await Promise.all([
        fetch(`${API_BASE}/api/simulation/status`),
        fetch(`${API_BASE}/api/customer/connections`),
        fetch(`${API_BASE}/api/portfolio/insights`),
      ]);
      if (practiceRes.ok) {
        const payload = await practiceRes.json();
        setPractice(payload.status || payload);
      }
      if (connectionsRes.ok) {
        const all = (await connectionsRes.json()).connections || [];
        const brokers = all.filter((item) => item.category === "broker" && item.enabled);
        setConnections(brokers);
        setConnectionId((current) => current || brokers[0]?.id || "");
      }
      if (marketRes.ok) setMarket(await marketRes.json());
    } finally { setLoading(false); }
  };

  const loadLive = async (id = connectionId) => {
    if (!id) { setLive(null); return; }
    try {
      const response = await fetch(`${API_BASE}/api/customer/trading/account?connection_id=${encodeURIComponent(id)}`);
      if (response.ok) setLive(await response.json());
    } catch { setLive(null); }
  };

  useEffect(() => {
    loadBase();
    const timer = setInterval(loadBase, 30000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => { if (connectionId) loadLive(connectionId); }, [connectionId]);

  if (loading) return <div className="h-full flex items-center justify-center gap-3"><Loader2 size={22} className="animate-spin text-[var(--accent)]" /><span className="text-[12px] text-[var(--text-muted)]">Loading your accounts…</span></div>;

  const practicePositions = Array.isArray(practice?.positions) ? practice.positions : Object.values(practice?.positions || {});
  const livePositions = live?.positions || [];
  const sectors = market?.sectors || [];

  return (
    <div className="flex-1 overflow-y-auto w-full p-4 md:p-6 lg:p-8 max-w-[1440px] mx-auto animate-fade-in flex flex-col gap-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div><div className="flex items-center gap-3"><PieChart size={21} className="text-[var(--accent)]" /><h1 className="heading-1">Portfolio</h1></div><p className="text-[13px] text-[var(--text-muted)] mt-2">See your practice capital and, when connected/unlocked, your real broker account separately. Values are never mixed together.</p></div>
        <button onClick={() => { loadBase(); loadLive(); }} className="btn-standard h-9 px-4"><RefreshCw size={13} /> Refresh</button>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <section className="surface-card p-5">
          <div className="flex items-start justify-between gap-4"><div className="flex items-start gap-3"><Coins size={18} className="text-[var(--positive)] mt-0.5" /><div><h2 className="heading-3">Practice account</h2><p className="text-[10px] text-[var(--text-muted)] mt-1">Simulated capital only—no real money.</p></div></div><span className="surface-badge text-[var(--positive)]">PRACTICE</span></div>
          {practice?.initialized ? <div className="grid grid-cols-2 gap-3 mt-5"><Metric label="Account value" value={`$${money(practice.total_balance)}`} /><Metric label="Available cash" value={`$${money(practice.available_cash)}`} /><Metric label="Total P/L" value={`$${money(practice.total_profit_loss)}`} /><Metric label="Return" value={`${Number(practice.profit_loss_percentage || 0).toFixed(2)}%`} /></div> : <div className="mt-5 rounded-[var(--radius-md)] border border-dashed border-[var(--border-color)] p-6 text-[11px] text-[var(--text-muted)]">No practice account yet. Open Paper Trading → Practice to create one.</div>}
        </section>

        <section className="surface-card p-5">
          <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3"><div className="flex items-start gap-3">{live?.ready ? <ShieldCheck size={18} className="text-[var(--positive)] mt-0.5" /> : <Lock size={18} className="text-amber-300 mt-0.5" />}<div><h2 className="heading-3">Real broker account</h2><p className="text-[10px] text-[var(--text-muted)] mt-1">Only visible when a broker connection is configured and live mode is unlocked.</p></div></div><select className="input-standard max-w-[220px]" value={connectionId} onChange={(e) => setConnectionId(e.target.value)}><option value="">Select broker</option>{connections.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></div>
          {live?.ready ? <div className="grid grid-cols-2 gap-3 mt-5"><Metric label="Account value" value={`$${money(live.balance?.total)}`} /><Metric label="Available" value={`$${money(live.balance?.available)}`} /><Metric label="Open positions" value={String(livePositions.length)} /><Metric label="Broker" value="Hyperliquid" /></div> : <div className="mt-5 rounded-[var(--radius-md)] border border-dashed border-[var(--border-color)] p-6 text-[11px] text-[var(--text-muted)]">{connectionId ? (live?.blockers?.[0] || "Real-money account access is locked by server safety settings.") : "Add a broker connection from Intelligence Status to see a real account here."}</div>}
        </section>
      </div>

      <AccountPositions title="Practice positions" positions={practicePositions} practice />
      <AccountPositions title="Real broker positions" positions={livePositions} />

      <section className="surface-card overflow-hidden">
        <div className="p-5 border-b border-[var(--border-color)]"><div className="flex items-center gap-2"><WalletCards size={16} className="text-[var(--accent)]" /><h2 className="heading-3">Research universe diversification</h2></div><p className="text-[10px] text-[var(--text-muted)] mt-1">This is the mix of assets AITradra is currently tracking—not your personal portfolio allocation.</p></div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-px bg-[var(--border-color)]">{sectors.slice(0, 12).map((sector) => <div key={sector.sector} className="bg-[var(--card-bg)] p-4"><div className="flex items-center justify-between"><span className="text-[11px] font-semibold text-white">{sector.sector}</span><span className="surface-badge">{Number(sector.allocation_pct || 0).toFixed(1)}%</span></div><div className="text-[9px] text-[var(--text-muted)] mt-2">{sector.count || 0} tracked • {(sector.tickers || []).slice(0, 4).join(", ")}</div></div>)}</div>
      </section>
    </div>
  );
}

function Metric({ label, value }) { return <div className="rounded-[var(--radius-md)] border border-[var(--border-color)] bg-[#171b22] p-3"><div className="text-[9px] uppercase tracking-wider text-[var(--text-muted)]">{label}</div><div className="text-[13px] font-mono font-semibold text-white mt-1">{value}</div></div>; }

function AccountPositions({ title, positions = [], practice = false }) {
  return <section className="surface-card overflow-hidden"><div className="p-5 border-b border-[var(--border-color)] flex items-center justify-between"><h2 className="heading-3">{title}</h2><span className="surface-badge">{positions.length}</span></div>{positions.length ? <div className="overflow-x-auto"><table className="table-standard min-w-[720px]"><thead><tr><th>Asset</th><th className="text-right">Quantity</th><th className="text-right">Entry</th><th className="text-right">Current</th><th className="text-right">P/L</th><th>Protection</th></tr></thead><tbody>{positions.map((p, index) => { const qty = Number(p.quantity ?? p.qty ?? p.shares ?? 0); const entry = Number(p.buy_price ?? p.entry_price ?? p.avg_price ?? 0); const current = Number(p.current_price ?? entry); const pnl = Number(p.profit_loss ?? p.unrealized_pnl ?? 0); return <tr key={`${p.ticker}-${index}`}><td className="font-semibold text-white">{p.ticker}</td><td className="text-right font-mono">{qty.toFixed(4)}</td><td className="text-right font-mono">${money(entry)}</td><td className="text-right font-mono">${money(current)}</td><td className="text-right font-mono" style={{ color: pnl >= 0 ? "var(--positive)" : "var(--negative)" }}>${money(pnl)}</td><td className="text-[10px] text-[var(--text-muted)]">{practice ? "Simulated" : `${p.stop_loss ? `SL ${p.stop_loss}` : "—"}${p.take_profit ? ` • TP ${p.take_profit}` : ""}`}</td></tr>; })}</tbody></table></div> : <div className="p-8 text-center text-[11px] text-[var(--text-muted)]">No positions in this account.</div>}</section>;
}
