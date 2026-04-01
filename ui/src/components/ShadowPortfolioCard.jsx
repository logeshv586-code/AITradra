import React, { useState, useEffect } from "react";
import { TrendingUp, TrendingDown, ArrowUpRight, ArrowDownRight, Zap, Target, Activity } from "lucide-react";
import { API_BASE } from "../api_config";

const ShadowPick = ({ pick }) => {
  const isUp = (pick.pl || 0) >= 0;
  const col = isUp ? 'var(--accent-positive)' : 'var(--accent-negative)';
  
  return (
    <div className="glass-card p-5 flex flex-col gap-4 border border-white/[0.06] hover:bg-white/[0.02] transition-all duration-120 group">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg flex items-center justify-center font-bold text-[12px] text-white border"
             style={{ background: `${col}08`, borderColor: `${col}15`, color: col }}>
            {pick.ticker[0]}
          </div>
          <div className="flex flex-col gap-0.5">
             <span className="font-bold text-white uppercase tracking-tight text-[14px]">{pick.ticker}</span>
             <span className="text-[8px] text-slate-600 font-bold uppercase tracking-widest leading-none">Autonomous Pick</span>
          </div>
        </div>
        {isUp ? <ArrowUpRight size={14} className="text-emerald-400 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" /> : <ArrowDownRight size={14} className="text-red-400" />}
      </div>
      
      <div className="space-y-1">
         <span className="text-[9px] text-slate-500 uppercase font-bold tracking-widest block">Live Drift</span>
         <span className={`text-[18px] font-mono font-bold tabular-nums leading-none ${isUp ? 'text-emerald-400' : 'text-red-400'}`}>
            {isUp ? '+' : ''}{(pick.pl_pct || 0).toFixed(2)}%
         </span>
      </div>
      
      <div className="pt-3 border-t border-white/[0.05]">
         <p className="text-[10px] text-slate-500 leading-relaxed italic line-clamp-2">
            "{pick.reason || 'Consensus high-conviction discovered across multi-agent nexus.'}"
         </p>
      </div>
    </div>
  );
};

export default function ShadowPortfolioCard() {
  const [data, setData] = useState({ portfolio: [], metrics: { accuracy: 100, day_pl: 0 } });
  const [loading, setLoading] = useState(true);

  const fetchStatus = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/mission/shadow_portfolio`);
      const result = await res.json();
      setData(result);
      setLoading(false);
    } catch (err) {
      console.error("Failed to fetch shadow portfolio:", err);
    }
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 10000);
    return () => clearInterval(interval);
  }, []);

  if (loading && data.portfolio.length === 0) return (
    <div className="flex items-center gap-3 py-6 px-1 animate-pulse">
       <Activity size={14} className="text-indigo-500" />
       <span className="text-[10px] font-mono text-slate-600 uppercase tracking-[0.3em]">Syncing Shadow Stream...</span>
    </div>
  );

  return (
    <div className="flex flex-col gap-8 animate-fade-in">
      <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-6 border-b border-white/[0.08] pb-6">
        <div className="flex flex-col gap-2">
          <h3 className="text-[12px] font-bold tracking-[0.25em] text-white uppercase flex items-center gap-3">
            <Target size={16} className="text-indigo-400" />
            Autonomous Shadow Vector
          </h3>
          <p className="text-[9px] text-slate-600 font-bold uppercase tracking-widest ml-7 opacity-60">
             VIRTUAL_ALLOCATION // 5.0% EXPOSURE // NODE_V4.1
          </p>
        </div>
        
        <div className="flex items-center gap-8 px-1">
           <div className="flex flex-col items-end gap-0.5">
              <span className="text-[8px] text-slate-600 uppercase font-bold tracking-widest">Aggregate_Acc</span>
              <span className="text-[14px] font-mono text-indigo-400 font-bold leading-none">{data.metrics.accuracy.toFixed(1)}%</span>
           </div>
           <div className="w-[1px] h-6 bg-white/[0.08]" />
           <div className="flex flex-col items-end gap-0.5">
              <span className="text-[8px] text-slate-600 uppercase font-bold tracking-widest">Intraday_Delta</span>
              <span className={`text-[14px] font-mono font-bold leading-none ${data.metrics.day_pl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                {data.metrics.day_pl >= 0 ? '+' : ''}{data.metrics.day_pl.toFixed(2)}
              </span>
           </div>
        </div>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
        {data.portfolio.slice(0, 4).map((pick, i) => (
          <ShadowPick key={pick.ticker} pick={pick} />
        ))}
        {data.portfolio.length === 0 && (
           <div className="col-span-full py-16 text-center border-2 border-dashed border-white/[0.04] rounded-2xl flex flex-col items-center gap-4 bg-white/[0.01]">
              <Activity size={32} className="text-slate-800 animate-pulse" />
              <div className="flex flex-col gap-1">
                <span className="text-[10px] text-slate-600 font-bold uppercase tracking-[0.3em]">Scanning Flux Triggers</span>
                <span className="text-[8px] text-slate-800 font-mono italic">NEXT_SWEEP :: 09:30 EST</span>
              </div>
           </div>
        )}
      </div>
    </div>
  );
}
