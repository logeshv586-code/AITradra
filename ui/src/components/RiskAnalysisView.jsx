import React, { useEffect, useMemo, useState } from "react";
import { AlertTriangle, Loader2, Search, Shield, ShieldCheck } from "lucide-react";
import { API_BASE } from "../api_config";

const tone = {
  LOW: { icon: ShieldCheck, color: "var(--positive)", label: "Lower risk" },
  MEDIUM: { icon: Shield, color: "var(--warning)", label: "Moderate risk" },
  HIGH: { icon: AlertTriangle, color: "var(--negative)", label: "Higher risk" },
};

export default function RiskAnalysisView() {
  const [rows, setRows] = useState([]);
  const [selected, setSelected] = useState(null);
  const [detail, setDetail] = useState(null);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/market/predictions`);
      if (!response.ok) throw new Error("Risk data is temporarily unavailable");
      setRows((await response.json()).predictions || []);
    } catch (e) {
      setError(e.message || "Risk data is unavailable");
    } finally { setLoading(false); }
  };

  useEffect(() => {
    load();
    const timer = setInterval(load, 60000);
    return () => clearInterval(timer);
  }, []);

  const openRisk = async (ticker) => {
    setSelected(ticker);
    setDetail(null);
    const response = await fetch(`${API_BASE}/api/stock/${encodeURIComponent(ticker)}/risk`);
    if (response.ok) setDetail(await response.json());
  };

  const filtered = useMemo(() => {
    const q = search.toLowerCase().trim();
    return rows.filter((row) => !q || `${row.ticker} ${row.name || ""} ${row.sector || ""}`.toLowerCase().includes(q));
  }, [rows, search]);

  const counts = filtered.reduce((acc, row) => {
    const key = row.risk_level || "MEDIUM";
    acc[key] = (acc[key] || 0) + 1;
    return acc;
  }, { LOW: 0, MEDIUM: 0, HIGH: 0 });

  if (loading) return <div className="h-full flex items-center justify-center gap-3"><Loader2 size={22} className="animate-spin text-[var(--accent)]" /><span className="text-[12px] text-[var(--text-muted)]">Checking market risk…</span></div>;

  return (
    <div className="flex-1 overflow-y-auto w-full p-4 md:p-6 lg:p-8 max-w-[1440px] mx-auto animate-fade-in flex flex-col gap-6">
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div><div className="flex items-center gap-3"><Shield size={22} className="text-[var(--accent)]" /><h1 className="heading-1">Risk Dynamics</h1></div><p className="text-[13px] text-[var(--text-muted)] mt-2 max-w-2xl">See which tracked assets currently carry more volatility, drawdown and market-sensitivity risk. Risk is shown separately from the AI prediction so a strong prediction never hides a dangerous setup.</p></div>
        <div className="relative w-full md:w-[300px]"><Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-muted)]" /><input className="input-standard pl-9" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search asset" /></div>
      </div>

      {error && <div className="surface-card p-4 text-[12px] text-[var(--negative)]">{error}</div>}

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">{Object.entries(tone).map(([level, meta]) => { const Icon = meta.icon; return <div key={level} className="surface-card p-5"><div className="flex items-center justify-between"><Icon size={17} style={{ color: meta.color }} /><span className="text-small-caps">{meta.label}</span></div><div className="text-2xl font-mono font-bold text-white mt-4">{counts[level] || 0}</div><p className="text-[10px] text-[var(--text-muted)] mt-1">tracked assets</p></div>; })}</div>

      <div className="grid grid-cols-1 xl:grid-cols-[1fr_380px] gap-6">
        <section className="surface-card overflow-hidden">
          <div className="overflow-x-auto"><table className="table-standard min-w-[780px]"><thead><tr><th>Asset</th><th>Risk</th><th>AI view</th><th className="text-right">Confidence</th><th className="text-right">Current move</th><th>Main driver</th></tr></thead><tbody>{filtered.map((row) => {
            const level = row.risk_level || "MEDIUM";
            const meta = tone[level] || tone.MEDIUM;
            return <tr key={row.ticker} onClick={() => openRisk(row.ticker)} className="cursor-pointer hover:bg-white/[0.025]"><td><div className="font-semibold text-white">{row.ticker}</div><div className="text-[9px] text-[var(--text-muted)]">{row.sector || row.name || "Market asset"}</div></td><td><span className="surface-badge" style={{ color: meta.color }}>{meta.label}</span></td><td><span className="surface-badge">{row.recommendation || "HOLD"}</span></td><td className="text-right font-mono">{Number(row.confidence_score || 0).toFixed(0)}%</td><td className="text-right font-mono" style={{ color: Number(row.chg || 0) >= 0 ? "var(--positive)" : "var(--negative)" }}>{Number(row.chg || 0) >= 0 ? "+" : ""}{Number(row.chg || 0).toFixed(2)}%</td><td className="text-[10px] text-[var(--text-muted)] capitalize">{String(row.primary_driver || "technical").replace(/_/g, " ")}</td></tr>;
          })}</tbody></table></div>
        </section>

        <aside className="surface-card p-5 h-fit">
          {!selected ? <div className="py-10 text-center"><Shield size={24} className="mx-auto text-[var(--text-muted)] mb-3" /><p className="text-[11px] text-[var(--text-muted)]">Select an asset to understand its main risk factors.</p></div> : !detail ? <div className="py-10 flex justify-center"><Loader2 size={20} className="animate-spin text-[var(--accent)]" /></div> : (
            <div><div className="flex items-center justify-between gap-3"><div><div className="text-xl font-bold text-white">{detail.ticker}</div><div className="text-[10px] text-[var(--text-muted)] mt-1">{detail.name || detail.ticker}</div></div><span className="surface-badge">{detail.overall_risk || "MEDIUM"}</span></div><div className="grid grid-cols-2 gap-3 mt-5"><Metric label="Beta" value={detail.metrics?.beta ?? "—"} /><Metric label="Volatility" value={detail.metrics?.volatility || "—"} /><Metric label="Daily VaR" value={detail.metrics?.var_95 || "—"} /><Metric label="Drawdown est." value={detail.metrics?.max_drawdown_estimate || "—"} /></div><div className="mt-5"><div className="text-[10px] font-semibold text-white mb-2">What this means</div><div className="space-y-2">{(detail.risk_factors || []).map((factor, index) => <div key={index} className="text-[10px] text-[var(--text-muted)] leading-relaxed border-l border-[var(--border-color)] pl-3">{factor}</div>)}</div></div></div>
          )}
        </aside>
      </div>

      <div className="surface-card p-4 flex items-start gap-3"><AlertTriangle size={15} className="text-[var(--warning)] mt-0.5 shrink-0" /><p className="text-[11px] text-[var(--text-muted)] leading-relaxed">Risk labels summarize historical/current behavior; they cannot predict every future loss. Real trading still uses hard position, daily-loss and protective-order limits.</p></div>
    </div>
  );
}

function Metric({ label, value }) { return <div className="rounded-[var(--radius-md)] border border-[var(--border-color)] bg-[#171b22] p-3"><div className="text-[9px] uppercase tracking-wider text-[var(--text-muted)]">{label}</div><div className="text-[12px] text-white font-semibold mt-1">{value}</div></div>; }
