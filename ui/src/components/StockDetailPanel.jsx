import React, { useState, useEffect } from 'react';
import MoveExplainer from './MoveExplainer';
import AnalysisCard from './AnalysisCard';
import StockChat from './StockChat';
import FreshnessBadge from './FreshnessBadge';

const API_BASE = "http://localhost:8000";

export default function StockDetailPanel({ ticker, onClose }) {
  const [data, setData] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [moveReason, setMoveReason] = useState(null);
  const [chatOpen, setChatOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [knowledgeStatus, setKnowledgeStatus] = useState(null);

  useEffect(() => {
    setLoading(true);
    setChatOpen(false);
    // Load in parallel
    Promise.all([
      fetch(`${API_BASE}/api/stock/${ticker}`).then(r => r.json()),
      fetch(`${API_BASE}/api/stock/${ticker}/analysis`).then(r => r.json()),
      fetch(`${API_BASE}/api/stock/${ticker}/explain-move`).then(r => r.json()),
      fetch(`${API_BASE}/api/knowledge/status`).then(r => r.json()).catch(() => null),
    ]).then(([stock, analysis, reason, kStatus]) => {
      setData(stock);
      setAnalysis(analysis);
      setMoveReason(reason);
      setKnowledgeStatus(kStatus);
      setLoading(false);
    }).catch(err => {
      console.error("Failed to load stock data", err);
      setLoading(false);
    });
  }, [ticker]);

  if (loading) return (
    <div className="fixed top-0 right-0 w-full sm:w-[450px] h-full clay-panel z-[100] flex items-center justify-center">
      <div className="text-center">
        <div className="text-indigo-400 animate-pulse text-lg mb-2">⚡</div>
        <div className="text-indigo-400 animate-pulse text-xs font-mono">Synchronizing Intelligence...</div>
        <div className="text-slate-600 text-[10px] mt-1 font-mono">RAG + LLM Pipeline Active</div>
      </div>
    </div>
  );
  if (!data) return <div className="p-8 text-red-400">Failed to establish link with {ticker}</div>;

  const { price_data } = data;

  return (
    <div className="fixed top-0 right-0 w-full sm:w-[450px] h-full clay-panel z-[100] overflow-y-auto slide-in-right">
      <div className="p-6">
        <header className="flex justify-between items-start mb-6">
          <div>
            <h2 className="text-3xl font-bold font-mono">{ticker}</h2>
            <div className="flex items-center gap-2 mt-1">
              <span className="text-2xl text-white">${price_data.px?.toFixed(2)}</span>
              <span className={price_data.chg >= 0 ? 'text-green-400' : 'text-red-400'}>
                {price_data.chg >= 0 ? '▲' : '▼'} {Math.abs(price_data.pct_chg)?.toFixed(2)}%
              </span>
            </div>
            <div className="flex items-center gap-2 mt-1">
              <FreshnessBadge label={data.freshness_label} />
              {knowledgeStatus && (
                <span className="text-[8px] px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 font-mono">
                  📚 {knowledgeStatus.total_ohlcv_records?.toLocaleString()} records
                </span>
              )}
            </div>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-white/10 rounded-full transition-colors text-slate-400 hover:text-white">
            ✕
          </button>
        </header>

        {/* Today's Range */}
        <div className="mb-8">
           <div className="flex justify-between text-[10px] text-slate-500 mb-1 uppercase tracking-widest">
             <span>L: ${price_data.low?.toFixed(2)}</span>
             <span>Today's Range</span>
             <span>H: ${price_data.high?.toFixed(2)}</span>
           </div>
           <div className="h-1.5 bg-slate-800 rounded-full relative">
              <div 
                className="absolute h-full bg-indigo-500 rounded-full"
                style={{ 
                  left: `${((price_data.px - price_data.low) / (price_data.high - price_data.low)) * 100}%`,
                  width: '4px'
                }}
              />
           </div>
        </div>

        <section className="space-y-6">
          <MoveExplainer reason={moveReason} />
          <AnalysisCard analysis={analysis} />
          
          {/* LLM Chat Button — creates a new AI session for this stock */}
          <button 
            onClick={() => setChatOpen(!chatOpen)}
            className="w-full btn-primary py-3 flex items-center justify-center gap-2 group"
          >
            <span className="group-hover:scale-110 transition-transform">💬</span>
            {chatOpen ? `Close AI Chat` : `Ask AI about ${ticker}`}
            <span className="text-[9px] ml-1 px-2 py-0.5 rounded-full bg-green-500/10 text-green-400 border border-green-500/20">
              LLM
            </span>
          </button>
        </section>

        {/* News Intelligence Feed with clickable source links */}
        <section className="mt-8">
          <h3 className="text-sm font-bold text-slate-400 uppercase tracking-widest mb-4">
            Intelligence Feed
            {data.news && (
              <span className="text-[9px] ml-2 text-indigo-400 normal-case font-normal">
                {data.news.length} articles
              </span>
            )}
          </h3>
          <div className="space-y-4">
            {data.news?.map((n, i) => (
              <a key={i} href={n.url} target="_blank" rel="noopener noreferrer" 
                 className="block p-3 rounded-xl bg-white/5 hover:bg-white/10 transition-colors border border-white/5">
                <div className="flex justify-between items-center mb-1">
                  <span className="text-[10px] text-indigo-400">{n.source} • {n.published_at}</span>
                  {n.url && (
                    <span className="text-[9px] text-cyan-400">🔗 Verify</span>
                  )}
                </div>
                <div className="text-sm leading-snug">{n.headline}</div>
                {n.summary && (
                  <div className="text-[10px] text-slate-500 mt-1 line-clamp-2">{n.summary}</div>
                )}
              </a>
            ))}
          </div>
        </section>

        {chatOpen && <StockChat ticker={ticker} context={data} onClose={() => setChatOpen(false)} />}
      </div>
    </div>
  );
}
