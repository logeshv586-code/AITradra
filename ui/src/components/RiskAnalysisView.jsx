import React, { useState, useEffect } from "react";
import { ShieldAlert, Activity, Loader2, AlertTriangle, Shield, ShieldCheck } from "lucide-react";

import { API_BASE } from "../api_config";

const RISK_CONFIG = {
  LOW:    { color: "#22c55e", bg: "rgba(34,197,94,0.10)", icon: ShieldCheck, label: "LOW RISK" },
  MEDIUM: { color: "#fbbf24", bg: "rgba(251,191,36,0.10)", icon: Shield,      label: "MEDIUM RISK" },
  HIGH:   { color: "#ef4444", bg: "rgba(239,68,68,0.10)", icon: AlertTriangle, label: "HIGH RISK" },
};

function MetricBar({ label, value, max = 10, color }) {
  const pct = Math.min((parseFloat(value) / max) * 100, 100);
  return (
    <div className="space-y-1">
      <div className="flex justify-between">
        <span className="text-[9px] font-black text-slate-500 uppercase tracking-widest">{label}</span>
        <span className="text-[10px] font-mono font-bold" style={{ color }}>{value}</span>
      </div>
      <div className="h-1.5 bg-black/30 rounded-full overflow-hidden">
        <div className="h-full rounded-full transition-all duration-700" style={{ width: `${pct}%`, background: color }} />
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

  // Group by risk level
  const riskGroups = { HIGH: [], MEDIUM: [], LOW: [] };
  predictions.forEach(p => {
    const group = riskGroups[p.risk_level] || riskGroups.MEDIUM;
    group.push(p);
  });

  if (loading) return (
    <div className="flex-1 flex items-center justify-center">
      <div className="text-center space-y-3">
        <Loader2 size={32} className="text-red-400 animate-spin mx-auto" />
        <p className="text-xs font-mono text-slate-500 tracking-widest">EVALUATING RISK MATRIX...</p>
      </div>
    </div>
  );

  return (
    <div className="flex-1 p-8 overflow-y-auto no-scrollbar animate-fade-in">
      <div className="max-w-7xl mx-auto space-y-8">
        {/* Header */}
        <div className="flex items-center gap-4 border-b border-white/5 pb-6">
          <div className="p-3 bg-red-500/10 rounded-2xl border border-red-500/30 shadow-lg">
            <ShieldAlert size={24} className="text-red-400" />
          </div>
          <div>
            <h2 className="text-3xl font-black text-white tracking-tighter uppercase">Risk Analysis</h2>
            <p className="text-[10px] font-mono text-slate-500 tracking-[0.3em] uppercase mt-1">
              {riskGroups.HIGH.length} HIGH • {riskGroups.MEDIUM.length} MEDIUM • {riskGroups.LOW.length} LOW
            </p>
          </div>
        </div>

        {/* Risk Distribution Summary */}
        <div className="grid grid-cols-3 gap-4">
          {["HIGH", "MEDIUM", "LOW"].map(level => {
            const cfg = RISK_CONFIG[level];
            const Icon = cfg.icon;
            const count = riskGroups[level].length;
            const pct = predictions.length ? Math.round((count / predictions.length) * 100) : 0;
            return (
              <div key={level} className="clay-card p-5 space-y-3" style={{ borderTop: `2px solid ${cfg.color}40` }}>
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-xl" style={{ background: cfg.bg }}>
                    <Icon size={18} style={{ color: cfg.color }} />
                  </div>
                  <div>
                    <div className="text-[9px] font-black tracking-widest text-slate-500 uppercase">{cfg.label}</div>
                    <div className="text-2xl font-black font-mono" style={{ color: cfg.color }}>{count}</div>
                  </div>
                </div>
                <div className="h-1.5 bg-black/30 rounded-full overflow-hidden">
                  <div className="h-full rounded-full transition-all duration-1000" style={{ width: `${pct}%`, background: cfg.color }} />
                </div>
                <div className="text-[9px] text-slate-600 font-mono">{pct}% of portfolio</div>
              </div>
            );
          })}
        </div>

        <div className="flex gap-8">
          {/* Risk Grid */}
          <div className="flex-1 space-y-6">
            {["HIGH", "MEDIUM", "LOW"].map(level => {
              const cfg = RISK_CONFIG[level];
              const stocks = riskGroups[level];
              if (stocks.length === 0) return null;
              return (
                <div key={level} className="space-y-3">
                  <div className="flex items-center gap-3">
                    <span className="text-[10px] font-black tracking-[0.3em] uppercase" style={{ color: cfg.color }}>{cfg.label}</span>
                    <div className="flex-1 h-px" style={{ background: `${cfg.color}20` }} />
                  </div>
                  <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
                    {stocks.map(s => (
                      <div key={s.ticker} onClick={() => fetchRiskDetail(s.ticker)}
                        className={`clay-card p-4 cursor-pointer hover:scale-[1.02] transition-all ${selectedRisk === s.ticker ? 'ring-1 ring-indigo-500/50' : ''}`}>
                        <div className="flex items-center justify-between mb-2">
                          <span className="font-mono font-bold text-white text-sm">{s.ticker}</span>
                          <span className="text-[9px] font-mono" style={{ color: s.chg >= 0 ? "#22c55e" : "#ef4444" }}>
                            {s.chg >= 0 ? "+" : ""}{s.chg?.toFixed(2)}%
                          </span>
                        </div>
                        <div className="text-[9px] text-slate-500 truncate">{s.name}</div>
                        <div className="mt-2 flex items-center gap-2">
                          <span className="px-1.5 py-0.5 rounded text-[8px] font-black" style={{ background: cfg.bg, color: cfg.color }}>{level}</span>
                          <span className="text-[9px] text-slate-600 font-mono">${s.current_price?.toFixed(2)}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Risk Detail Panel */}
          {riskDetail && (
            <div className="w-80 shrink-0 clay-card p-6 space-y-5 self-start sticky top-8" style={{ borderTop: `2px solid ${RISK_CONFIG[riskDetail.overall_risk]?.color || "#fbbf24"}40` }}>
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-xl font-black font-mono text-white">{riskDetail.ticker}</h3>
                  <p className="text-[10px] text-slate-500">{riskDetail.name}</p>
                </div>
                <span className="px-2.5 py-1 rounded-lg text-[9px] font-black tracking-wider"
                  style={{ background: RISK_CONFIG[riskDetail.overall_risk]?.bg, color: RISK_CONFIG[riskDetail.overall_risk]?.color }}>
                  {riskDetail.overall_risk}
                </span>
              </div>

              <div className="space-y-3">
                <MetricBar label="VaR (95%)" value={riskDetail.metrics.var_95} max={10} color="#ef4444" />
                <MetricBar label="Beta" value={riskDetail.metrics.beta} max={3} color="#fbbf24" />
                <MetricBar label="Max Drawdown" value={riskDetail.metrics.max_drawdown_estimate} max={25} color="#ef4444" />
              </div>

              <div className="space-y-2 pt-3 border-t border-white/5">
                <span className="text-[9px] font-black text-slate-500 uppercase tracking-widest">Risk Factors</span>
                {riskDetail.risk_factors?.map((f, i) => (
                  <div key={i} className="flex items-start gap-2">
                    <AlertTriangle size={10} className="text-amber-400 mt-0.5 shrink-0" />
                    <span className="text-[10px] text-slate-400 leading-snug">{f}</span>
                  </div>
                ))}
              </div>

              <div className="grid grid-cols-2 gap-3 pt-3 border-t border-white/5">
                <div>
                  <span className="text-[8px] font-black text-slate-600 uppercase tracking-widest">52W HIGH</span>
                  <div className="text-sm font-mono font-bold text-white">${riskDetail.week52_high?.toFixed(2)}</div>
                </div>
                <div>
                  <span className="text-[8px] font-black text-slate-600 uppercase tracking-widest">52W LOW</span>
                  <div className="text-sm font-mono font-bold text-white">${riskDetail.week52_low?.toFixed(2)}</div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
