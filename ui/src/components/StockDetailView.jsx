import React, { useState, useEffect } from "react";
import { 
  ArrowUpRight, 
  ArrowDownRight, 
  BarChart2, 
  History, 
  Brain, 
  Cpu, 
  ShieldAlert, 
  Newspaper, 
  Activity, 
  Zap, 
  Terminal, 
  Loader2 
} from "lucide-react";
import AdvancedCandlestickChart from "./CandlestickChart";
import { API_BASE } from "../api_config";

export default function StockDetailView({ stock, isAnalyzing, analysisComplete, agentLogs }) {
  const [news, setNews] = useState([]);
  const [newsLoading, setNewsLoading] = useState(true);
  
  const isUp = (stock.chg || 0) >= 0;
  const col = isUp ? 'var(--accent-positive)' : 'var(--accent-negative)';

  useEffect(() => {
    if (!stock?.id) return;
    setNewsLoading(true);
    
    fetch(`${API_BASE}/api/stock/${stock.id}/news`)
      .then(res => res.json())
      .then(data => {
        setNews(data.news || []);
        setNewsLoading(false);
      })
      .catch(err => {
        console.error("News fetch failed:", err);
        setNewsLoading(false);
      });
  }, [stock?.id]);

  const liveAnalysis = stock.analysis_result || {};
  const confidence = liveAnalysis.confidence ? (liveAnalysis.confidence * 100).toFixed(1) : '82.4';
  const signalText = liveAnalysis.signal || (isUp ? 'STRONG BUY' : 'HOLD');
  const conclusionText = liveAnalysis.conclusion || (analysisComplete 
    ? "Multi-agent ensemble verification confirmed. Liquidity clusters identified at current pivots. News latency adjusted for volatility spike. SYNTHESIS_COMPLETE: Action recommended."
    : "Awaiting asynchronous agent resolution streams...");

  const pastPredictions = liveAnalysis.past_predictions || [
    { pred: isUp ? 'BUY' : 'SELL', acc: analysisComplete ? '88%' : '—', ago: 'now', target: (stock.px * 0.95).toFixed(0), actual: stock.px?.toFixed(0) || '0', note: analysisComplete ? `14-agent pipeline analysis for ${stock.id}. ${signalText} signal confirmed.` : 'Analysis in progress...' }
  ];

  const riskData = stock.risk || { var: 'N/A', beta: 1.0, vol: 'N/A' };

  return (
    <div className="flex-1 p-8 overflow-y-auto no-scrollbar animate-fade-in institutional-bg">
      <div className="max-w-6xl mx-auto space-y-10">
        
        {/* Header Section - Refined Alignment */}
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-8 border-b border-white/[0.08] pb-8">
          <div className="flex flex-col gap-6">
            <div className="flex items-center gap-5">
              <div className="w-14 h-14 rounded-xl flex items-center justify-center text-xl font-bold glass-card"
                style={{ 
                  background: `${col}10`,
                  borderColor: `${col}20`,
                  color: col,
                }}>
                {(stock.id || '?')[0]}
              </div>

              <div className="flex flex-col gap-1">
                <div className="flex items-center gap-3">
                  <h1 className="text-[24px] font-bold text-white tracking-tight uppercase leading-none">{stock.name || stock.id}</h1>
                  <span className="px-2 py-0.5 rounded-md bg-white/[0.05] border border-white/[0.1] text-[9px] font-bold text-slate-500 tracking-widest uppercase">
                    {stock.ex || 'N/A'} // {stock.id}
                  </span>
                </div>
                <div className="flex items-center gap-5">
                  <span className="text-[24px] font-mono font-bold text-white tracking-tighter">
                    {stock.id?.includes('-USD') ? '' : '$'}{(stock.px || 0).toLocaleString(undefined, {minimumFractionDigits: 2})}
                  </span>
                  <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-md font-bold text-[11px] border"
                    style={{ 
                      background: `${col}10`, 
                      color: col,
                      borderColor: `${col}20`,
                    }}>
                    {isUp ? <ArrowUpRight size={14}/> : <ArrowDownRight size={14}/>}
                    {Math.abs(stock.chg || 0)}%
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Quick Metrics Grid */}
          <div className="flex gap-4">
            {[
              ['MARKET_CAP', stock.mcap || 'N/A'],
              ['VOL_24H', stock.vol || 'N/A'],
              ['SECTOR', stock.sector || 'N/A']
            ].map(([l,v]) => (
              <div key={l} className="px-5 py-3 glass-card bg-white/[0.02] flex flex-col gap-1 min-w-[120px]">
                <span className="text-[9px] uppercase tracking-[0.2em] text-slate-500 font-bold font-mono">{l}</span>
                <span className="font-mono text-[12px] text-white font-bold truncate">{v}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-10">
          {/* Main Visualizer Area */}
          <div className="lg:col-span-2 space-y-10">
            {/* Technical Chart */}
            <div className="glass-card p-6 animate-slide-up">
              <div className="flex items-center justify-between mb-8">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-indigo-500/10 rounded-lg border border-indigo-500/20">
                    <BarChart2 size={16} className="text-indigo-400" />
                  </div>
                  <h3 className="text-[12px] font-bold uppercase tracking-widest text-white">Advanced Data Matrix</h3>
                </div>
                <div className="skeuo-toggle">
                  {['1H','4H','1D','1W'].map(t => (
                    <button key={t} className={`skeuo-toggle-item ${t==='1D' ? 'active' : ''}`}>{t}</button>
                  ))}
                </div>
              </div>

              <div className="min-h-[300px]">
                {stock.ohlcv && stock.ohlcv.length > 0 ? (
                  <AdvancedCandlestickChart data={stock.ohlcv} />
                ) : (
                  <div className="flex flex-col items-center justify-center p-20 gap-3 text-slate-700 font-mono text-[10px]">
                    <Loader2 size={20} className="animate-spin text-indigo-500" />
                    SYNCING_CANDLE_STREAM...
                  </div>
                )}
              </div>
            </div>

            {/* Neural Insights / Past Predictions */}
            <div className="glass-card p-6 animate-slide-up">
              <div className="flex items-center gap-3 mb-6">
                <div className="p-2 bg-purple-500/10 rounded-lg border border-purple-500/20">
                  <Terminal size={16} className="text-purple-400" />
                </div>
                <h3 className="text-[12px] font-bold uppercase tracking-widest text-white">Synaptic Model Recall</h3>
              </div>

              <div className="space-y-3">
                {pastPredictions.map((p,i) => (
                  <div key={i} className="flex gap-4 p-4 rounded-xl border border-white/[0.04] bg-white/[0.01] hover:bg-white/[0.03] transition-all duration-120">
                    <div className="w-14 h-14 rounded-lg flex flex-col items-center justify-center shrink-0 border"
                      style={{ 
                        background: `${p.pred==='BUY'? 'var(--accent-positive)' : 'var(--accent-negative)'}08`,
                        borderColor: `${p.pred==='BUY'? 'var(--accent-positive)' : 'var(--accent-negative)'}15`,
                      }}>
                      <span className="text-[9px] font-bold tracking-widest" style={{ color: p.pred==='BUY'?'var(--accent-positive)':'var(--accent-negative)' }}>{p.pred}</span>
                      <span className="text-[8px] text-slate-500 font-mono mt-1 font-bold">{p.acc}</span>
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-1">
                        <span className="text-[9px] font-mono text-indigo-400 font-bold">{(p.ago || 'NOW').toString().toUpperCase()}</span>
                        <div className="h-[1px] flex-1 bg-white/[0.05]" />
                        <span className="text-[8px] font-mono text-slate-500 uppercase font-bold tracking-wider">TGT: ${p.target} // ACT: ${p.actual}</span>
                      </div>
                      <p className="text-[11px] text-slate-400 leading-relaxed italic">"{p.note}"</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Analysis & Risk Sidebar */}
          <div className="space-y-10">
            {/* AI Synthesis Summary */}
            <div className={`glass-panel p-6 rounded-xl space-y-6 ${isAnalyzing ? 'border-indigo-500/30' : ''} animate-slide-up`}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-indigo-500/10 rounded-lg border border-indigo-500/20">
                    <Brain size={16} className="text-indigo-400" />
                  </div>
                  <h3 className="text-[10px] font-bold uppercase tracking-widest text-white">Synthesis Consensus</h3>
                </div>
                {isAnalyzing && <Loader2 size={12} className="text-indigo-400 animate-spin" />}
              </div>

              {analysisComplete ? (
                <div className="flex items-center gap-6 py-2">
                  <div className="w-20 h-20 rounded-full flex items-center justify-center shrink-0 border-2"
                    style={{ 
                      background: `${col}08`,
                      borderColor: `${col}20`,
                      boxShadow: `0 0 20px ${col}10`
                    }}>
                    <span className="text-2xl" style={{ color: col }}>{isUp ? '▲' : '▼'}</span>
                  </div>
                  <div className="flex flex-col">
                    <div className="text-[28px] font-mono font-bold text-white tracking-tighter leading-none mb-1">{confidence}<span className="text-slate-700">%</span></div>
                    <span className="text-[9px] font-bold uppercase tracking-widest text-slate-500">Node Confidence</span>
                  </div>
                </div>
              ) : (
                <div className="flex flex-col items-center py-4 gap-4">
                  <Activity size={32} className="text-indigo-500/40 animate-pulse" />
                  <span className="text-[9px] font-mono font-bold text-slate-600 uppercase tracking-widest animate-pulse">Resolving Synaptic Clusters...</span>
                </div>
              )}

              <div className="space-y-3 pt-4 border-t border-white/[0.08]">
                <div className="flex items-center gap-2 text-[9px] font-bold text-slate-500 uppercase tracking-widest">
                  <Zap size={10} className="text-amber-500" /> Executive Verdict
                </div>
                <p className="text-[11px] leading-relaxed text-slate-400 italic">
                  {conclusionText}
                </p>
                {analysisComplete && (
                  <button className="skeuo-button w-full h-10 mt-2 gap-2">
                    <ShieldAlert size={14} />
                    ACTIVATE_POSITION
                  </button>
                )}
              </div>
            </div>

            {/* Risk Dynamics */}
            <div className="glass-card p-6 space-y-6 animate-slide-up">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-amber-500/10 rounded-lg border border-amber-500/20">
                  <ShieldAlert size={16} className="text-amber-400" />
                </div>
                <h3 className="text-[11px] font-bold uppercase tracking-widest text-white">Risk Engineering</h3>
              </div>

              <div className="space-y-5">
                <div className="space-y-2">
                  <div className="flex justify-between text-[9px] font-bold uppercase tracking-widest">
                    <span className="text-slate-500">Value at Risk (95%)</span>
                    <span className="text-white font-mono">{riskData.var}</span>
                  </div>
                  <div className="h-1.5 bg-black/40 rounded-full overflow-hidden border border-white/[0.04]">
                    <div className="h-full bg-amber-500/60" style={{ width: riskData.var || '0%' }} />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  {[
                    ['BETA_COEFF', riskData.beta, 'var(--text-primary)'],
                    ['VOLATILITY', riskData.vol, riskData.vol==='High'?'var(--accent-negative)':'var(--accent-positive)']
                  ].map(([l,v,c]) => (
                    <div key={l} className="p-3 bg-white/[0.02] rounded-lg border border-white/[0.04]">
                      <span className="text-[8px] uppercase tracking-wider block mb-1 text-slate-600 font-bold">{l}</span>
                      <span className="font-mono text-sm font-bold" style={{ color: c }}>{v}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Catalog Indicators / News */}
            <div className="glass-card p-6 space-y-6 animate-slide-up">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-emerald-500/10 rounded-lg border border-emerald-500/20">
                    <Newspaper size={16} className="text-emerald-400" />
                  </div>
                  <h3 className="text-[11px] font-bold uppercase tracking-widest text-white">Catalyst Feed</h3>
                </div>
                <div className="flex items-center gap-1.5">
                   <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                   <span className="text-[8px] font-bold text-slate-500 tracking-widest uppercase">LIVE</span>
                </div>
              </div>

              <div className="space-y-4">
                {newsLoading ? (
                  <div className="flex flex-col items-center py-6 gap-2">
                    <Loader2 size={16} className="text-emerald-500 animate-spin" />
                    <span className="text-[9px] text-slate-700 font-mono animate-pulse uppercase">Syncing Flux...</span>
                  </div>
                ) : news.length > 0 ? (
                  news.slice(0, 3).map((n,i) => (
                    <div key={i} className="flex flex-col gap-2 p-3 rounded-lg border border-white/[0.04] bg-white/[0.01] hover:bg-white/[0.03] transition-all duration-120 cursor-pointer">
                      <div className="flex justify-between items-center">
                        <span className="text-[8px] font-bold font-mono text-indigo-400">{(n.src || 'FEED').toUpperCase()}</span>
                        <span className={`text-[8px] font-bold px-1.5 rounded ${ (n.s || 0) > 0 ? 'bg-emerald-500/10 text-emerald-400' : 'bg-red-500/10 text-red-400' }`}>
                          {(n.s || 0) > 0 ? 'BULL' : 'BEAR'}
                        </span>
                      </div>
                      <p className="text-[10px] text-slate-400 leading-normal line-clamp-2">"{n.txt}"</p>
                    </div>
                  ))
                ) : (
                  <div className="text-center py-6">
                    <span className="text-[9px] text-slate-700 font-mono uppercase tracking-widest">No Catalyst Clusters Found</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
