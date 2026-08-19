import React, { useEffect, useMemo, useState } from "react";
import { ArrowDown, ArrowUp, Loader2, Search, Shield, Sparkles, Target } from "lucide-react";
import { API_BASE } from "../api_config";

export default function PredictionTableView({ onSelect }) {
  const [rows, setRows] = useState([]);
  const [summary, setSummary] = useState("");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/customer/daily-brief?limit=30`);
      if (!response.ok) throw new Error("Predictions are temporarily unavailable");
      const data = await response.json();
      const combined = [...(data.opportunities || []), ...(data.top_movers || [])];
      const seen = new Set();
      setRows(combined.filter((item) => {
        if (!item?.ticker || seen.has(item.ticker)) return false;
        seen.add(item.ticker);
        return true;
      }));
      setSummary(data.summary || "");
    } catch (e) {
      setError(e.message || "Predictions are unavailable");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    const timer = setInterval(load, 60000);
    return () => clearInterval(timer);
  }, []);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return rows.filter((row) => !q || `${row.ticker} ${row.name || ""} ${row.sector || ""}`.toLowerCase().includes(q));
  }, [rows, search]);

  if (loading) return <div className="h-full flex items-center justify-center gap-3"><Loader2 size={22} className="animate-spin text-[var(--accent)]" /><span className="text-[12px] text-[var(--text-muted)]">Preparing today’s prediction view…</span></div>;

  return (
    <div className="flex-1 overflow-y-auto w-full p-4 md:p-6 lg:p-8 max-w-[1440px] mx-auto animate-fade-in flex flex-col gap-6">
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <div className="flex items-center gap-3"><Sparkles size={21} className="text-[var(--accent)]" /><h1 className="heading-1">Stock predictions</h1></div>
          <p className="text-[13px] text-[var(--text-muted)] mt-2 max-w-2xl">{summary || "Current AI views based on available price history, news, sentiment and risk signals."}</p>
        </div>
        <div className="relative w-full md:w-[300px]">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-muted)]" />
          <input className="input-standard pl-9" placeholder="Search asset or sector" value={search} onChange={(e) => setSearch(e.target.value)} />
        </div>
      </div>

      {error && <div className="surface-card p-4 text-[12px] text-[var(--negative)]">{error}</div>}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <InfoCard icon={Target} label="How to use this" text="Open an asset to see what happened, why it moved, all agent views, evidence and risks before acting." />
        <InfoCard icon={Shield} label="Risk matters" text="A BUY view is not a guarantee. Confidence and risk should be read together, not separately." />
        <InfoCard icon={Sparkles} label="Always updating" text="AITradra refreshes market/news data in the background and re-scores stale intelligence." />
      </div>

      <section className="surface-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="table-standard min-w-[940px]">
            <thead>
              <tr>
                <th>Asset</th><th className="text-right">Current price</th><th className="text-right">Today</th><th>AI view</th><th className="text-right">Confidence</th><th className="text-right">Model target</th><th>Risk</th><th>Main reason</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((row) => {
                const change = Number(row.chg || 0);
                const direction = row.prediction_direction || "SIDEWAYS";
                const recommendation = row.recommendation || "HOLD";
                return (
                  <tr key={row.ticker} onClick={() => onSelect?.(row.ticker)} className="cursor-pointer hover:bg-white/[0.025]">
                    <td><div className="font-semibold text-white">{row.ticker}</div><div className="text-[10px] text-[var(--text-muted)] mt-0.5">{row.sector || row.name || "Market asset"}</div></td>
                    <td className="text-right font-mono text-white">${Number(row.current_price || 0).toFixed(2)}</td>
                    <td className="text-right"><span className="inline-flex items-center gap-1 font-mono" style={{ color: change >= 0 ? "var(--positive)" : "var(--negative)" }}>{change >= 0 ? <ArrowUp size={12} /> : <ArrowDown size={12} />}{change >= 0 ? "+" : ""}{change.toFixed(2)}%</span></td>
                    <td><span className={`surface-badge ${recommendation === "BUY" ? "text-[var(--positive)]" : recommendation === "AVOID" ? "text-[var(--negative)]" : "text-amber-300"}`}>{recommendation}</span><div className="text-[9px] text-[var(--text-muted)] mt-1">{direction}</div></td>
                    <td className="text-right font-mono">{Number(row.confidence_score || 0).toFixed(0)}%</td>
                    <td className="text-right font-mono">${Number(row.predicted_price || row.current_price || 0).toFixed(2)}</td>
                    <td><span className={`surface-badge ${row.risk_level === "HIGH" ? "text-[var(--negative)]" : row.risk_level === "LOW" ? "text-[var(--positive)]" : "text-amber-300"}`}>{row.risk_level || "MEDIUM"}</span></td>
                    <td className="max-w-[280px]"><div className="text-[11px] text-white capitalize">{String(row.primary_driver || "technical").replace(/_/g, " ")}</div><div className="text-[9px] text-[var(--text-muted)] line-clamp-2 mt-1">{row.reasoning_summary || "Open to see the supporting evidence."}</div></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {!filtered.length && <div className="p-10 text-center text-[12px] text-[var(--text-muted)]">No assets match your search.</div>}
        </div>
      </section>
    </div>
  );
}

function InfoCard({ icon: Icon, label, text }) {
  return <div className="surface-card p-4 flex items-start gap-3"><Icon size={16} className="text-[var(--accent)] mt-0.5 shrink-0" /><div><div className="text-[11px] font-semibold text-white">{label}</div><p className="text-[10px] text-[var(--text-muted)] leading-relaxed mt-1">{text}</p></div></div>;
}
