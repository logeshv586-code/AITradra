import React from 'react';

export default function MoveExplainer({ reason }) {
  if (!reason) return <div className="h-24 clay-card animate-pulse" />;

  const { explanation, cited_article, confidence, primary_cause } = reason;

  return (
    <div className="clay-card p-4 border-l-4 border-l-indigo-500">
      <div className="flex justify-between items-center mb-2">
        <span className="text-[10px] font-bold text-indigo-400 uppercase tracking-widest">Market Driver: {primary_cause}</span>
        <span className="text-[10px] text-slate-500">{confidence}% Confidence</span>
      </div>
      <p className="text-sm text-slate-200 leading-relaxed mb-3 italic">"{explanation}"</p>
      {cited_article && (
        <a 
          href={cited_article.url} 
          target="_blank" 
          rel="noopener noreferrer"
          className="flex items-center gap-2 text-[11px] text-indigo-300 hover:text-indigo-200 transition-colors"
        >
          📰 <span className="underline truncate">{cited_article.headline}</span>
          <span className="shrink-0 text-slate-500">[{cited_article.source}]</span>
        </a>
      )}
    </div>
  );
}
