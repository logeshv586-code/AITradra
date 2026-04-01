import React from 'react';
import { Target, ShieldAlert, Zap, Cpu, TrendingUp, ChevronRight } from 'lucide-react';

function Level({ label, value, color, icon: Icon }) {
  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center gap-1.5 opacity-60">
        {Icon && <Icon size={10} className="text-slate-500" />}
        <span className="text-[8px] font-bold text-slate-500 uppercase tracking-widest leading-none">{label}</span>
      </div>
      <span className={`text-[12px] font-mono font-bold leading-none ${color}`}>{typeof value === 'number' ? `$${value.toFixed(2)}` : value}</span>
    </div>
  );
}

export default function AnalysisCard({ analysis }) {
  if (!analysis) return (
    <div className="h-64 bg-white/[0.01] border border-dashed border-white/[0.08] rounded-xl animate-pulse flex flex-col items-center justify-center gap-2">
       <Cpu size={24} className="text-indigo-500/40" />
       <span className="text-[10px] font-mono text-slate-600 uppercase tracking-[0.2em]">Synthesizing Analysis...</span>
    </div>
  );

  const signalColors = {
    STRONG_BUY: "text-emerald-400", 
    BUY:        "text-emerald-500",
    HOLD:       "text-amber-400",
    SELL:       "text-red-400", 
    STRONG_SELL:"text-red-500"
  };

  const signalColor = signalColors[analysis.signal] || "text-slate-400";

  return (
    <div className="glass-card p-6 border border-white/[0.08] bg-white/[0.01]">
      <div className="flex justify-between items-start mb-8">
        <div className="flex flex-col gap-1.5">
          <div className="flex items-center gap-2">
            <Cpu size={14} className="text-indigo-400" />
            <span className="text-[9px] font-bold text-slate-500 uppercase tracking-[0.2em]">Alpha Recommendation</span>
          </div>
          <span className={`text-[24px] font-bold ${signalColor} tracking-tighter uppercase leading-none`}>{analysis.signal}</span>
        </div>
        <div className="w-10 h-10 rounded-lg bg-black/40 border border-white/[0.06] flex items-center justify-center text-[18px] font-mono font-bold text-white shadow-inner tabular-nums">
          {analysis.overall_score}
        </div>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-6 mb-8 p-4 rounded-xl bg-black/20 border border-white/[0.04]">
        <Level label="Entry"  value={analysis.entry_price} color="text-indigo-400" icon={Target} />
        <Level label="Target" value={analysis.target_price} color="text-emerald-400" icon={TrendingUp} />
        <Level label="Stop"   value={analysis.stop_loss} color="text-red-400" icon={ShieldAlert} />
        <Level label="Horizon" value={analysis.time_horizon} color="text-slate-500" />
      </div>

      <div className="space-y-6 mb-8">
        {analysis.criteria?.map((c, i) => (
          <div key={i} className="flex flex-col gap-2 group">
            <div className="flex justify-between items-center px-0.5">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-tight group-hover:text-white transition-colors">{c.name}</span>
              <span className="text-[10px] font-mono font-bold text-slate-600">{c.score}/10</span>
            </div>
            <div className="h-1 bg-black/40 rounded-full overflow-hidden border border-white/[0.04]">
               <div className="h-full bg-indigo-500/40 rounded-full transition-all duration-1000" style={{ width: `${c.score * 10}%` }} />
            </div>
            <p className="text-[10px] text-slate-600 leading-normal italic line-clamp-1">— "{c.reason}"</p>
          </div>
        ))}
      </div>

      {analysis.cited_article && (
        <div className="p-4 rounded-xl bg-indigo-500/5 border border-indigo-500/10 mb-8 flex flex-col gap-2 group hover:border-indigo-500/30 transition-all duration-120">
           <span className="text-[9px] font-bold text-indigo-400 uppercase tracking-widest block leading-none">Primary Evidence</span>
           <a href={analysis.cited_article.url} target="_blank" rel="noopener noreferrer" className="text-[11px] font-bold text-slate-400 group-hover:text-indigo-300 leading-tight transition-colors uppercase">
             {analysis.cited_article.headline}
           </a>
        </div>
      )}

      <div className="pt-4 border-t border-white/[0.08] flex flex-col gap-3">
         <div className="flex items-start gap-3 p-3 rounded-lg bg-red-500/[0.03] border border-red-500/10">
            <ShieldAlert size={12} className="text-red-500/60 mt-0.5 shrink-0" />
            <div className="flex flex-col gap-0.5">
               <span className="text-[8px] font-bold text-red-500/60 uppercase tracking-widest">Risk_Expose:</span>
               <p className="text-[10px] text-slate-400 font-medium">{analysis.key_risk}</p>
            </div>
         </div>
         <div className="flex items-start gap-3 p-3 rounded-lg bg-emerald-500/[0.03] border border-emerald-500/10">
            <Zap size={12} className="text-emerald-500/60 mt-0.5 shrink-0" />
            <div className="flex flex-col gap-0.5">
               <span className="text-[8px] font-bold text-emerald-500/60 uppercase tracking-widest">Growth_Vector:</span>
               <p className="text-[10px] text-slate-400 font-medium">{analysis.key_catalyst}</p>
            </div>
         </div>
      </div>
    </div>
  );
}
