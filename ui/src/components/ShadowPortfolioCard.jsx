import React, { useState, useEffect } from "react";
import { TrendingUp, TrendingDown, ArrowUpRight, ArrowDownRight, Zap, Target } from "lucide-react";
import { API_BASE } from "../constants/config";

const ShadowPick = ({ pick }) => (
    <div className="clay-card p-4 flex flex-col gap-3 min-w-[200px] flex-1">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
           <div className="w-8 h-8 rounded-lg bg-indigo-500/10 border border-indigo-400/20 flex items-center justify-center font-bold text-[10px] text-white">
             {pick.ticker[0]}
           </div>
           <span className="font-bold text-white uppercase">{pick.ticker}</span>
        </div>
        {(pick.pl || 0) >= 0 ? <ArrowUpRight size={14} className="text-emerald-400" /> : <ArrowDownRight size={14} className="text-red-400" />}
      </div>
      
      <div className="flex flex-col gap-0.5">
         <span className="text-[8px] text-slate-500 uppercase font-bold tracking-widest">Live Performance:</span>
         <span className={`text-xl font-mono font-bold ${(pick.pl || 0) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
            {(pick.pl || 0) >= 0 ? '+' : ''}{(pick.pl_pct || 0).toFixed(2)}%
         </span>
      </div>
      
      <div className="mt-2 pt-2 border-t border-white/5 flex flex-col gap-1">
         <span className="text-[8px] text-slate-500 uppercase font-bold tracking-tighter italic">"Shadow reasoning: {pick.reason || 'Consensus high-conviction discovered.'}"</span>
      </div>
    </div>
);

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

  if (loading && data.portfolio.length === 0) return <div className="animate-pulse text-indigo-400 font-mono text-[10px]">SYNCING WITH SHADOW INVESTOR...</div>;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-bold tracking-[0.2em] text-white uppercase font-mono flex items-center gap-2">
          <Target size={14} className="text-indigo-400" />
          Autonomous Shadow Portfolio (5% VIRTUAL ONLY)
        </h3>
        <div className="flex items-center gap-4">
           <div className="flex flex-col items-end">
              <span className="text-[8px] text-slate-500 uppercase font-bold">Accuracy:</span>
              <span className="text-[10px] font-mono text-indigo-400 font-bold">{data.metrics.accuracy.toFixed(1)}%</span>
           </div>
           <div className="flex flex-col items-end">
              <span className="text-[8px] text-slate-500 uppercase font-bold">Day P/L:</span>
              <span className={`text-[10px] font-mono font-bold ${data.metrics.day_pl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                {data.metrics.day_pl >= 0 ? '+' : ''}{data.metrics.day_pl.toFixed(2)}
              </span>
           </div>
        </div>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {data.portfolio.slice(0, 3).map((pick, i) => (
          <ShadowPick key={pick.ticker} pick={pick} />
        ))}
        {data.portfolio.length === 0 && (
           <div className="col-span-full py-12 text-center text-slate-500 font-mono text-[10px] uppercase tracking-widest border border-dashed border-white/10 rounded-2xl flex flex-col gap-2 bg-white/5">
              <span>Scanning for high-conviction 85% consensus...</span>
              <span className="text-[8px]">DAILY SCAN: 9:30 AM EST</span>
           </div>
        )}
      </div>
    </div>
  );
}
