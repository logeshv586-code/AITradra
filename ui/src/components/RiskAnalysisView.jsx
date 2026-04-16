import React, { useState, useEffect } from "react";
import { ShieldAlert, Loader2, AlertTriangle, Shield, ShieldCheck, ChevronRight } from "lucide-react";
import { API_BASE } from "../api_config";

const RISK = {
  LOW:    { color: "var(--positive)", icon: ShieldCheck, label: "Low Risk" },
  MEDIUM: { color: "var(--warning)",  icon: Shield,      label: "Medium Risk" },
  HIGH:   { color: "var(--negative)", icon: AlertTriangle, label: "High Risk" },
};

function Bar({ label, value, max, color }) {
  const pct = Math.min((parseFloat(value) / max) * 100, 100);
  return (
    <div className="space-y-1.5">
      <div className="flex justify-between text-small-caps text-[var(--text-muted)]">
        <span>{label}</span>
        <span className="font-mono text-[11px]" style={{ color }}>{value}</span>
      </div>
      <div className="h-1.5 rounded-full bg-[#1e232b] overflow-hidden">
        <div className="h-full rounded-full transition-all duration-700" style={{ width: `${pct}%`, background: color }} />
      </div>
    </div>
  );
}

export default function RiskAnalysisView({ onSelect }) {
  const [predictions, setPredictions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selTicker, setSelTicker] = useState(null);
  const [detail, setDetail] = useState(null);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/market/predictions`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        if (!cancelled) setPredictions(data.predictions || []);
      } catch (err) {
        if (!cancelled) setError(err.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    load();
    const id = setInterval(load, 60_000);
    return () => { cancelled = true; clearInterval(id); };
  }, []);

  const fetchDetail = async (ticker) => {
    setSelTicker(ticker);
    setDetail(null);
    try {
      const res = await fetch(`${API_BASE}/api/stock/${ticker}/risk`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setDetail(await res.json());
    } catch (err) {
      console.error("Risk detail fetch failed:", err);
    }
  };

  const groups = { HIGH: [], MEDIUM: [], LOW: [] };
  predictions.forEach((p) => (groups[p.risk_level] || groups.MEDIUM).push(p));

  if (loading) return (
             <div className="h-full flex flex-col items-center justify-center gap-4 bg-[var(--app-bg)] w-full">
               <Loader2 size={24} className="text-[var(--accent)] animate-spin" />
               <span className="text-[12px] font-medium text-[var(--text-muted)]">Scanning risk matrix...</span>
             </div>
  );

  if (error) return (
             <div className="h-full flex flex-col items-center justify-center gap-2 bg-[var(--app-bg)] w-full text-[var(--negative)]">
               <Shield size={28} className="mb-2" />
               <p className="font-semibold text-[13px]">Risk Matrix Offline</p>
               <p className="text-[11px] font-mono opacity-80">{error}</p>
             </div>
  );

  return (
    <div className="flex-1 overflow-y-auto w-full p-4 md:p-6 lg:p-8 max-w-[1440px] mx-auto animate-fade-in relative grid grid-cols-1 lg:grid-cols-[1fr_360px] gap-6 lg:gap-8">
      
      {/* Left Column: List */}
      <div className="flex flex-col gap-6">
         {/* Page Header */}
         <div className="flex flex-col gap-2">
            <div className="flex items-center gap-3">
               <ShieldAlert size={20} className="text-[var(--warning)]" />
               <h1 className="heading-1">Risk Dynamics</h1>
            </div>
            <p className="text-[13px] text-[var(--text-muted)]">Live monitoring of volatility and downside risk across active models.</p>
         </div>

         {/* Summary bar */}
         <div className="flex items-center gap-3 w-full border-b border-[var(--border-color)] pb-4 overflow-x-auto">
            {["HIGH", "MEDIUM", "LOW"].map((l) => (
               <div key={l} className="surface-badge text-white" style={{ borderColor: `${RISK[l].color}50` }}>
                  <div className="w-2 h-2 rounded-full" style={{backgroundColor: RISK[l].color}}/>
                  {groups[l].length} {l.toLowerCase()}
               </div>
            ))}
         </div>

         {/* Groups */}
         <div className="flex flex-col gap-8">
            {["HIGH", "MEDIUM", "LOW"].map((level) => {
               const cfg = RISK[level];
               const items = groups[level];
               if (!items.length) return null;
               
               return (
                  <div key={level} className="flex flex-col gap-4">
                     <div className="flex items-center gap-3">
                        <span className="text-small-caps font-bold" style={{ color: cfg.color }}>{cfg.label}</span>
                        <div className="flex-1 h-px bg-[var(--border-color)]" />
                     </div>
                     <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        {items.map((s) => (
                           <article 
                              key={s.ticker} 
                              onClick={() => fetchDetail(s.ticker)}
                              className={`interactive-card p-4 flex flex-col justify-between ${selTicker === s.ticker ? "border-[var(--accent)] bg-[#1b1f27]" : ""}`}
                           >
                              <div className="flex justify-between items-start mb-4">
                                 <div className="flex flex-col">
                                    <span className="text-[14px] font-semibold text-white">{s.ticker}</span>
                                    <span className="text-[11px] text-[var(--text-muted)] truncate max-w-[120px]">{s.name}</span>
                                 </div>
                                 <span className="text-[12px] font-mono font-medium" style={{ color: s.chg >= 0 ? "var(--positive)" : "var(--negative)" }}>
                                    {s.chg >= 0 ? "+" : ""}{s.chg?.toFixed(2)}%
                                 </span>
                              </div>
                              <div className="flex items-center justify-between mt-auto">
                                 <span className="text-[12px] font-mono font-medium text-[var(--text-main)]">${s.current_price?.toFixed(2)}</span>
                                 <ChevronRight size={14} className="text-[var(--text-muted)] group-hover:text-white transition-colors" />
                              </div>
                           </article>
                        ))}
                     </div>
                  </div>
               );
            })}
         </div>
      </div>

      {/* Right Column: Detail */}
      <div className="lg:sticky lg:top-8 self-start flex flex-col gap-4">
         {detail ? (
            <div className="surface-card flex flex-col overflow-hidden">
               {/* Detail Header */}
               <div className="p-6 border-b border-[var(--border-color)] bg-[#1b1f27] flex items-center justify-between">
                  <div>
                     <h3 className="heading-2">{detail.ticker}</h3>
                     <p className="text-[11px] text-[var(--text-muted)]">{detail.name}</p>
                  </div>
                  <span className="surface-badge" style={{ borderColor: RISK[detail.overall_risk]?.color, color: RISK[detail.overall_risk]?.color }}>
                     {detail.overall_risk}
                  </span>
               </div>
               
               {/* Metrics */}
               <div className="p-6 flex flex-col gap-6">
                  <div className="space-y-4">
                     <Bar label="VaR (95%)" value={detail.metrics?.var_95 || 0} max={10} color="var(--negative)" />
                     <Bar label="Beta" value={detail.metrics?.beta || 0} max={3} color="var(--warning)" />
                     <Bar label="Max Drawdown" value={detail.metrics?.max_drawdown_estimate || 0} max={25} color="var(--negative)" />
                  </div>

                  {detail.risk_factors?.length > 0 && (
                     <div className="pt-6 border-t border-[var(--border-color)] flex flex-col gap-3">
                        <p className="text-small-caps">Risk Factors</p>
                        {detail.risk_factors.map((f, i) => (
                           <div key={i} className="flex items-start gap-2 bg-[#1e232b] border border-[var(--border-color)] rounded-[var(--radius-sm)] p-2">
                              <AlertTriangle size={12} className="text-[var(--warning)] shrink-0 mt-0.5" />
                              <span className="text-[11px] text-[var(--text-muted)] leading-relaxed">{f}</span>
                           </div>
                        ))}
                     </div>
                  )}

                  <div className="pt-6 border-t border-[var(--border-color)] grid grid-cols-2 gap-4">
                     <div className="flex flex-col gap-1">
                        <span className="text-small-caps">52W High</span>
                        <span className="font-mono text-[14px] text-white">${detail.week52_high?.toFixed(2)}</span>
                     </div>
                     <div className="flex flex-col gap-1 text-right">
                        <span className="text-small-caps">52W Low</span>
                        <span className="font-mono text-[14px] text-[var(--text-muted)]">${detail.week52_low?.toFixed(2)}</span>
                     </div>
                  </div>
               </div>
            </div>
         ) : (
            <div className="surface-card p-12 flex flex-col items-center justify-center text-center opacity-70 border-dashed">
               <Shield size={32} className="text-[var(--text-muted)] mb-4" />
               <p className="text-[13px] font-medium text-white mb-1">No Asset Selected</p>
               <p className="text-[11px] text-[var(--text-muted)]">Select an asset from the risk matrices on the left to view detailed metrics.</p>
            </div>
         )}
      </div>

    </div>
  );
}
