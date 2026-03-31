import React, { useState, useEffect } from "react";
import { PieChart, Loader2, TrendingUp, TrendingDown, BarChart3, ShieldCheck, Shield, AlertTriangle } from "lucide-react";

import { API_BASE } from "../constants/config";

const SECTOR_COLORS = [
  "#6366f1", "#a855f7", "#ec4899", "#ef4444", "#f97316",
  "#eab308", "#22c55e", "#14b8a6", "#06b6d4", "#3b82f6",
  "#8b5cf6", "#d946ef", "#f43f5e", "#fb923c", "#84cc16",
];

function DonutChart({ sectors }) {
  const total = sectors.reduce((s, x) => s + x.allocation_pct, 0) || 1;
  let cumAngle = 0;
  const size = 200;
  const cx = size / 2, cy = size / 2, r = 70, thickness = 22;

  const arcs = sectors.slice(0, 10).map((s, i) => {
    const pct = s.allocation_pct / total;
    const startAngle = cumAngle;
    cumAngle += pct * 360;
    const endAngle = cumAngle;

    const startRad = (startAngle - 90) * (Math.PI / 180);
    const endRad = (endAngle - 90) * (Math.PI / 180);
    const outerR = r;
    const innerR = r - thickness;

    const largeArc = pct > 0.5 ? 1 : 0;

    const x1 = cx + outerR * Math.cos(startRad);
    const y1 = cy + outerR * Math.sin(startRad);
    const x2 = cx + outerR * Math.cos(endRad);
    const y2 = cy + outerR * Math.sin(endRad);
    const x3 = cx + innerR * Math.cos(endRad);
    const y3 = cy + innerR * Math.sin(endRad);
    const x4 = cx + innerR * Math.cos(startRad);
    const y4 = cy + innerR * Math.sin(startRad);

    const d = `M ${x1} ${y1} A ${outerR} ${outerR} 0 ${largeArc} 1 ${x2} ${y2} L ${x3} ${y3} A ${innerR} ${innerR} 0 ${largeArc} 0 ${x4} ${y4} Z`;
    const color = SECTOR_COLORS[i % SECTOR_COLORS.length];

    return <path key={i} d={d} fill={color} opacity={0.85} className="hover:opacity-100 transition-opacity cursor-pointer">
      <title>{s.sector}: {s.allocation_pct}%</title>
    </path>;
  });

  return (
    <svg width={size} height={size} className="drop-shadow-lg">
      {arcs}
      <text x={cx} y={cy - 6} textAnchor="middle" className="text-[10px] font-black fill-slate-400 uppercase tracking-widest">Sectors</text>
      <text x={cx} y={cy + 14} textAnchor="middle" className="text-[18px] font-black fill-white font-mono">{sectors.length}</text>
    </svg>
  );
}

const RISK_ICONS = { LOW: ShieldCheck, MEDIUM: Shield, HIGH: AlertTriangle };
const RISK_COLORS = { LOW: "#22c55e", MEDIUM: "#fbbf24", HIGH: "#ef4444" };

