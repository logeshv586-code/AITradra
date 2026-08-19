import React, { useEffect, useMemo, useState } from "react";
import { ArrowDown, ArrowUp, BarChart2, Loader2, RefreshCcw, Shield } from "lucide-react";
import { API_BASE } from "../api_config";

export default function TrendingStocksView({ stocks: liveStocks, onSelect }) {
  const [rows, setRows] = useState([]);
  const [filter, setFilter] = useState("ALL");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/customer/daily-brief?limit=24`);
      if (!response.ok) throw new Error("Market pulse is temporarily unavailable");
      const payload = await response.json();
      const combined = [...(payload.top_movers || []), ...(payload.opportunities || [])];
      const seen = new Set();
      setRows(combined.filter((item) => item.ticker && !seen.has(item.ticker) && seen.add(item.ticker)));
      setError("");
    } catch (e) {
      if (liveStocks?.length) {
        setRows(liveStocks.map((item) => ({ ...item, ticker: item.ticker || item.id, current_price: item.current_price ?? item.price ?? item.px, chg: item.chg ?? item.change_pct ?? 0 })));
      } else {
        setError(e.message || "Market pulse is unavailable");
      }
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); const timer = setInterval(load, 60000); return () => clearInterval(timer); }, []);

  const filtered = useMemo(() => {
    const copy = [...rows];
    if (filter === "GAINERS") return copy.filter((row) => Number(row.chg || 0) >= 0).sort((a, b) => Number(b.chg || 0) - Number(a.chg || 0));
    if (filter === "LOSERS") return copy.filter((row) => Number(row.chg || 0) < 0).sort((a, b) => Number(a.chg || 0) - Number(b.chg || 0));
    if (filter === "BUY") return copy.filter((row) => row.recommendation === "BUY").sort((a, b) => Number(b.confidence_score || 0) - Number(a.confidence_score || 0));
    return copy;
  }, [rows, filter]);

  if (loading) return <div className="h-full flex items-center justify-center gap-3"><Loader2 size={22} className="animate-spin text-[var(--accent)]" /><span className="text-[12px] text-[var(--text-muted)]">Updating market pulse…</span></div>;

  return (
    <div className="flex-1 overflow-y-auto w-full p-4 md:p-6 lg:p-8 max-w-[1440px] mx-auto animate-fade-in flex flex-col gap-6">
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4"><div><div className="flex items-center gap-3"><BarChart2 size={21} className="text-[var(--accent)]" /><h1 className="heading-1">Market Pulse</h1></div><p className="text-[13px] text-[var(--text-muted)] mt-2">See what is moving now and which assets deserve deeper research. Cards show customer-level signals, not internal model diagnostics.</p></div><button onClick={load} className="btn-standard h-9 px-4"><RefreshCcw size={13} /> Refresh</button></div>
      <div className="toggle-group w-fit overflow-x-auto">{[["ALL", "All movers"], ["GAINERS", "Gainers"], ["LOSERS", "Losers"], ["BUY", "Buy research"]].map(([key, label]) => <button key={key} onClick={() => setFilter(key)} className={`toggle-item ${filter === key ? "active" : ""}`}>{label}</button>)}</div>
      {error && <div className="surface-card p-4 text-[12px] text-[var(--negative)]">{error}</div>}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
        {filtered.map((row) => {
          const change = Number(row.chg ?? row.change_pct ?? 0);
          const price = Number(row.current_price ?? row.price ?? row.px ?? 0);
          const up = change >= 0;
          return <button key={row.ticker || row.id} onClick={() => onSelect?.(row.ticker || row.id)} className="surface-card p-5 text-left hover:border-slate-500 transition-colors flex flex-col gap-4"><div className="flex items-start justify-between gap-3"><div><div className="text-[16px] font-bold text-white">{row.ticker || row.id}</div><div className="text-[10px] text-[var(--text-muted)] mt-1">{row.sector || row.name || "Market asset"}</div></div><span className="inline-flex items-center gap-1 font-mono text-[11px]" style={{ color: up ? "var(--positive)" : "var(--negative)" }}>{up ? <ArrowUp size={12} /> : <ArrowDown size={12} />}{up ? "+" : ""}{change.toFixed(2)}%</span></div><div className="text-2xl font-mono font-semibold text-white">${price.toFixed(2)}</div><div className="flex flex-wrap gap-2"><span className={`surface-badge ${row.recommendation === "BUY" ? "text-[var(--positive)]" : row.recommendation === "AVOID" ? "text-[var(--negative)]" : "text-amber-300"}`}>{row.recommendation || "HOLD"}</span>{row.confidence_score != null && <span className="surface-badge">{Number(row.confidence_score).toFixed(0)}% confidence</span>}{row.risk_level && <span className="surface-badge"><Shield size={10} className="inline mr-1" />{row.risk_level} risk</span>}</div><div className="border-t border-[var(--border-color)] pt-3 text-[10px] text-[var(--text-muted)] capitalize">Main reason: {String(row.primary_driver || "market movement").replace(/_/g, " ")}</div></button>;
        })}
      </div>
      {!filtered.length && <div className="surface-card p-10 text-center text-[11px] text-[var(--text-muted)]">No assets match this view yet.</div>}
    </div>
  );
}
