import React from "react";
import { ArrowUpRight, ArrowDownRight, BarChart2, History, Brain, Cpu, ShieldAlert, Newspaper } from "lucide-react";
import { T } from "../theme";
import { NEWS, MEMORIES } from "../data";
import { GlassCard } from "./Shared";
import AdvancedCandlestickChart from "./CandlestickChart";

export default function StockDetailView({ stock, isAnalyzing, analysisComplete, agentLogs }) {
  const isUp = stock.chg >= 0;
  const col = isUp ? T.buy : T.sell;
  const dir = isUp ? '▲' : '▼';
  const news = NEWS[stock.id] || NEWS['NVDA'];

  return (
    <div className="flex-1 p-8 overflow-y-auto">
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
          <div>
            <div className="flex items-center gap-4 mb-2">
              <h1 className="text-4xl font-bold text-white text-shadow-glow tracking-tight">{stock.name}</h1>
              <span className="px-2.5 py-1 rounded-md text-xs font-mono font-bold" style={{ background: T.glass2, color: T.muted, border:`1px solid ${T.border}` }}>
                {stock.ex}:{stock.id}
              </span>
            </div>
            <div className="flex items-baseline gap-4">
              <span className="text-3xl font-mono font-bold text-white tracking-tight">${stock.px.toFixed(2)}</span>
              <span className="font-bold flex items-center gap-1 text-xl" style={{ color: col, textShadow: `0 0 15px ${col}80` }}>
                {isUp ? <ArrowUpRight size={22}/> : <ArrowDownRight size={22}/>}
                {Math.abs(stock.chg)}%
              </span>
            </div>
          </div>
          <GlassCard className="flex gap-6 text-sm p-4 rounded-xl">
            {[['Mkt Cap',stock.mcap],['Volume',stock.vol],['Sector',stock.sector]].map(([l,v], i) => (
              <React.Fragment key={l}>
                <div className="flex flex-col items-start">
                  <span className="text-[10px] uppercase tracking-widest mb-1 text-slate-400 font-bold">{l}</span>
                  <span className="font-mono text-base text-white">{v}</span>
                </div>
                {i < 2 && <div className="w-px bg-white/10" />}
              </React.Fragment>
            ))}
          </GlassCard>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column: Chart + Memory */}
          <div className="lg:col-span-2 space-y-6">
            <div className="clay-card p-5">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-xs uppercase tracking-widest text-slate-400 font-bold flex items-center gap-2">
                  <BarChart2 size={14}/> Price Action & Technicals
                </h3>
              </div>
              <AdvancedCandlestickChart data={stock.ohlcv} />
            </div>

            <div className="clay-card p-5">
              <h3 className="text-xs uppercase tracking-widest text-slate-400 font-bold flex items-center gap-2 mb-4">
                <History size={14} /> Episodic Memory Recall
              </h3>
              <div className="space-y-3">
                {MEMORIES.episodic.map((p,i) => (
                  <div key={i} className="flex gap-4 p-3.5 rounded-xl transition-all hover:bg-white/5 border border-transparent hover:border-white/10" style={{ background: 'rgba(0,0,0,0.2)' }}>
                    <div className="w-14 h-14 rounded-xl flex flex-col items-center justify-center flex-shrink-0"
                      style={{ background: `${p.pred==='BUY'?T.buy:T.sell}10`, border:`1px solid ${p.pred==='BUY'?T.buy:T.sell}40`, boxShadow: `0 0 15px ${p.pred==='BUY'?T.buy:T.sell}20` }}>
                      <span className="text-sm font-bold tracking-wider" style={{ color: p.pred==='BUY'?T.buy:T.sell }}>{p.pred}</span>
                      <span className="text-[10px] text-slate-300 mt-0.5">{p.acc}</span>
                    </div>
                    <div>
                      <div className="text-xs text-slate-400 mb-1 font-mono">
                        {p.ago} · Tgt: ${p.target} · Act: ${p.actual}
                      </div>
                      <p className="text-sm text-slate-200 leading-snug">"{p.note}"</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Right Column */}
          <div className="space-y-6">
            {/* AI Prediction */}
            <div className="clay-card relative overflow-hidden group">
              {isAnalyzing && (
                <div className="absolute inset-0 flex flex-col items-center justify-center z-20 backdrop-blur-md bg-black/60">
                  <Cpu size={32} className="animate-pulse mb-3" style={{ color: T.ai, filter:`drop-shadow(0 0 10px ${T.ai})` }} />
                  <span className="text-xs font-mono font-bold tracking-widest" style={{ color: T.ai }}>SYNTHESIZING...</span>
                </div>
              )}
              <div className="p-5 border-b border-white/5 bg-gradient-to-br from-white/5 to-transparent">
                <h3 className="text-[10px] uppercase tracking-widest text-slate-400 font-bold mb-5 flex items-center gap-2">
                  <Brain size={14} style={{ color: T.purple }} /> ML Ensemble Output
                </h3>
                {analysisComplete ? (
                  <div className="flex items-center gap-5">
                    <div className="w-20 h-20 rounded-full flex items-center justify-center text-xl font-bold border-2 shadow-2xl"
                      style={{ borderColor: col, color: col, background: `${col}15`, boxShadow: `0 0 30px ${col}40` }}>
                      {dir}
                    </div>
                    <div>
                      <div className="text-4xl font-mono font-bold text-white text-shadow-glow mb-1">82%</div>
                      <div className="text-[10px] uppercase tracking-widest text-slate-400">Confidence</div>
                    </div>
                  </div>
                ) : (
                  <div className="opacity-30 flex items-center gap-5 grayscale">
                    <div className="w-20 h-20 rounded-full border-2 border-slate-500 flex items-center justify-center">---</div>
                    <div><div className="text-4xl font-mono font-bold text-white">--%</div><div className="text-[10px] uppercase text-slate-400">Confidence</div></div>
                  </div>
                )}
              </div>
              <div className="p-5 bg-black/20">
                <div className="text-[10px] uppercase tracking-widest mb-2 text-slate-400 font-bold">Reasoning Chain</div>
                <p className="text-xs leading-relaxed text-slate-300">
                  {analysisComplete
                    ? `Ensemble (LSTM+XGBoost) strongly confirms ${isUp?'bullish':'bearish'} bias. Momentum indicators (RSI/MACD) aligning. News sentiment highlights institutional accumulation. Self-critique validation passed across all agent nodes.`
                    : 'Awaiting pipeline resolution...'}
                </p>
              </div>
            </div>

            {/* Risk */}
            <div className="clay-card p-5">
              <h3 className="text-[10px] uppercase tracking-widest text-slate-400 font-bold mb-4 flex items-center gap-2">
                <ShieldAlert size={14} style={{ color: T.warn }} /> Risk Profile
              </h3>
              <div className="space-y-4">
                <div>
                  <div className="flex justify-between text-xs mb-1.5 font-bold">
                    <span className="text-slate-400">Value at Risk (95%)</span>
                    <span className="font-mono text-white">{stock.risk.var}</span>
                  </div>
                  <div className="w-full h-2 rounded-full overflow-hidden bg-black/50 border border-white/5">
                    <div className="h-full rounded-full" style={{ width: stock.risk.var, background: T.warn, boxShadow: `0 0 10px ${T.warn}` }}/>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-3 pt-1">
                  {[['Beta',stock.risk.beta,T.text],['Volatility',stock.risk.vol,stock.risk.vol==='High'?T.sell:T.buy]].map(([l,v,c]) => (
                    <div key={l} className="p-3 rounded-xl bg-black/30 border border-white/5 shadow-[inset_2px_2px_5px_rgba(0,0,0,0.5)]">
                      <span className="text-[10px] uppercase tracking-widest block mb-1 text-slate-400">{l}</span>
                      <span className="font-mono text-lg font-bold" style={{ color: c, textShadow: `0 0 10px ${c}60` }}>{v}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* News */}
            <div className="clay-card p-5">
              <h3 className="text-[10px] uppercase tracking-widest text-slate-400 font-bold mb-4 flex items-center gap-2">
                <Newspaper size={14} style={{ color: T.aiLight }} /> Real-time Catalyst Feed
              </h3>
              <div className="space-y-4">
                {news.map((n,i) => (
                  <div key={i} className="pb-4 last:pb-0 border-b border-white/5 last:border-0 hover:bg-white/5 transition-colors p-2 rounded-lg cursor-pointer">
                    <div className="flex justify-between items-center mb-1.5">
                      <span className="text-[10px] font-mono text-slate-400">{n.src} · {n.t}</span>
                      <span className="text-[9px] font-bold px-2 py-0.5 rounded-md tracking-wider flex items-center gap-1"
                        style={{ background:`${n.s>0?T.buy:T.sell}15`, color:n.s>0?T.buy:T.sell, border: `1px solid ${n.s>0?T.buy:T.sell}40` }}>
                        {n.s>0 ? <ArrowUpRight size={10}/> : <ArrowDownRight size={10}/>}
                        {n.s>0?'BULLISH IMPACT':'BEARISH IMPACT'}
                      </span>
                    </div>
                    <p className="text-xs leading-relaxed text-slate-200">{n.txt}</p>
                    <a href="#" className="text-[10px] text-indigo-400 hover:text-indigo-300 mt-2 inline-block font-medium">Read Full Report →</a>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
