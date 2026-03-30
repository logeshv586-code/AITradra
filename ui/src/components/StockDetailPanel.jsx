import React, { useState, useEffect } from 'react';
import MoveExplainer from './MoveExplainer';
import AnalysisCard from './AnalysisCard';
import StockChat from './StockChat';
import FreshnessBadge from './FreshnessBadge';
import DummyInvestment from "./DummyInvestment";
import { PieChart } from 'lucide-react';

import { API_BASE } from "../api_config";

export default function StockDetailPanel({ ticker, onClose }) {
  const tickerId = (typeof ticker === 'string' ? ticker : ticker?.id || '').toUpperCase();
  
  const [data, setData] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [moveReason, setMoveReason] = useState(null);
  const [prediction, setPrediction] = useState(null);
  const [risk, setRisk] = useState(null);
  const [chatOpen, setChatOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [knowledgeStatus, setKnowledgeStatus] = useState(null);
  const [buyAmount, setBuyAmount] = useState("1000");
  const [isBuying, setIsBuying] = useState(false);
  const [simData, setSimData] = useState(null);

  useEffect(() => {
    if (!tickerId) return;
    setLoading(true);
    setChatOpen(false);
    // Load in parallel
    Promise.all([
      fetch(`${API_BASE}/api/stock/${tickerId}`).then(r => r.json()),
      fetch(`${API_BASE}/api/stock/${tickerId}/analysis`).then(r => r.json()),
      fetch(`${API_BASE}/api/stock/${tickerId}/explain-move`).then(r => r.json()),
      fetch(`${API_BASE}/api/market/predictions`).then(r => r.json()),
      fetch(`${API_BASE}/api/stock/${tickerId}/risk`).then(r => r.json()),
      fetch(`${API_BASE}/api/knowledge/status`).then(r => r.json()).catch(() => null),
      fetch(`${API_BASE}/api/simulation/status`).then(r => r.json()).catch(() => null),
    ]).then(([stock, analysis, reason, preds, riskData, kStatus, sData]) => {
      setData(stock);
      setAnalysis(analysis);
      setMoveReason(reason);
      setRisk(riskData);
      setKnowledgeStatus(kStatus);
      setSimData(sData);
      
      const p = preds.predictions?.find(x => x.ticker === tickerId);
      setPrediction(p);
      
      setLoading(false);
    }).catch(err => {
      console.error("Failed to load stock data", err);
      setLoading(false);
    });
  }, [tickerId]);

  if (loading) return (
    <div className="fixed top-0 right-0 w-full sm:w-[450px] h-full clay-panel z-[100] flex items-center justify-center">
      <div className="text-center">
        <div className="text-indigo-400 animate-pulse text-lg mb-2">⚡</div>
        <div className="text-indigo-400 animate-pulse text-xs font-mono">Synchronizing Intelligence...</div>
        <div className="text-slate-600 text-[10px] mt-1 font-mono">RAG + LLM Pipeline Active</div>
      </div>
    </div>
  );
  if (!data) return <div className="p-8 text-red-400">Failed to establish link with {tickerId}</div>;

  const { price_data } = data;

  return (
    <div className="fixed top-0 right-0 w-full sm:w-[450px] h-full clay-panel z-[100] overflow-y-auto slide-in-right">
      <div className="p-6">
        <header className="flex justify-between items-start mb-6">
          <div>
            <h2 className="text-3xl font-bold font-mono">{tickerId}</h2>
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
        <div className="mb-6">
           <div className="flex justify-between text-[9px] text-slate-500 mb-1 uppercase tracking-[0.2em]">
             <span>L: ${price_data.low?.toFixed(2)}</span>
             <span>Intraday Range</span>
             <span>H: ${price_data.high?.toFixed(2)}</span>
           </div>
           <div className="h-1 bg-slate-800 rounded-full relative">
              <div 
                className="absolute h-full bg-indigo-500 rounded-full shadow-[0_0_8px_rgba(99,102,241,0.5)]"
                style={{ 
                  left: `${((price_data.px - price_data.low) / (Math.max(0.01, price_data.high - price_data.low))) * 100}%`,
                  width: '4px'
                }}
              />
           </div>
        </div>

        {/* OMNI-AXIOM Prediction Block */}
        {prediction && (
          <div className="clay-card p-4 mb-6 relative overflow-hidden group border-indigo-500/20">
            <div className="absolute top-0 right-0 p-3 opacity-5 group-hover:opacity-10 transition-opacity">
              <span className="text-4xl">🧠</span>
            </div>
            <div className="flex items-center gap-2 mb-4">
              <div className="p-1.5 bg-indigo-500/10 rounded-lg border border-indigo-500/20">
                <div className="w-2 h-2 rounded-full bg-indigo-500 animate-pulse" />
              </div>
              <h3 className="text-[10px] font-black uppercase tracking-[0.25em] text-indigo-300">AI Prediction Engine</h3>
            </div>

            <div className="flex items-center justify-between gap-4">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className={`text-xl font-black ${prediction.prediction_direction === 'UP' ? 'text-green-400' : prediction.prediction_direction === 'DOWN' ? 'text-red-400' : 'text-amber-400'}`}>
                    {prediction.prediction_direction === 'UP' ? '▲' : prediction.prediction_direction === 'DOWN' ? '▼' : '▬'}
                    <span className="ml-1 uppercase tracking-tighter">{prediction.prediction_direction}</span>
                  </span>
                </div>
                <div className="text-[10px] text-slate-500 font-mono uppercase tracking-widest">Consensus Goal</div>
              </div>

              <div className="text-right space-y-1">
                <div className="text-xl font-black text-white font-mono">
                  {prediction.prediction_direction === 'DOWN' ? '-' : '+'}{prediction.expected_move_percent}%
                </div>
                <div className="text-[10px] text-slate-500 font-mono uppercase tracking-widest">Exp. Volatility</div>
              </div>
            </div>

            {/* VIRTUAL INVESTMENT TERMINAL */}
            <div className="mt-4 pt-4 border-t border-white/10 space-y-4">
              <div className="flex items-center justify-between">
                <h4 className="text-[9px] font-black text-indigo-300 uppercase tracking-widest">💰 Virtual Investment Terminal</h4>
                {simData?.initialized && (
                  <span className="text-[8px] font-mono text-slate-500 uppercase">Avail: ₹{simData.available_cash.toFixed(2)}</span>
                )}
              </div>
              
              {!simData?.initialized ? (
                <div className="text-[9px] text-slate-500 font-mono py-2 italic">
                  * Simulation not initialized. Visit Portfolio tab to start.
                </div>
              ) : (
                <div className="flex items-center gap-2">
                  <div className="flex-1 relative">
                    <span className="absolute left-3 top-1/2 -translate-y-1/2 text-[10px] text-slate-500">₹</span>
                    <input 
                      type="number"
                      value={buyAmount}
                      onChange={(e) => setBuyAmount(e.target.value)}
                      className="w-full bg-black/40 border border-white/10 rounded-lg pl-6 pr-3 py-2 text-white font-mono text-xs focus:outline-none focus:border-indigo-500/50"
                      placeholder="Amount"
                    />
                  </div>
                  <button 
                    disabled={isBuying}
                    onClick={async () => {
                      setIsBuying(true);
                      try {
                        const res = await fetch(`${API_BASE}/api/simulation/buy`, {
                          method: 'POST',
                          headers: { 'Content-Type': 'application/json' },
                          body: JSON.stringify({ 
                            ticker: tickerId, 
                            amount: parseFloat(buyAmount),
                            prediction: prediction?.prediction_direction
                          })
                        });
                        const result = await res.json();
                        if (result.error) alert(result.error);
                        else {
                          setSimData(result);
                          alert(`Success! Bought ${tickerId} with virtual funds.`);
                        }
                      } catch (e) { console.error(e); }
                      finally { setIsBuying(false); }
                    }}
                    className={`clay-badge-action px-4 py-2 flex items-center gap-2 ${isBuying ? 'opacity-50 grayscale' : ''}`}
                    style={{ background: 'rgba(99,102,241,0.15)', borderColor: 'rgba(99,102,241,0.3)', color: '#818cf8' }}
                  >
                    {isBuying ? '...' : 'BUY'}
                  </button>
                </div>
              )}
            </div>

            <div className="mt-4 pt-4 border-t border-white/5 space-y-3">
              <div className="space-y-1.5">
                <div className="flex justify-between items-center text-[9px] font-black uppercase tracking-widest">
                  <span className="text-slate-500">Node Confidence</span>
                  <span className="text-indigo-400">{prediction.confidence_score}%</span>
                </div>
                <div className="h-1 bg-black/40 rounded-full overflow-hidden">
                  <div className="h-full bg-indigo-500 rounded-full transition-all duration-1000" style={{ width: `${prediction.confidence_score}%` }} />
                </div>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-[9px] font-black text-slate-500 uppercase tracking-widest">Risk Exposure</span>
                <span className={`px-2 py-0.5 rounded text-[8px] font-black tracking-widest ${prediction.risk_level === 'HIGH' ? 'bg-red-500/10 text-red-400 border border-red-500/20' : 'bg-green-500/10 text-green-400 border border-green-500/20'}`}>
                  {prediction.risk_level}
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Sentiment Gauge */}
        <div className="clay-card p-6 mb-6 border border-white/5 bg-white/5 rounded-xl">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400">
                <PieChart size={18} />
              </div>
              <div>
                <h3 className="text-xs font-black tracking-widest text-white uppercase">Social Sentiment</h3>
                <p className="text-[10px] text-slate-500 font-bold tracking-tighter uppercase grayscale mt-0.5">Crowd conviction metrics</p>
              </div>
            </div>
          </div>
          
          <div className="relative h-24 flex items-center justify-center">
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="w-32 h-16 rounded-t-full border-4 border-slate-800 relative overflow-hidden">
                <div className="absolute bottom-0 left-0 h-full bg-gradient-to-r from-red-500 via-yellow-400 to-green-500 opacity-20 w-full" />
                <div 
                  className="absolute bottom-0 left-1/2 w-1 h-14 bg-white origin-bottom -translate-x-1/2 transition-transform duration-1000 ease-out z-10"
                  style={{ transform: `translateX(-50%) rotate(${(parseFloat(data.sentiment?.score || 0) * 90)}deg)` }}
                />
                <div className="absolute bottom-0 left-1/2 w-3 h-3 bg-white rounded-full -translate-x-1/2 translate-y-1/2 z-20" />
              </div>
            </div>
          </div>
          
          <div className="flex justify-between mt-2 text-[10px] font-black tracking-widest text-slate-500 uppercase">
            <span>Bearish</span>
            <span className="text-indigo-400">Neutral</span>
            <span>Bullish</span>
          </div>
        </div>

        <DummyInvestment ticker={tickerId} currentPrice={price_data.px} />

        <section className="space-y-6 mt-6">
          <MoveExplainer reason={moveReason} />
          <AnalysisCard analysis={analysis} />
          
          {/* LLM Chat Button — creates a new AI session for this stock */}
          <button 
            onClick={() => setChatOpen(!chatOpen)}
            className="w-full btn-primary py-3 flex items-center justify-center gap-2 group"
          >
            <span className="group-hover:scale-110 transition-transform">💬</span>
            {chatOpen ? `Close AI Chat` : `Ask AI about ${tickerId}`}
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

        {chatOpen && <StockChat ticker={tickerId} context={data} onClose={() => setChatOpen(false)} />}
      </div>
    </div>
  );
}
