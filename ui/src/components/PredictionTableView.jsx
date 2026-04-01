import React, { useState, useEffect } from "react";
import { TrendingUp, TrendingDown, Minus, ArrowUpDown, Loader2, BarChart3, Search, Activity, Cpu } from "lucide-react";

import { API_BASE } from "../api_config";

const DIRECTION_CONFIG = {
  UP:       { icon: TrendingUp,   color: "var(--accent-positive)", label: "BULLISH" },
  DOWN:     { icon: TrendingDown, color: "var(--accent-negative)", label: "BEARISH" },
  SIDEWAYS: { icon: Minus,        color: "#fbbf24", label: "NEUTRAL" },
};

const RISK_COLORS = {
  LOW:    { color: "var(--accent-positive)" },
  MEDIUM: { color: "#fbbf24" },
  HIGH:   { color: "var(--accent-negative)" },
};

const DRIVER_COLORS = {
  news:      "#a855f7",
  technical: "var(--accent-indigo)",
  macro:     "#10b981",
  sentiment: "#fbbf24",
};

function ConfidenceRing({ value, size = 32 }) {
  const r = (size - 4) / 2;
  const circ = 2 * Math.PI * r;
  const offset = circ - (value / 100) * circ;
  const color = value >= 70 ? "var(--accent-positive)" : value >= 45 ? "#fbbf24" : "var(--accent-negative)";
  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="transform -rotate-90">
        <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="rgba(255,255,255,0.03)" strokeWidth="2.5" />
        <circle cx={size/2} cy={size/2} r={r} fill="none" stroke={color} strokeWidth="2.5"
          strokeDasharray={circ} strokeDashoffset={offset} strokeLinecap="round"
          style={{ transition: "stroke-dashoffset 1s ease-out", opacity: 0.7 }} />
      </svg>
      <span className="absolute inset-0 flex items-center justify-center text-[8px] font-bold font-mono" style={{ color }}>
        {value}
      </span>
    </div>
  );
}

