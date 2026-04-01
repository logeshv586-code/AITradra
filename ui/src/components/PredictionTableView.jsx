import React, { useState, useEffect } from "react";
import { TrendingUp, TrendingDown, Minus, ArrowUpDown, Loader2, BarChart3, Search } from "lucide-react";

import { API_BASE } from "../api_config";

const DIRECTION_CONFIG = {
  UP:       { icon: TrendingUp,   color: "#22c55e", bg: "rgba(34,197,94,0.10)",  border: "rgba(34,197,94,0.25)", label: "BULLISH" },
  DOWN:     { icon: TrendingDown, color: "#ef4444", bg: "rgba(239,68,68,0.10)",  border: "rgba(239,68,68,0.25)", label: "BEARISH" },
  SIDEWAYS: { icon: Minus,        color: "#fbbf24", bg: "rgba(251,191,36,0.10)", border: "rgba(251,191,36,0.25)", label: "NEUTRAL" },
};

const RISK_COLORS = {
  LOW:    { color: "#22c55e", bg: "rgba(34,197,94,0.12)" },
  MEDIUM: { color: "#fbbf24", bg: "rgba(251,191,36,0.12)" },
  HIGH:   { color: "#ef4444", bg: "rgba(239,68,68,0.12)" },
};

const DRIVER_COLORS = {
  news:      "#a855f7",
  technical: "#00f0ff",
  macro:     "#22c55e",
  sentiment: "#fbbf24",
};

