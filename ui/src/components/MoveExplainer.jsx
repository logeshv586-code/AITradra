import React from 'react';
import { Newspaper, ShieldCheck, Activity } from 'lucide-react';

export default function MoveExplainer({ reason }) {
  if (!reason) return (
    <div className="h-24 bg-white/[0.01] border border-dashed border-white/[0.08] rounded-xl animate-pulse flex items-center justify-center">
       <span className="text-[10px] font-mono text-slate-700 uppercase tracking-widest">Awaiting Move Reason...</span>
    </div>
  );

  const { explanation, cited_article, confidence, primary_cause } = reason;

  return (
    <div className="glass-panel p-6 border-l-2 border-l-indigo-500 bg-indigo-500/[0.02]">
      <div className="flex justify-between items-center mb-4">
        <div className="flex items-center gap-2">
          <Activity size={14} className="text-indigo-400" />
          <span className="text-[10px] font-bold text-indigo-400 uppercase tracking-[0.2em]">Catalyst_Root: {primary_cause}</span>
        </div>
        <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-white/[0.02] border border-white/[0.06]">
           <ShieldCheck size={10} className="text-slate-500" />
           <span className="text-[9px] font-mono font-bold text-slate-500 uppercase">{confidence}% CONF</span>
        </div>
      </div>
      <p className="text-[13px] text-slate-300 leading-relaxed mb-6 font-medium italic">
        "{explanation}"
      </p>
      {cited_article && (
        <a 
          href={cited_article.url} 
          target="_blank" 
          rel="noopener noreferrer"
          className="group flex items-center justify-between p-3 rounded-xl bg-black/40 border border-white/[0.05] hover:border-indigo-500/30 transition-all duration-120"
        >
          <div className="flex items-center gap-3 overflow-hidden">
            <Newspaper size={14} className="text-slate-600 group-hover:text-indigo-400" />
            <span className="text-[11px] text-slate-400 group-hover:text-white truncate font-bold uppercase tracking-tight">{cited_article.headline}</span>
          </div>
          <span className="shrink-0 text-[9px] font-mono font-bold text-slate-700 uppercase ml-4">[{cited_article.source}]</span>
        </a>
      )}
    </div>
  );
}
