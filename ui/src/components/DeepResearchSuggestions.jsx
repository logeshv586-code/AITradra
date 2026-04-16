import React from 'react';
import { Lightbulb, ArrowRight, BookOpen } from 'lucide-react';

export default function DeepResearchSuggestions() {
  const suggestions = [
    { title: "Macro Impact on Tech", desc: "Analyze the 5-year correlation between prime rates and NASDAQ top 10.", type: "MACRO" },
    { title: "Earnings Surprise DB", desc: "Scan Q3 earnings anomalies against pre-release sentiment data.", type: "FUNDAMENTAL" },
    { title: "Options Flow Anomalies", desc: "Identify unusual put/call volume spikes from the past 48 hours.", type: "QUANT" }
  ];

  return (
    <div className="flex flex-col h-full bg-[var(--card-bg)]">
       <div className="p-5 flex flex-col gap-4">
          {suggestions.map((s, i) => (
             <div key={i} className="flex gap-4 p-4 bg-[#1e232b] rounded-[var(--radius-md)] border border-[var(--border-color)] hover:border-slate-500 transition-colors group cursor-pointer">
                <div className="shrink-0 mt-1">
                   <Lightbulb size={20} className="text-[var(--accent)]" />
                </div>
                <div className="flex flex-col">
                   <div className="flex items-center gap-2 mb-1">
                      <h4 className="text-[14px] font-semibold text-white group-hover:text-[var(--accent)] transition-colors">{s.title}</h4>
                      <span className="text-[9px] font-bold uppercase tracking-wider text-[var(--accent)] px-2 py-0.5 rounded border border-[var(--accent)] border-opacity-30 bg-[#3b82f615]">
                         {s.type}
                      </span>
                   </div>
                   <p className="text-[12px] text-[var(--text-muted)] leading-relaxed mb-3">{s.desc}</p>
                   <div className="flex items-center gap-2 text-[11px] font-medium text-[var(--text-muted)] group-hover:text-white transition-colors">
                      Execute Query <ArrowRight size={12} />
                   </div>
                </div>
             </div>
          ))}
       </div>
    </div>
  );
}
