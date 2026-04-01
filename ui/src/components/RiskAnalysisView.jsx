import React, { useState, useEffect } from "react";
import { ShieldAlert, Activity, Loader2, AlertTriangle, Shield, ShieldCheck, ChevronRight } from "lucide-react";
import { API_BASE } from "../api_config";

const RISK_CONFIG = {
  LOW:    { color: "var(--accent-positive)", icon: ShieldCheck, label: "LOW RISK" },
  MEDIUM: { color: "var(--accent-warn)", icon: Shield,      label: "MEDIUM RISK" },
  HIGH:   { color: "var(--accent-negative)", icon: AlertTriangle, label: "HIGH RISK" },
};

function MetricBar({ label, value, max = 10, color }) {
  const pct = Math.min((parseFloat(value) / max) * 100, 100);
  return (
    <div className="space-y-1.5">
      <div className="flex justify-between items-end px-0.5">
        <span className="text-[9px] font-bold text-slate-500 uppercase tracking-widest">{label}</span>
        <span className="text-[10px] font-mono font-bold" style={{ color }}>{value}</span>
      </div>
      <div className="h-1 bg-black/40 rounded-sm overflow-hidden border border-white/[0.04]">
        <div className="h-full rounded-sm transition-all duration-700" style={{ width: `${pct}%`, background: color }} />
      </div>
    </div>
  );
}