function ConfidenceRing({ value, size = 36 }) {
  const r = (size - 4) / 2;
  const circ = 2 * Math.PI * r;
  const offset = circ - (value / 100) * circ;
  const color = value >= 70 ? "#22c55e" : value >= 45 ? "#fbbf24" : "#ef4444";
  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="transform -rotate-90">
        <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="3" />
        <circle cx={size/2} cy={size/2} r={r} fill="none" stroke={color} strokeWidth="3"
          strokeDasharray={circ} strokeDashoffset={offset} strokeLinecap="round"
          style={{ transition: "stroke-dashoffset 1s ease-out" }} />
      </svg>
      <span className="absolute inset-0 flex items-center justify-center text-[9px] font-black font-mono" style={{ color }}>
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
      className={`px-3 py-3 text-left cursor-pointer group select-none ${className}`}>
      <div className="flex items-center gap-1.5">
        <span className="text-[9px] font-black uppercase tracking-[0.15em] text-slate-500 group-hover:text-indigo-400 transition-colors">
          {label}
        </span>
        <ArrowUpDown size={10} className={`transition-colors ${sortCol === col ? "text-indigo-400" : "text-slate-700"}`} />
      </div>
    </th>
  );

  if (loading) return (
    <div className="flex-1 flex items-center justify-center">
      <div className="text-center space-y-3">
        <Loader2 size={32} className="text-indigo-400 animate-spin mx-auto" />
        <p className="text-xs font-mono text-slate-500 tracking-widest">COMPUTING PREDICTIONS...</p>
      </div>
    </div>
  );

  return (
    <div className="flex-1 p-8 overflow-y-auto no-scrollbar animate-fade-in">
      <div className="max-w-7xl mx-auto space-y-8">
        {/* Header */}
        <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-6 border-b border-white/5 pb-6">
          <div className="space-y-2">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-indigo-500/10 rounded-2xl border border-indigo-500/30 shadow-lg">
                <BarChart3 size={24} className="text-indigo-400" />
              </div>
              <div>
                <h2 className="text-3xl font-black text-white tracking-tighter uppercase">Prediction Table</h2>
                <p className="text-[10px] font-mono text-slate-500 tracking-[0.3em] uppercase mt-1">
                  OMNI-AXIOM INTELLIGENCE • {predictions.length} ASSETS • MAX CONFIDENCE 85%
                </p>
              </div>
            </div>
          </div>
          <div className="relative group min-w-[280px]">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500 group-focus-within:text-indigo-400 transition-colors" />
            <input value={search} onChange={e => setSearch(e.target.value)}
              placeholder="FILTER PREDICTIONS..."
              className="clay-input pl-9 pr-4 py-3 w-full text-xs font-mono tracking-wider" />
          </div>
        </div>

        {/* Table */}
        <div className="clay-card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-white/5" style={{ background: "linear-gradient(135deg, rgba(99,102,241,0.08), rgba(0,240,255,0.04))" }}>
                  <SortHeader col="ticker" label="Asset" />
                  <SortHeader col="current_price" label="Price" />
                  <SortHeader col="prediction_direction" label="Direction" />
                  <SortHeader col="predicted_price" label="Predicted" />
                  <SortHeader col="confidence_score" label="Confidence" />
                  <SortHeader col="expected_move_percent" label="Exp. Move" />
                  <SortHeader col="risk_level" label="Risk" />
                  <th className="px-3 py-3">
                    <span className="text-[9px] font-black uppercase tracking-[0.15em] text-slate-500">Reasoning</span>
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
                      className="border-b border-white/[0.03] hover:bg-white/[0.03] cursor-pointer transition-colors group"
                      style={{ animationDelay: `${i * 30}ms` }}>
                      {/* Ticker */}
                      <td className="px-3 py-3">
                        <div className="flex items-center gap-3">
                          <div className="w-9 h-9 rounded-xl flex items-center justify-center text-sm font-black"
                            style={{ background: dir.bg, border: `1px solid ${dir.border}`, color: dir.color }}>
                            {p.ticker[0]}
                          </div>
                          <div>
                            <div className="font-mono font-bold text-white text-sm group-hover:text-indigo-400 transition-colors">{p.ticker}</div>
                            <div className="text-[9px] text-slate-600 truncate max-w-[100px]">{p.name}</div>
                          </div>
                        </div>
                      </td>
                      {/* Price */}
                      <td className="px-3 py-3">
                        <span className="font-mono text-sm font-bold text-white">
                          ${p.current_price?.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                        </span>
                      </td>
                      {/* Direction */}
                      <td className="px-3 py-3">
                        <div className="flex items-center gap-1.5 px-2 py-1 rounded-lg w-fit"
                          style={{ background: dir.bg, border: `1px solid ${dir.border}` }}>
                          <DirIcon size={12} style={{ color: dir.color }} />
                          <span className="text-[9px] font-black tracking-wider" style={{ color: dir.color }}>{dir.label}</span>
                        </div>
                      </td>
                      {/* Predicted Price */}
                      <td className="px-3 py-3">
                        <span className="font-mono text-sm" style={{ color: dir.color }}>
                          ${p.predicted_price?.toFixed(2)}
                        </span>
                      </td>
                      {/* Confidence */}
                      <td className="px-3 py-3">
                        <ConfidenceRing value={p.confidence_score} size={34} />
                      </td>
                      {/* Expected Move */}
                      <td className="px-3 py-3">
                        <span className="font-mono text-xs font-bold" style={{ color: dir.color }}>
                          {p.prediction_direction === "DOWN" ? "-" : "+"}{p.expected_move_percent}%
                        </span>
                      </td>
                      {/* Risk Level */}
                      <td className="px-3 py-3">
                        <span className="px-2 py-0.5 rounded-md text-[9px] font-black tracking-wider"
                          style={{ background: riskStyle.bg, color: riskStyle.color }}>
                          {p.risk_level}
                        </span>
                      </td>
                      {/* Reasoning */}
                      <td className="px-3 py-3 max-w-[200px]">
                        <p className="text-[10px] text-slate-400 leading-snug line-clamp-2">{p.reasoning_summary}</p>
                      </td>
                      {/* Driver */}
                      <td className="px-3 py-3">
                        <span className="px-2 py-0.5 rounded-md text-[8px] font-black tracking-widest uppercase"
                          style={{ background: `${driverColor}18`, color: driverColor, border: `1px solid ${driverColor}30` }}>
                          {p.primary_driver}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
