import React from 'react';

export default function AnalysisCard({ analysis }) {
  if (!analysis) return <div className="h-64 clay-card animate-pulse" />;

  const signalColors = {
    STRONG_BUY: "text-green-400", 
    BUY:        "text-green-300",
    HOLD:       "text-yellow-400",
    SELL:       "text-red-300", 
    STRONG_SELL:"text-red-500"
  };

  const signalColor = signalColors[analysis.signal] || "text-slate-400";

  return (
    <div className="clay-card p-5">
      <div className="flex justify-between items-center mb-6">
        <div>
          <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest block mb-1">AI Suggestion</span>
          <span className={`text-2xl font-black ${signalColor} tracking-tighter`}>{analysis.signal}</span>
        </div>
        <div className="w-12 h-12 rounded-full border-2 border-slate-800 flex items-center justify-center text-lg font-bold">
          {analysis.overall_score}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 mb-6">
        <PriceLevel label="Entry"  value={analysis.entry_price} color="text-indigo-400" />
        <PriceLevel label="Target" value={analysis.target_price} color="text-green-400" />
        <PriceLevel label="Stop"   value={analysis.stop_loss} color="text-red-400" />
        <PriceLevel label="Horizon" value={analysis.time_horizon} color="text-slate-400" />
      </div>

      <div className="space-y-3 mb-6">
        {analysis.criteria?.map((c, i) => (
          <div key={i} className="text-xs">
            <div className="flex justify-between mb-1">
              <span className="text-slate-400">{c.name}</span>
              <span className="font-mono">{c.score}/10</span>
            </div>
            <div className="h-1 bg-slate-800 rounded-full overflow-hidden">
               <div className="h-full bg-indigo-500/50" style={{ width: `${c.score * 10}%` }} />
            </div>
            <p className="text-[10px] text-slate-500 mt-1 italic">{c.reason}</p>
          </div>
        ))}
      </div>

      {analysis.cited_article && (
        <div className="p-3 rounded-lg bg-indigo-500/10 border border-indigo-500/20">
           <span className="text-[10px] font-bold text-indigo-400 uppercase tracking-widest block mb-1">Evidence Base</span>
           <a href={analysis.cited_article.url} target="_blank" rel="noopener noreferrer" className="text-[11px] text-indigo-200 hover:underline">
             {analysis.cited_article.headline}
           </a>
        </div>
      )}

      <div className="mt-4 pt-4 border-t border-white/5 grid grid-cols-1 gap-3">
         <div className="text-[10px]"><span className="text-red-500 font-bold mr-1">⚠️ RISK:</span> {analysis.key_risk}</div>
         <div className="text-[10px]"><span className="text-green-500 font-bold mr-1">🚀 CATALYST:</span> {analysis.key_catalyst}</div>
      </div>
    </div>
  );
}

function PriceLevel({ label, value, color }) {
  return (
    <div>
      <span className="text-[9px] text-slate-500 uppercase tracking-widest block">{label}</span>
      <span className={`text-sm font-bold ${color}`}>{typeof value === 'number' ? `$${value.toFixed(2)}` : value}</span>
    </div>
  );
}
