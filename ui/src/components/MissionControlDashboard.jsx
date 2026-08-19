import React, { useEffect, useState } from "react";
import { Activity, CheckCircle2, Clock3, Cpu, Loader2, RefreshCw, ShieldCheck, Sparkles } from "lucide-react";
import { API_BASE } from "../api_config";

export default function MissionControlDashboard({ agentsStatus = [] }) {
  const [daily, setDaily] = useState(null);
  const [history, setHistory] = useState([]);
  const [trading, setTrading] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    try {
      const [dailyRes, historyRes, tradingRes] = await Promise.all([
        fetch(`${API_BASE}/api/customer/daily-brief?limit=8`),
        fetch(`${API_BASE}/api/customer/history?limit=12`),
        fetch(`${API_BASE}/api/customer/trading/status`),
      ]);
      if (dailyRes.ok) setDaily(await dailyRes.json());
      if (historyRes.ok) setHistory((await historyRes.json()).history || []);
      if (tradingRes.ok) setTrading(await tradingRes.json());
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    const timer = setInterval(load, 60000);
    return () => clearInterval(timer);
  }, []);

  const readyAgents = agentsStatus.filter((agent) => ["active", "idle"].includes(String(agent.status || "").toLowerCase())).length;
  const autoEnabled = Boolean(trading?.automation?.automation_enabled);

  if (loading) return <div className="h-full flex items-center justify-center gap-3"><Loader2 size={22} className="animate-spin text-[var(--accent)]" /><span className="text-[12px] text-[var(--text-muted)]">Preparing your daily control center…</span></div>;

  return (
    <div className="flex-1 overflow-y-auto w-full p-4 md:p-6 lg:p-8 max-w-[1440px] mx-auto animate-fade-in flex flex-col gap-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div><div className="flex items-center gap-3"><Cpu size={21} className="text-[var(--accent)]" /><h1 className="heading-1">Mission Control</h1></div><p className="text-[13px] text-[var(--text-muted)] mt-2 max-w-2xl">A customer view of what AITradra has collected, what it is watching, and what activity has happened recently.</p></div>
        <button onClick={load} className="btn-standard h-9 px-4"><RefreshCw size={13} /> Refresh</button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card icon={Activity} label="AI services ready" value={`${readyAgents}/${agentsStatus.length || 0}`} sub="Specialists available for market checks" />
        <Card icon={Sparkles} label="Tracked today" value={String((daily?.top_movers || []).length)} sub="Leading market moves in the current brief" />
        <Card icon={Clock3} label="Saved activity" value={String(history.length)} sub="Recent research and trading history" />
        <Card icon={ShieldCheck} label="Auto trading" value={autoEnabled ? "Enabled" : "Off"} sub={autoEnabled ? "Autonomous cycles are explicitly enabled" : "No autonomous real-money orders can start"} good={!autoEnabled} />
      </div>

      <section className="surface-card p-5">
        <div className="flex items-start gap-3"><CheckCircle2 size={17} className="text-[var(--positive)] mt-0.5" /><div><h2 className="heading-3">What the system does automatically</h2><p className="text-[11px] text-[var(--text-muted)] leading-relaxed mt-2">Price collectors refresh while markets are active, lightweight public news feeds continue through the day, intelligence is re-scored in the background, and customer-added APIs are used automatically when compatible data is requested.</p></div></div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 mt-5">{["Collect market prices", "Collect public news", "Refresh AI predictions", "Save customer history"].map((label) => <div key={label} className="rounded-[var(--radius-md)] border border-[var(--border-color)] bg-[#171b22] p-3 text-[11px] text-white"><CheckCircle2 size={12} className="text-[var(--positive)] inline mr-2" />{label}</div>)}</div>
      </section>

      <div className="grid grid-cols-1 xl:grid-cols-[1.15fr_0.85fr] gap-6">
        <section className="surface-card overflow-hidden">
          <div className="p-5 border-b border-[var(--border-color)]"><h2 className="heading-3">Today’s research leads</h2><p className="text-[10px] text-[var(--text-muted)] mt-1">These are assets worth investigating, not automatic buy orders.</p></div>
          <div className="divide-y divide-[var(--border-color)]">{(daily?.opportunities || []).slice(0, 8).map((row) => <div key={row.ticker} className="p-4 flex items-center justify-between gap-4"><div><div className="text-[12px] font-semibold text-white">{row.ticker}</div><div className="text-[9px] text-[var(--text-muted)] mt-1 capitalize">{String(row.primary_driver || "technical").replace(/_/g, " ")} • {row.risk_level || "MEDIUM"} risk</div></div><div className="text-right"><span className="surface-badge">{row.recommendation || "HOLD"}</span><div className="text-[9px] text-[var(--text-muted)] mt-1">{Number(row.confidence_score || 0).toFixed(0)}% confidence</div></div></div>)}</div>
        </section>

        <section className="surface-card overflow-hidden">
          <div className="p-5 border-b border-[var(--border-color)]"><h2 className="heading-3">Recent customer history</h2><p className="text-[10px] text-[var(--text-muted)] mt-1">Stored under the local default history profile.</p></div>
          <div className="divide-y divide-[var(--border-color)]">{history.length ? history.map((item) => <div key={item.id} className="p-4"><div className="flex items-center justify-between gap-3"><div className="text-[11px] font-semibold text-white">{item.title}</div>{item.ticker && <span className="surface-badge">{item.ticker}</span>}</div><div className="text-[9px] text-[var(--text-muted)] mt-1">{new Date(item.created_at).toLocaleString()} • {String(item.event_type || "activity").replace(/_/g, " ")}</div></div>) : <div className="p-8 text-center text-[11px] text-[var(--text-muted)]">Your research history will appear here after you run full stock research or submit a trade.</div>}</div>
        </section>
      </div>
    </div>
  );
}

function Card({ icon: Icon, label, value, sub, good }) {
  return <div className="surface-card p-5"><div className="flex items-center justify-between"><Icon size={17} className={good ? "text-[var(--positive)]" : "text-[var(--accent)]"} /><span className="text-small-caps">{label}</span></div><div className="text-xl font-mono font-bold text-white mt-4">{value}</div><p className="text-[10px] text-[var(--text-muted)] mt-1 leading-relaxed">{sub}</p></div>;
}