export default function PredictionTableView({ onSelect }) {
  const [predictions, setPredictions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [sortCol, setSortCol] = useState("confidence_score");
  const [sortDir, setSortDir] = useState("desc");
  const [search, setSearch] = useState("");

  useEffect(() => {
    const fetchPredictions = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/market/predictions`);
        const data = await res.json();
        setPredictions(data.predictions || []);
      } catch (err) {
        console.error("Prediction fetch failed:", err);
      }
      setLoading(false);
    };
    fetchPredictions();
    const interval = setInterval(fetchPredictions, 60000);
    return () => clearInterval(interval);
  }, []);

  const handleSort = (col) => {
    if (sortCol === col) setSortDir(d => d === "asc" ? "desc" : "asc");
    else { setSortCol(col); setSortDir("desc"); }
  };

  const filtered = predictions.filter(p =>
    p.ticker.toLowerCase().includes(search.toLowerCase()) ||
    (p.name || "").toLowerCase().includes(search.toLowerCase())
  );

  const sorted = [...filtered].sort((a, b) => {
    const va = a[sortCol] ?? 0;
    const vb = b[sortCol] ?? 0;
    if (typeof va === "string") return sortDir === "asc" ? va.localeCompare(vb) : vb.localeCompare(va);
    return sortDir === "asc" ? va - vb : vb - va;
  });

  const SortHeader = ({ col, label, className = "" }) => (
    <th onClick={() => handleSort(col)}
      className={`px-4 py-4 text-left cursor-pointer group select-none ${className} border-b border-white/[0.06]`}>
      <div className="flex items-center gap-2">
        <span className="text-[9px] font-bold uppercase tracking-[0.2em] text-slate-500 group-hover:text-indigo-400 transition-colors">
          {label}
        </span>
        <ArrowUpDown size={10} className={`transition-colors ${sortCol === col ? "text-indigo-400" : "text-slate-800"}`} />
      </div>
    </th>
  );

  if (loading) return (
    <div className="flex-1 flex items-center justify-center institutional-bg">
      <div className="text-center space-y-4">
        <Loader2 size={24} className="text-indigo-500 animate-spin mx-auto" />
        <p className="text-[10px] font-mono text-slate-500 tracking-[0.3em] uppercase animate-pulse">Ingesting Synapse Data...</p>
      </div>
    </div>
  );

  return (
    <div className="flex-1 p-8 overflow-y-auto no-scrollbar animate-fade-in institutional-bg">
      <div className="max-w-7xl mx-auto space-y-10">
        {/* Institutional Header */}
        <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-6 border-b border-white/[0.08] pb-8">
          <div className="flex items-center gap-5">
            <div className="w-12 h-12 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center shadow-lg">
              <BarChart3 size={24} className="text-indigo-400" />
            </div>
            <div className="flex flex-col gap-1">
              <h1 className="text-[24px] font-bold text-white tracking-tight uppercase leading-none">Omni Prediction Matrix</h1>
              <p className="text-[10px] font-mono text-slate-500 tracking-[0.4em] uppercase">
                {predictions.length} ACTIVE_NODES // AX-V4_CORE // SIG_CONSOL_85%
              </p>
            </div>
          </div>
          
          <div className="relative group min-w-[320px]">
             <Search size={14} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-600 group-focus-within:text-indigo-500 transition-colors" />
             <input value={search} onChange={e => setSearch(e.target.value)}
              placeholder="SEARCH_NODE_IDENTIFIER..."
              className="w-full bg-white/[0.02] border border-white/[0.08] rounded-xl pl-12 pr-4 py-3 text-[11px] font-mono tracking-widest text-white focus:outline-none focus:border-indigo-500/40 transition-all placeholder:text-slate-800" />
          </div>
        </div>

        {/* Precision Table */}
        <div className="glass-card overflow-hidden border border-white/[0.06]">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-white/[0.02]">
                  <SortHeader col="ticker" label="Asset" />
                  <SortHeader col="current_price" label="Price" />
                  <SortHeader col="prediction_direction" label="Bias" />
                  <SortHeader col="predicted_price" label="Target" />
                  <SortHeader col="confidence_score" label="Conf" />
                  <SortHeader col="expected_move_percent" label="Delta" />
                  <SortHeader col="risk_level" label="Risk" />
                  <th className="px-4 py-4 border-b border-white/[0.06]">
                    <span className="text-[9px] font-bold uppercase tracking-[0.2em] text-slate-500">Heuristics</span>
                  </th>
                  <SortHeader col="primary_driver" label="Driver" />
                </tr>
              </thead>
              <tbody>
                {sorted.map((p, i) => {
                  const dir = DIRECTION_CONFIG[p.prediction_direction] || DIRECTION_CONFIG.SIDEWAYS;
                  const riskStyle = RISK_COLORS[p.risk_level] || RISK_COLORS.MEDIUM;
                  const DirIcon = dir.icon;
                  const driverColor = DRIVER_COLORS[p.primary_driver] || "#94a3b8";
                  return (
                    <tr key={p.ticker} onClick={() => onSelect && onSelect(p.ticker)}
                      className="border-b border-white/[0.03] hover:bg-white/[0.02] cursor-pointer transition-all duration-120 group">
                      {/* Ticker */}
                      <td className="px-4 py-5">
                        <div className="flex items-center gap-4">
                          <div className="w-9 h-9 rounded-lg flex items-center justify-center text-xs font-bold border transition-all duration-120 group-hover:scale-105"
                            style={{ background: `${dir.color}08`, borderColor: `${dir.color}15`, color: dir.color }}>
                            {p.ticker[0]}
                          </div>
                          <div className="flex flex-col gap-0.5">
                            <span className="font-bold text-white text-[14px] leading-none group-hover:text-indigo-400 transition-colors uppercase tracking-tight">{p.ticker}</span>
                            <span className="text-[8px] text-slate-600 font-bold uppercase tracking-widest truncate max-w-[80px]">{p.name}</span>
                          </div>
                        </div>
                      </td>
                      {/* Price */}
                      <td className="px-4 py-5">
                        <span className="font-mono text-[13px] font-bold text-white tabular-nums">
                          ${p.current_price?.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                        </span>
                      </td>
                      {/* Direction */}
                      <td className="px-4 py-5">
                        <div className="flex items-center gap-2 px-2.5 py-1 rounded-md w-fit border"
                          style={{ background: `${dir.color}08`, borderColor: `${dir.color}15` }}>
                          <DirIcon size={10} style={{ color: dir.color }} />
                          <span className="text-[9px] font-bold tracking-widest uppercase" style={{ color: dir.color }}>{dir.label}</span>
                        </div>
                      </td>
                      {/* Target Price */}
                      <td className="px-4 py-5">
                        <span className="font-mono text-[13px] font-bold tabular-nums" style={{ color: dir.color }}>
                          ${p.predicted_price?.toFixed(2)}
                        </span>
                      </td>
                      {/* Confidence */}
                      <td className="px-4 py-5">
                        <ConfidenceRing value={p.confidence_score} />
                      </td>
                      {/* Expected Move */}
                      <td className="px-4 py-5">
                        <span className="font-mono text-[13px] font-bold tabular-nums" style={{ color: dir.color }}>
                          {p.prediction_direction === "DOWN" ? "-" : "+"}{p.expected_move_percent}%
                        </span>
                      </td>
                      {/* Risk Level */}
                      <td className="px-4 py-5">
                        <span className="px-2 py-0.5 rounded-md text-[9px] font-bold tracking-widest uppercase border"
                          style={{ background: `${riskStyle.color}08`, borderColor: `${riskStyle.color}15`, color: riskStyle.color }}>
                          {p.risk_level}
                        </span>
                      </td>
                      {/* Reasoning Summary */}
                      <td className="px-4 py-5 max-w-[240px]">
                        <p className="text-[10px] text-slate-500 leading-relaxed line-clamp-1 italic">"{p.reasoning_summary}"</p>
                      </td>
                      {/* Driver Indicator */}
                      <td className="px-4 py-5">
                        <div className="flex items-center gap-2 text-slate-400 group-hover:text-white transition-colors">
                           <div className="w-1.5 h-1.5 rounded-full" style={{ background: driverColor }} />
                           <span className="text-[9px] font-bold tracking-widest uppercase">{p.primary_driver}</span>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {filtered.length === 0 && (
          <div className="flex flex-col items-center justify-center py-20 gap-4 opacity-40">
            <Activity size={32} className="text-slate-800 animate-pulse" />
            <p className="text-[10px] font-mono font-bold text-slate-700 uppercase tracking-widest">No nodes match current filter</p>
          </div>
        )}
      </div>
    </div>
  );
}
