import React, { useState, useEffect } from 'react';
import MoveExplainer from './MoveExplainer';
import AnalysisCard from './AnalysisCard';
import QuanticInsightView from './QuanticInsightView';
import StockChat from './StockChat';
import FreshnessBadge from './FreshnessBadge';
import DummyInvestment from "./DummyInvestment";
import { PieChart, X, Zap, Activity, ShieldAlert, Cpu, Globe, Search, MessageSquare, TrendingUp, TrendingDown, Loader2 } from 'lucide-react';

import { API_BASE } from "../api_config";

export default function StockDetailPanel({ ticker, onClose }) {
  const tickerId = (typeof ticker === 'string' ? ticker : ticker?.id || '').toUpperCase();
  
  const [data, setData] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [moveReason, setMoveReason] = useState(null);
  const [prediction, setPrediction] = useState(null);
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
    
    const abortController = new AbortController();
    const timeoutId = setTimeout(() => abortController.abort(), 300000); // Extended to 5 minutes to allow deep intelligence generation

    const safeFetch = (url) => 
      fetch(url, { signal: abortController.signal })
        .then(r => {
           if (!r.ok) throw new Error(`HTTP ${r.status}`);
           return r.json().catch(() => null);
        })
        .catch(() => null);
    
    // Separate fetches to prevent peripheral intelligence from blocking core price UI
    safeFetch(`${API_BASE}/api/stock/${tickerId}`).then(stock => {
      setData(stock);
      setLoading(false);
    });

    safeFetch(`${API_BASE}/api/stock/${tickerId}/analysis`).then(setAnalysis);
    safeFetch(`${API_BASE}/api/stock/${tickerId}/explain-move`).then(setMoveReason);
    safeFetch(`${API_BASE}/api/market/predictions`).then(preds => {
      const p = preds?.predictions?.find(x => x.ticker === tickerId);
      setPrediction(p);
    });
    safeFetch(`${API_BASE}/api/knowledge/status`).then(setKnowledgeStatus);
    safeFetch(`${API_BASE}/api/simulation/status`).then(sData => {
      setSimData(sData);
      clearTimeout(timeoutId);
    });

    return () => {
      clearTimeout(timeoutId);
      abortController.abort();
    };
  }, [tickerId]);

  if (loading) return (
    <div className="fixed top-0 right-0 w-full sm:w-[450px] h-full glass-panel z-[100] flex items-center justify-center border-l border-white/[0.08]">
      <div className="text-center space-y-4">
        <Loader2 size={24} className="text-indigo-500 animate-spin mx-auto" />
        <p className="text-[10px] font-mono text-slate-500 tracking-[0.3em] uppercase animate-pulse">Syncing Peripheral Link...</p>
      </div>
    </div>
  );
  
  if (!data) return <div className="fixed top-0 right-0 w-full sm:w-[450px] h-full glass-panel z-[100] p-8 text-red-400 font-mono text-xs">Link error: {tickerId} not found in current sector.</div>;

  const price_data = data.price_data || {};
  const isUp = (price_data.pct_chg || 0) >= 0;
  const col = isUp ? 'var(--accent-positive)' : 'var(--accent-negative)';

  return (
    <div className="fixed top-0 right-0 w-full sm:w-[450px] h-full glass-panel z-[100] overflow-y-auto no-scrollbar slide-in-right border-l border-white/[0.15] bg-[#0B0F14]/95 backdrop-blur-3xl shadow-[-20px_0_40px_rgba(0,0,0,0.4)]">
      <div className="p-8 space-y-10">
        <header className="flex justify-between items-start">
          <div className="space-y-4">
            <div className="flex flex-col gap-1">
              <h2 className="text-[28px] font-bold text-white tracking-tighter uppercase leading-none">{tickerId}</h2>
              <span className="text-[10px] font-bold text-slate-600 tracking-wider uppercase">{data.name}</span>
            </div>
            <div className="flex items-center gap-4">
              <span className="text-[24px] font-mono font-bold text-white tracking-tight">${price_data.px?.toFixed(2)}</span>
              <div className="flex items-center gap-1 px-2 py-0.5 rounded-md font-bold text-[11px] border" style={{ background: `${col}10`, color: col, borderColor: `${col}20` }}>
                {isUp ? <TrendingUp size={12}/> : <TrendingDown size={12}/>}
                {Math.abs(price_data.pct_chg || 0).toFixed(2)}%
              </div>
            </div>
            <div className="flex items-center gap-3">
              <FreshnessBadge label={data.freshness_label} />
              {data.mcap && (
                <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-white/[0.05] border border-white/[0.1]">
                   <span className="text-[8px] font-bold text-slate-500 uppercase tracking-widest">MCAP</span>
                   <span className="text-[9px] font-mono font-bold text-indigo-400 uppercase">{data.mcap}</span>
                </div>
              )}
              {knowledgeStatus && (
                <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-white/[0.05] border border-white/[0.1]">
                   <Globe size={10} className="text-slate-500" />
                   <span className="text-[8px] font-bold text-slate-500 uppercase tracking-widest">{knowledgeStatus.total_ohlcv_records?.toLocaleString()} NODES</span>
                </div>
              )}
            </div>
          </div>
          <button onClick={onClose} className="w-10 h-10 flex items-center justify-center rounded-full bg-white/[0.02] border border-white/[0.08] hover:bg-white/[0.05] transition-all duration-120 text-slate-500 hover:text-white">
            <X size={20} />
          </button>
        </header>

        {/* Today's Range Gauge */}
        <div className="space-y-3">
           <div className="flex justify-between text-[9px] font-bold text-slate-600 uppercase tracking-[0.2em]">
             <span>L: ${price_data.low?.toFixed(2)}</span>
             <span>Intraday Delta</span>
             <span>H: ${price_data.high?.toFixed(2)}</span>
           </div>
           <div className="h-1 bg-black/40 rounded-full relative border border-white/[0.04]">
              <div 
                className="absolute h-full rounded-full transition-all duration-500"
                style={{ 
                  left: `${(((price_data.px || 0) - (price_data.low || 0)) / (Math.max(0.01, (price_data.high || 1) - (price_data.low || 0)))) * 100}%`,
                  width: '6px',
                  background: 'var(--accent-indigo)',
                  boxShadow: '0 0 8px var(--accent-indigo)'
                }}
              />
           </div>
        </div>

        {/* Prediction Matrix */}
        {prediction && (
          <div className="glass-card p-6 bg-white/[0.01] border border-white/[0.08] relative group">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-indigo-500/10 rounded-lg border border-indigo-500/20">
                  <Cpu size={16} className="text-indigo-400" />
                </div>
                <h3 className="text-[10px] font-bold uppercase tracking-[0.2em] text-white">AI Prediction Stream</h3>
              </div>
              <div className="flex items-center gap-1">
                 <div className="w-1.5 h-1.5 rounded-full bg-indigo-500 animate-pulse" />
              </div>
            </div>

            <div className="flex items-center justify-between gap-4">
              <div className="flex flex-col gap-1">
                <span className={`text-[12px] font-bold tracking-widest uppercase flex items-center gap-2 ${prediction.prediction_direction === 'UP' ? 'text-emerald-400' : 'text-red-400'}`}>
                  {prediction.prediction_direction === 'UP' ? <TrendingUp size={14}/> : <TrendingDown size={14}/>}
                  {prediction.prediction_direction}
                </span>
                <span className="text-[9px] text-slate-600 font-bold uppercase tracking-widest">Model Bias</span>
              </div>

              <div className="flex flex-col items-end gap-1">
                <span className="text-[18px] font-bold text-white font-mono tabular-nums leading-none">
                  {prediction.prediction_direction === 'DOWN' ? '-' : '+'}{prediction.expected_move_percent}%
                </span>
                <span className="text-[9px] text-slate-600 font-bold uppercase tracking-widest">Exp. Momentum</span>
              </div>
            </div>

            {/* Simulation Controls - Institutional Stylized */}
            <div className="mt-8 pt-6 border-t border-white/[0.08] space-y-5">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                   <Zap size={12} className="text-amber-500" />
                   <h4 className="text-[9px] font-bold text-slate-500 uppercase tracking-widest">Virtual Terminal</h4>
                </div>
                {simData?.initialized && (
                  <span className="text-[8px] font-mono text-slate-600 font-bold uppercase tracking-widest">BAL: ₹{simData.available_cash.toLocaleString()}</span>
                )}
              </div>
              
              {!simData?.initialized ? (
                <div className="p-4 bg-black/20 rounded-lg border border-dashed border-white/[0.08] text-[9px] text-slate-700 font-mono text-center uppercase tracking-widest">
                  Simulation Cluster Offline
                </div>
              ) : (
                <div className="flex items-center gap-3">
                  <div className="flex-1 relative">
                    <input 
                      type="number"
                      value={buyAmount}
                      onChange={(e) => setBuyAmount(e.target.value)}
                      className="w-full bg-black/40 border border-white/[0.08] rounded-xl pl-4 pr-3 py-2.5 text-white font-mono text-xs focus:outline-none focus:border-indigo-500/40 transition-all placeholder:text-slate-800"
                      placeholder="AMOUNT_INR"
                    />
                  </div>
                  <button 
                    disabled={isBuying}
                    onClick={async () => {
                      setIsBuying(true);
                      try {
                        const shares = parseFloat(buyAmount) / (price_data.px || 0);
                        const res = await fetch(`${API_BASE}/api/simulation/buy`, {
                          method: 'POST',
                          headers: { 'Content-Type': 'application/json' },
                          body: JSON.stringify({ 
                            ticker: tickerId, 
                            shares: shares,
                            prediction: prediction?.prediction_direction,
                            confidence_score: prediction?.confidence_score,
                            monte_carlo_volatility: prediction?.monte_carlo_volatility
                          })
                        });
                        const result = await res.json();
                        if (result.error) alert(result.error);
                        else {
                          setSimData(result);
                          alert(`Transaction Executed: ${tickerId}`);
                        }
                      } catch (e) { console.error(e); }
                      finally { setIsBuying(false); }
                    }}
                    className={`h-10 px-6 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-[10px] tracking-[0.2em] transition-all duration-120 whitespace-nowrap ${isBuying ? 'opacity-50 grayscale cursor-not-allowed' : ''}`}
                  >
                    {isBuying ? '...' : 'EXECUTE'}
                  </button>
                </div>
              )}
            </div>

            <div className="mt-6 space-y-4 pt-6 border-t border-white/[0.08]">
              <div className="space-y-1.5">
                <div className="flex justify-between items-center text-[9px] font-bold uppercase tracking-widest">
                  <span className="text-slate-600">Model Confidence</span>
                  <span className="text-indigo-400">{prediction.confidence_score}%</span>
                </div>
                <div className="h-1 bg-black/40 rounded-full overflow-hidden border border-white/[0.04]">
                  <div className="h-full bg-indigo-500/60 rounded-full transition-all duration-1000" style={{ width: `${prediction.confidence_score}%` }} />
                </div>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-[9px] font-bold text-slate-600 uppercase tracking-widest">Aggregated Risk</span>
                <span className={`px-2 py-0.5 rounded-md text-[8px] font-bold tracking-widest uppercase border ${prediction.risk_level === 'HIGH' ? 'bg-red-500/10 text-red-400 border-red-500/20' : 'bg-green-500/10 text-green-400 border-green-500/20'}`}>
                  {prediction.risk_level}
                </span>
              </div>
            </div>
          </div>
        )}

        <QuanticInsightView ticker={tickerId} quantic={analysis?.quantic} />

        {/* Crowd Sentiment Vector */}
        <div className="glass-panel p-6 space-y-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-emerald-500/10 rounded-lg border border-emerald-500/20">
                <PieChart size={16} className="text-emerald-400" />
              </div>
              <div>
                <h3 className="text-[10px] font-bold uppercase tracking-widest text-white leading-none">Crowd Heuristics</h3>
                <p className="text-[8px] text-slate-600 font-bold uppercase tracking-widest mt-1">Social sentiment velocity</p>
              </div>
            </div>
            <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-white/[0.02] border border-white/[0.06]">
               <Globe size={10} className="text-slate-600" />
               <span className="text-[8px] font-bold text-slate-600 uppercase tracking-widest font-mono">SOCIALLINK_ACTIVE</span>
            </div>
          </div>
          
          <div className="relative h-20 flex items-center justify-center overflow-hidden">
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="w-48 h-24 rounded-t-full border border-white/[0.08] relative overflow-hidden bg-white/[0.01]">
                <div className="absolute bottom-0 left-0 h-full bg-gradient-to-r from-red-500/10 via-amber-500/10 to-emerald-500/10 w-full" />
                <div 
                  className="absolute bottom-0 left-1/2 w-[1px] h-20 bg-white/40 origin-bottom shadow-[0_0_8px_rgba(255,255,255,0.2)] transition-all duration-1000 ease-out z-10"
                  style={{ transform: `translateX(-50%) rotate(${(parseFloat(data.sentiment?.score || 0) * 80)}deg)` }}
                />
                <div className="absolute bottom-0 left-1/2 w-2 h-2 bg-white/80 rounded-full -translate-x-1/2 translate-y-1/2 z-20" />
              </div>
            </div>
          </div>
          
          <div className="flex justify-between text-[8px] font-bold tracking-[0.2em] text-slate-700 uppercase pt-2 border-t border-white/[0.04]">
            <span>Bearish_Void</span>
            <span className="text-indigo-500 animate-pulse">Equilibrium</span>
            <span>Bullish_Wave</span>
          </div>
        </div>

        {/* Supplementary Widgets */}
        <section className="space-y-8">
          <DummyInvestment ticker={tickerId} currentPrice={price_data.px} />
          <MoveExplainer reason={moveReason} />
          <AnalysisCard analysis={analysis} />
          
          <button 
            onClick={() => setChatOpen(!chatOpen)}
            className="w-full h-14 rounded-xl bg-white/[0.02] border border-white/[0.08] hover:bg-white/[0.06] hover:border-white/[0.2] flex items-center justify-center gap-3 group transition-all duration-120"
          >
            <MessageSquare size={16} className="text-indigo-400 group-hover:scale-110 transition-transform" />
            <span className="text-[11px] font-bold text-white uppercase tracking-[0.2em]">{chatOpen ? `Collapse Interface` : `Interactive AI Query`}</span>
            <span className="text-[8px] px-1.5 py-0.5 rounded-md bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 font-mono">AXV4</span>
          </button>
        </section>

        {/* Intelligence Stream */}
        <section className="space-y-6 pt-6 border-t border-white/[0.08]">
          <div className="flex items-center justify-between">
            <h3 className="text-[11px] font-bold text-slate-500 uppercase tracking-widest">Catalyst Corpus</h3>
            <div className="flex items-center gap-2">
               <Activity size={10} className="text-indigo-500/40" />
               <span className="text-[9px] font-mono text-slate-700 uppercase">{data.news?.length || 0} SELECTIONS</span>
            </div>
          </div>
          <div className="space-y-4">
            {data.news?.slice(0, 5).map((n, i) => (
              <a key={i} href={n.url} target="_blank" rel="noopener noreferrer" 
                 className="block p-4 rounded-xl bg-white/[0.01] hover:bg-white/[0.03] transition-all duration-120 border border-white/[0.06] group">
                <div className="flex justify-between items-center mb-2">
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-bold text-indigo-400/80 uppercase tracking-tight">{n.source}</span>
                    <span className="w-1 h-1 rounded-full bg-white/5" />
                    <span className="text-[9px] font-mono text-slate-600 uppercase">{n.published_at}</span>
                  </div>
                  {n.url && (
                    <div className="flex items-center gap-1 text-[9px] font-bold text-slate-700 group-hover:text-cyan-400 transition-colors">
                       <Globe size={10} />
                       <span>SOURCE</span>
                    </div>
                  )}
                </div>
                <div className="text-[13px] font-bold text-slate-300 leading-snug group-hover:text-white transition-colors uppercase tracking-tight line-clamp-2">{n.headline}</div>
              </a>
            ))}
          </div>
        </section>

        {chatOpen && <StockChat ticker={tickerId} context={data} onClose={() => setChatOpen(false)} />}
      </div>
    </div>
  );
}
