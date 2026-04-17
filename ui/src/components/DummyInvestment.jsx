import React, { useState } from "react";
import { TrendingUp, TrendingDown, DollarSign, Wallet, Activity, ShieldCheck, Zap } from "lucide-react";

function loadSavedTrades() {
  try {
    return JSON.parse(localStorage.getItem("axiom_dummy_trades") || "{}");
  } catch {
    return {};
  }
}

export default function DummyInvestment({ ticker, currentPrice }) {
  const [savedTrades, setSavedTrades] = useState(loadSavedTrades);
  const trade = savedTrades[ticker] || null;
  const investmentAmount = 1000;

  const handleInvest = () => {
    const newTrade = {
      ticker,
      entryPrice: currentPrice,
      amount: investmentAmount,
      timestamp: new Date().toISOString(),
    };
    const nextTrades = { ...savedTrades, [ticker]: newTrade };
    localStorage.setItem("axiom_dummy_trades", JSON.stringify(nextTrades));
    setSavedTrades(nextTrades);
  };

  const handleReset = () => {
    const nextTrades = { ...savedTrades };
    delete nextTrades[ticker];
    localStorage.setItem("axiom_dummy_trades", JSON.stringify(nextTrades));
    setSavedTrades(nextTrades);
  };

  if (!currentPrice) return null;

  const pl = trade ? ((currentPrice - trade.entryPrice) / trade.entryPrice) * trade.amount : 0;
  const plPct = trade ? ((currentPrice - trade.entryPrice) / trade.entryPrice) * 100 : 0;
  const isProfitable = pl >= 0;
  const col = isProfitable ? 'var(--accent-positive)' : 'var(--accent-negative)';

  const getLiquidityRank = () => {
    if (ticker.endsWith(".NS") || ticker.endsWith(".BO")) return { label: "MODERATE", color: "text-amber-400" };
    if (ticker.includes("-") || ticker.length > 5) return { label: "MED_STABLE", color: "text-indigo-400" };
    return { label: "HIGH_DEEP", color: "text-emerald-400" };
  };
  const liq = getLiquidityRank();

  return (
    <div className="glass-card p-6 border border-white/[0.08] bg-white/[0.01] relative group overflow-hidden">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center shadow-lg">
            <Wallet size={16} className="text-indigo-400" />
          </div>
          <div className="flex flex-col gap-0.5">
            <h3 className="text-[10px] font-bold text-white uppercase tracking-widest leading-none">Virtual Agent</h3>
            <span className="text-[8px] font-bold text-slate-600 uppercase tracking-widest leading-none">Simulation Layer</span>
          </div>
        </div>
        
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 px-2 py-0.5 rounded-md bg-black/40 border border-white/[0.06]">
            <div className={`w-1 h-1 rounded-full bg-current ${liq.color} animate-pulse`} />
            <span className={`text-[8px] font-bold tracking-widest uppercase ${liq.color}`}>{liq.label}_LIQ</span>
          </div>
          {trade && (
            <button 
              onClick={handleReset}
              className="text-[9px] font-bold text-slate-700 hover:text-white transition-all uppercase tracking-widest border-b border-transparent hover:border-white/20"
            >
              Reset
            </button>
          )}
        </div>
      </div>

      {!trade ? (
        <div className="flex flex-col gap-5">
          <p className="text-[11px] text-slate-500 leading-relaxed font-medium italic opacity-80">
            "Audit your convictions with a shadow allocation of <span className="text-white font-bold not-italic">₹1000</span>. 
            AXIOM will track real-time drift metrics."
          </p>
          <button
            onClick={handleInvest}
            className="w-full h-10 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-[10px] font-bold tracking-[0.25em] transition-all duration-120 active:scale-[0.98] shadow-lg shadow-indigo-900/20 uppercase"
          >
            Deploy ₹1000
          </button>
        </div>
      ) : (
        <div className="space-y-6">
          <div className="grid grid-cols-2 gap-6">
            <div className="flex flex-col gap-1">
              <span className="text-[8px] font-bold text-slate-600 uppercase tracking-widest">Entry_Point</span>
              <span className="text-[14px] font-mono font-bold text-white tabular-nums leading-none">
                ${trade.entryPrice.toLocaleString()}
              </span>
            </div>
            <div className="flex flex-col gap-1 items-end">
              <span className="text-[8px] font-bold text-slate-600 uppercase tracking-widest">Real-time_PL</span>
              <div className="flex items-center gap-2">
                <span className="text-[14px] font-mono font-bold tabular-nums leading-none" style={{ color: col }}>
                  {isProfitable ? '+' : ''}₹{pl.toFixed(2)}
                </span>
                {isProfitable ? <TrendingUp size={12} className="text-emerald-500" /> : <TrendingDown size={12} className="text-red-500" />}
              </div>
            </div>
          </div>

          <div className="pt-4 border-t border-white/[0.08] space-y-4">
             <div className="flex items-center justify-between">
                <div className="flex flex-col gap-1">
                  <span className="text-[8px] font-bold text-slate-700 uppercase tracking-widest leading-none">V-Performance</span>
                  <div className="flex items-center gap-2">
                     <span className={`text-[12px] font-bold font-mono ${isProfitable ? 'text-emerald-400' : 'text-red-400'}`}>
                       {isProfitable ? '+' : ''}{plPct.toFixed(2)}%
                     </span>
                     <div className="w-1.5 h-1.5 rounded-full" style={{ background: col, boxShadow: `0 0 4px ${col}` }} />
                  </div>
                </div>
                <div className="flex flex-col items-end gap-1">
                   <span className="text-[8px] font-bold text-slate-700 uppercase tracking-widest leading-none font-mono">Timestamp</span>
                   <span className="text-[9px] text-slate-500 font-mono italic">
                    {new Date(trade.timestamp).toLocaleTimeString([], { hour12: false })}
                   </span>
                </div>
             </div>

             {isProfitable && (
               <button className="w-full h-10 bg-emerald-600 hover:bg-emerald-500 text-white text-[10px] font-bold tracking-widest uppercase rounded-xl transition-all duration-120 flex items-center justify-center gap-3">
                 <Zap size={14} fill="white" /> Convert to Real Segment
               </button>
             )}
          </div>
        </div>
      )}
      
      {/* Structural Decorator */}
      <div className="absolute -right-4 -bottom-4 opacity-[0.02] pointer-events-none group-hover:opacity-[0.04] transition-opacity duration-300">
        <DollarSign size={96} />
      </div>
    </div>
  );
}