export default function PortfolioInsightsView() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/portfolio/insights`);
        const d = await res.json();
        setData(d);
      } catch (err) {
        console.error("Portfolio insights fetch failed:", err);
      }
      setLoading(false);
    };
    fetchData();
  }, []);

  if (loading) return (
    <div className="flex-1 flex items-center justify-center">
      <div className="text-center space-y-3">
        <Loader2 size={32} className="text-emerald-400 animate-spin mx-auto" />
        <p className="text-xs font-mono text-slate-500 tracking-widest">COMPUTING PORTFOLIO METRICS...</p>
      </div>
    </div>
  );

  if (!data) return null;

  const { sectors, risk_distribution, aggregate, total_assets } = data;
  const bullPct = total_assets ? Math.round((aggregate.bullish_count / total_assets) * 100) : 0;

  return (
    <div className="flex-1 p-8 overflow-y-auto no-scrollbar animate-fade-in">
      <div className="max-w-6xl mx-auto space-y-8">
        {/* Header */}
        <div className="flex items-center gap-4 border-b border-white/5 pb-6">
          <div className="p-3 bg-emerald-500/10 rounded-2xl border border-emerald-500/30 shadow-lg">
            <PieChart size={24} className="text-emerald-400" />
          </div>
          <div>
            <h2 className="text-3xl font-black text-white tracking-tighter uppercase">Portfolio Insights</h2>
            <p className="text-[10px] font-mono text-slate-500 tracking-[0.3em] uppercase mt-1">
              {total_assets} ASSETS • {sectors.length} SECTORS • BULL/BEAR {aggregate.bull_bear_ratio}
            </p>
          </div>
        </div>

        {/* Top Stats */}
        <div className="grid grid-cols-4 gap-4">
          <div className="clay-card p-5 text-center">
            <div className="text-[9px] font-black text-slate-500 uppercase tracking-widest mb-2">Total Assets</div>
            <div className="text-3xl font-black text-white font-mono">{total_assets}</div>
          </div>
          <div className="clay-card p-5 text-center">
            <div className="text-[9px] font-black text-slate-500 uppercase tracking-widest mb-2">Avg Change</div>
            <div className="text-3xl font-black font-mono" style={{ color: aggregate.avg_change_pct >= 0 ? "#22c55e" : "#ef4444" }}>
              {aggregate.avg_change_pct >= 0 ? "+" : ""}{aggregate.avg_change_pct}%
            </div>
          </div>
          <div className="clay-card p-5 text-center">
            <div className="text-[9px] font-black text-slate-500 uppercase tracking-widest mb-2">Bullish</div>
            <div className="flex items-center justify-center gap-2">
              <TrendingUp size={20} className="text-green-400" />
              <span className="text-3xl font-black text-green-400 font-mono">{aggregate.bullish_count}</span>
            </div>
          </div>
          <div className="clay-card p-5 text-center">
            <div className="text-[9px] font-black text-slate-500 uppercase tracking-widest mb-2">Bearish</div>
            <div className="flex items-center justify-center gap-2">
              <TrendingDown size={20} className="text-red-400" />
              <span className="text-3xl font-black text-red-400 font-mono">{aggregate.bearish_count}</span>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-8">
          {/* Donut + Legend */}
          <div className="clay-card p-6 space-y-4">
            <h3 className="text-[10px] font-black text-slate-400 uppercase tracking-[0.25em]">Sector Allocation</h3>
            <div className="flex items-center gap-8">
              <DonutChart sectors={sectors} />
              <div className="space-y-2 flex-1">
                {sectors.slice(0, 8).map((s, i) => (
                  <div key={s.sector} className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <div className="w-2.5 h-2.5 rounded-sm" style={{ background: SECTOR_COLORS[i % SECTOR_COLORS.length] }} />
                      <span className="text-[10px] text-slate-400 truncate max-w-[140px]">{s.sector}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-mono font-bold text-white">{s.allocation_pct}%</span>
                      <span className="text-[9px] text-slate-600 font-mono">{s.count}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Risk Distribution */}
          <div className="clay-card p-6 space-y-4">
            <h3 className="text-[10px] font-black text-slate-400 uppercase tracking-[0.25em]">Risk Distribution</h3>
            <div className="space-y-4 pt-4">
              {["LOW", "MEDIUM", "HIGH"].map(level => {
                const count = risk_distribution[level] || 0;
                const pct = total_assets ? Math.round((count / total_assets) * 100) : 0;
                const color = RISK_COLORS[level];
                const Icon = RISK_ICONS[level];
                return (
                  <div key={level} className="space-y-2">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Icon size={14} style={{ color }} />
                        <span className="text-[10px] font-black tracking-widest uppercase" style={{ color }}>{level}</span>
                      </div>
                      <span className="text-sm font-mono font-black" style={{ color }}>{count} <span className="text-[9px] text-slate-600">({pct}%)</span></span>
                    </div>
                    <div className="h-2 bg-black/30 rounded-full overflow-hidden">
                      <div className="h-full rounded-full transition-all duration-1000" style={{ width: `${pct}%`, background: color }} />
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Bull / Bear gauge */}
            <div className="pt-4 border-t border-white/5 space-y-2">
              <div className="text-[9px] font-black text-slate-500 uppercase tracking-widest">Market Sentiment</div>
              <div className="h-3 bg-black/30 rounded-full overflow-hidden flex">
                <div className="h-full transition-all duration-1000 bg-green-500" style={{ width: `${bullPct}%` }} />
                <div className="h-full transition-all duration-1000 bg-red-500" style={{ width: `${100 - bullPct}%` }} />
              </div>
              <div className="flex justify-between text-[9px] font-mono">
                <span className="text-green-400">{bullPct}% BULL</span>
                <span className="text-red-400">{100 - bullPct}% BEAR</span>
              </div>
            </div>
          </div>
        </div>

        {/* Top Holdings */}
        <div className="clay-card p-6 space-y-4">
          <h3 className="text-[10px] font-black text-slate-400 uppercase tracking-[0.25em]">Top Sector Holdings</h3>
          <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
            {sectors.slice(0, 6).map((s, i) => (
              <div key={s.sector} className="p-4 rounded-xl bg-white/[0.02] border border-white/5 space-y-2">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-sm" style={{ background: SECTOR_COLORS[i % SECTOR_COLORS.length] }} />
                  <span className="text-xs font-bold text-white truncate">{s.sector}</span>
                </div>
                <div className="flex flex-wrap gap-1">
                  {s.tickers.map(t => (
                    <span key={t} className="px-1.5 py-0.5 rounded text-[8px] font-mono font-bold text-slate-400 bg-white/5 border border-white/5">
                      {t}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
