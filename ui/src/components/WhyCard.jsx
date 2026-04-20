import React from 'react';
import { Newspaper, ShieldCheck, Activity, Brain, PieChart, Info } from 'lucide-react';

export default function WhyCard({ ticker, explanation }) {
  if (!explanation) return (
    <div className="glass-panel p-6 border-dashed border-white/[0.08] flex items-center justify-center min-h-[140px]">
       <div className="flex flex-col items-center gap-2">
         <Brain size={24} className="text-slate-800 animate-pulse" />
         <span className="text-[10px] font-mono text-slate-700 uppercase tracking-widest">Awaiting Neural Insights...</span>
       </div>
    </div>
  );

  const { 
    reason, 
    sentiment, 
    confidence, 
    key_headlines, 
    catalyst_type, 
    magnitude, 
    generated_at,
    price_change
  } = explanation;

  const sentimentColor = 
    sentiment === 'BULLISH' ? 'var(--positive)' : 
    sentiment === 'BEARISH' ? 'var(--negative)' : 
    'var(--warning)';

  return (
    <div className="glass-panel overflow-hidden border-l-2 relative group transition-all duration-300 hover:border-l-indigo-500"
         style={{ borderLeftColor: sentimentColor }}>
      
      {/* Background Accent */}
      <div className="absolute top-0 right-0 p-8 opacity-[0.03] group-hover:opacity-[0.07] transition-opacity">
        <Activity size={120} className="text-white" />
      </div>

      <div className="p-6 relative z-10">
        <div className="flex justify-between items-start mb-6">
          <div className="flex flex-col gap-1">
            <div className="flex items-center gap-2">
              <Brain size={16} className="text-indigo-400" />
              <span className="text-[10px] font-bold text-indigo-400 uppercase tracking-[0.2em]">Neural_Reasoning_Engine</span>
            </div>
            <h3 className="text-[11px] font-mono text-slate-500 uppercase">
              {ticker} | {magnitude} Catalyst Detected
            </h3>
          </div>
          
          <div className="flex items-center gap-3">
            <div className="flex flex-col items-end">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Confidence</span>
              <span className="text-[14px] font-mono font-bold text-white">{confidence}%</span>
            </div>
            <div className="h-8 w-px bg-white/[0.06]" />
            <div className="flex flex-col items-end">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Impact</span>
              <span className="text-[14px] font-mono font-bold" style={{ color: sentimentColor }}>
                {price_change > 0 ? '+' : ''}{price_change}%
              </span>
            </div>
          </div>
        </div>

        <div className="mb-6">
          <div className="flex items-center gap-2 mb-2 p-1 px-2 rounded-md bg-white/[0.03] border border-white/[0.06] w-fit">
            <Info size={12} className="text-slate-500" />
            <span className="text-[9px] font-bold text-slate-400 uppercase tracking-tighter">Catalyst Type: {catalyst_type}</span>
          </div>
          <p className="text-[14px] text-slate-200 leading-relaxed font-medium">
            {reason}
          </p>
        </div>

        {key_headlines && key_headlines.length > 0 && (
          <div className="space-y-2">
            <span className="text-[9px] font-bold text-slate-600 uppercase tracking-widest block mb-2">Evidence Chunks</span>
            {key_headlines.map((headline, i) => (
              <div key={i} className="flex items-center gap-3 p-2.5 rounded-lg bg-black/40 border border-white/[0.04] hover:border-white/[0.1] transition-all">
                <Newspaper size={12} className="text-slate-500 shrink-0" />
                <span className="text-[11px] text-slate-400 truncate">{headline}</span>
              </div>
            ))}
          </div>
        )}

        <div className="mt-6 pt-4 border-t border-white/[0.04] flex justify-between items-center">
          <div className="flex items-center gap-1.5">
            <Activity size={12} className="text-slate-600" />
            <span className="text-[9px] font-mono text-slate-600 uppercase">Live_Inference: {generated_at || 'just now'}</span>
          </div>
          <div className="flex items-center gap-1 text-[9px] font-bold text-indigo-500/60 uppercase group-hover:text-indigo-400 transition-colors cursor-pointer">
             <PieChart size={12} />
             <span>View Swarm Consensus</span>
          </div>
        </div>
      </div>
    </div>
  );
}