export default function RiskAnalysisView({ onSelect }) {
  const [predictions, setPredictions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedRisk, setSelectedRisk] = useState(null);
  const [riskDetail, setRiskDetail] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/market/predictions`);
        const data = await res.json();
        setPredictions(data.predictions || []);
      } catch (err) {
        console.error("Risk data fetch failed:", err);
      }
      setLoading(false);
    };
    fetchData();
  }, []);

  const fetchRiskDetail = async (ticker) => {
    setSelectedRisk(ticker);
    setRiskDetail(null);
    try {
      const res = await fetch(`${API_BASE}/api/stock/${ticker}/risk`);
      const data = await res.json();
      setRiskDetail(data);
    } catch (err) {
      console.error("Risk detail fetch failed:", err);
    }
  };

  const riskGroups = { HIGH: [], MEDIUM: [], LOW: [] };
  predictions.forEach(p => {
    const group = riskGroups[p.risk_level] || riskGroups.MEDIUM;
    group.push(p);
  });

  if (loading) return (
    <div className="flex-1 flex items-center justify-center p-10">
      <div className="flex flex-col items-center gap-4 animate-pulse">
        <Loader2 size={24} className="text-indigo-500 animate-spin" />
        <span className="text-[10px] font-mono text-slate-500 tracking-[0.4em] uppercase">Scanning_Risk_Matrix...</span>
      </div>
    </div>
  );

  return (
    <div className="flex-1 overflow-y-auto no-scrollbar animate-fade-in page-padding">
      <div className="content-max-w space-y-6 md:space-y-10">
        
        {/* SHARP Header Alignment */}
        <div className="flex flex-col md:flex-row md:items-center gap-4 md:gap-6 border-b border-white/[0.08] pb-6 md:pb-8">
          <div className="w-11 h-11 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center shadow-sm">
            <ShieldAlert size={20} className="text-indigo-400" />
          </div>
          <div className="flex flex-col gap-0.5">
            <h1 className="text-xl md:text-2xl font-bold text-white tracking-tight uppercase leading-none">Risk Dynamics</h1>
            <p className="text-[10px] font-mono text-slate-500 tracking-[0.4em] uppercase mt-1">
              {riskGroups.HIGH.length} HIGH_CRITICAL • Cluster_Analysis :: Active
            </p>
          </div>
          <div className="hidden md:block flex-1"/>
          <div className="flex gap-2">
             <div className="status-badge negative">{riskGroups.HIGH.length} CRITICAL</div>
             <div className="status-badge">{predictions.length} NODES</div>
          </div>
        </div>

        {/* RESPONSIVE Risk Distribution Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 md:gap-6">
          {["HIGH", "MEDIUM", "LOW"].map(level => {
            const cfg = RISK_CONFIG[level];
            const Icon = cfg.icon;
            const count = riskGroups[level].length;
            const pct = predictions.length ? Math.round((count / predictions.length) * 100) : 0;
            return (
              <div key={level} className="glass-card p-5 md:p-6 flex flex-col gap-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-lg flex items-center justify-center border" 
                      style={{ background: `${cfg.color}08`, borderColor: `${cfg.color}15`, color: cfg.color }}>
                      <Icon size={18} />
                    </div>
                    <div className="flex flex-col">
                      <span className="text-[9px] font-bold tracking-widest text-slate-500 uppercase">{cfg.label}</span>
                      <span className="text-xl md:text-2xl font-bold font-mono text-white leading-none">{count}</span>
                    </div>
                  </div>
                  <div className="text-[11px] font-mono font-bold" style={{ color: cfg.color }}>{pct}%</div>
                </div>
                <div className="h-1 bg-black/40 rounded-sm overflow-hidden border border-white/[0.04]">
                  <div className="h-full rounded-sm transition-all duration-1000" style={{ width: `${pct}%`, background: cfg.color }} />
                </div>
              </div>
            );
          })}
        </div>

        <div className="flex flex-col lg:flex-row gap-6 md:gap-10">
          {/* Risk Grid - Main Panel */}
          <div className="flex-1 space-y-8 md:space-y-10">
            {["HIGH", "MEDIUM", "LOW"].map(level => {
              const cfg = RISK_CONFIG[level];
              const stocks = riskGroups[level];
              if (stocks.length === 0) return null;
              return (
                <div key={level} className="space-y-4">
                  <div className="flex items-center gap-4 px-1">
                    <span className="text-[10px] font-bold tracking-[0.3em] uppercase" style={{ color: cfg.color }}>{cfg.label}</span>
                    <div className="flex-1 h-[1px] bg-white/[0.05]" />
                    <span className="text-[8px] font-mono text-slate-700 uppercase">{stocks.length} CLUSTERS</span>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3 md:gap-4">
                    {stocks.map(s => (
                      <div key={s.ticker} onClick={() => fetchRiskDetail(s.ticker)}
                        className={`glass-card p-4 interactive border ${selectedRisk === s.ticker ? 'border-indigo-500/40 shadow-md shadow-indigo-900/10' : 'border-white/[0.06]'}`}>
                        <div className="flex justify-between items-start mb-2">
                          <div className="flex flex-col gap-0.5">
                            <span className="font-bold text-white text-[14px] leading-tight truncate max-w-[120px]">{s.ticker}</span>
                            <span className="text-[8px] text-slate-500 font-bold uppercase tracking-wider truncate max-w-[100px]">{s.name}</span>
                          </div>
                          <div className="flex flex-col items-end">
                             <span className="text-[10px] font-mono font-bold" style={{ color: s.chg >= 0 ? "var(--accent-positive)" : "var(--accent-negative)" }}>
                               {s.chg >= 0 ? "+" : ""}{s.chg?.toFixed(2)}%
                             </span>
                             <span className="text-[8px] text-slate-700 font-mono font-bold">${s.current_price?.toFixed(1)}</span>
                          </div>
                        </div>
                        <div className="mt-4 flex items-center justify-between gap-2 border-t border-white/[0.03] pt-3">
                           <div className="flex items-center gap-1.5">
                             <div className="w-1 h-1 rounded-sm" style={{ background: cfg.color }} />
                             <span className="text-[8px] font-bold tracking-widest text-slate-600 uppercase">VOLATILITY_INDEX</span>
                           </div>
                           <ChevronRight size={10} className="text-slate-800" />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Risk Detail Sidebar - Responsive Stack */}
          <div className="w-full lg:w-80 lg:shrink-0">
            {riskDetail ? (
              <div className="glass-panel p-5 md:p-6 space-y-6 self-start sticky top-10 border-indigo-500/10 rounded-lg shadow-2xl">
                <div className="flex items-center justify-between border-b border-white/[0.08] pb-4">
                  <div className="flex flex-col gap-1">
                    <h3 className="text-lg font-bold font-mono text-white leading-none">{riskDetail.ticker}</h3>
                    <p className="text-[9px] text-slate-500 font-bold uppercase tracking-wider">{riskDetail.name}</p>
                  </div>
                  <div className="px-2 py-0.5 rounded-sm border text-[8px] font-black tracking-widest uppercase"
                    style={{ borderColor: RISK_CONFIG[riskDetail.overall_risk]?.color, color: RISK_CONFIG[riskDetail.overall_risk]?.color }}>
                    {riskDetail.overall_risk}
                  </div>
                </div>

                <div className="space-y-4">
                  <MetricBar label="VaR (95%)" value={riskDetail.metrics.var_95} max={10} color="var(--accent-negative)" />
                  <MetricBar label="Beta Coefficient" value={riskDetail.metrics.beta} max={3} color="var(--accent-warn)" />
                  <MetricBar label="Max Drawdown est." value={riskDetail.metrics.max_drawdown_estimate} max={25} color="var(--accent-negative)" />
                </div>

                <div className="space-y-3 pt-4 border-t border-white/[0.06]">
                  <span className="text-[9px] font-bold text-slate-600 uppercase tracking-widest px-1">Risk Logic Factors</span>
                  <div className="flex flex-col gap-2">
                    {riskDetail.risk_factors?.map((f, i) => (
                      <div key={i} className="flex items-start gap-3 p-2.5 rounded-md bg-black/20 border border-white/[0.03]">
                        <AlertTriangle size={10} className="text-amber-500/60 mt-0.5 shrink-0" />
                        <span className="text-[9px] text-slate-400 leading-normal italic">"{f}"</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4 pt-4 border-t border-white/[0.06]">
                  <div className="flex flex-col gap-1 px-1">
                    <span className="text-[8px] font-bold text-slate-600 uppercase tracking-widest">52W_HIGH</span>
                    <span className="text-sm font-mono font-bold text-white">${riskDetail.week52_high?.toFixed(1)}</span>
                  </div>
                  <div className="flex flex-col gap-1 px-1 text-right">
                    <span className="text-[8px] font-bold text-slate-600 uppercase tracking-widest">52W_LOW</span>
                    <span className="text-sm font-mono font-bold text-slate-500">${riskDetail.week52_low?.toFixed(1)}</span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="glass-card p-10 flex flex-col items-center justify-center text-center gap-5 opacity-40 border-dashed border-white/[0.08] min-h-[300px]">
                 <Shield size={28} className="text-slate-800" />
                 <p className="text-[9px] font-mono font-bold text-slate-700 uppercase tracking-[0.2em] max-w-[120px]">Await Audit Selection</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
