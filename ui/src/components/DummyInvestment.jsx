import React, { useState, useEffect } from "react";
import { TrendingUp, TrendingDown, DollarSign, Wallet } from "lucide-react";
import { T } from "../theme";

export default function DummyInvestment({ ticker, currentPrice }) {
  const [trade, setTrade] = useState(null);
  const investmentAmount = 1000; // Fixed ₹1000 as per request

  useEffect(() => {
    const savedTrades = JSON.parse(localStorage.getItem("axiom_dummy_trades") || "{}");
    if (savedTrades[ticker]) {
      setTrade(savedTrades[ticker]);
    } else {
      setTrade(null);
    }
  }, [ticker]);

  const handleInvest = () => {
    const newTrade = {
      ticker,
      entryPrice: currentPrice,
      amount: investmentAmount,
      timestamp: new Date().toISOString(),
    };
    const savedTrades = JSON.parse(localStorage.getItem("axiom_dummy_trades") || "{}");
    savedTrades[ticker] = newTrade;
    localStorage.setItem("axiom_dummy_trades", JSON.stringify(savedTrades));
    setTrade(newTrade);
  };

  const handleReset = () => {
    const savedTrades = JSON.parse(localStorage.getItem("axiom_dummy_trades") || "{}");
    delete savedTrades[ticker];
    localStorage.setItem("axiom_dummy_trades", JSON.stringify(savedTrades));
    setTrade(null);
  };

  if (!currentPrice) return null;

  const pl = trade ? ((currentPrice - trade.entryPrice) / trade.entryPrice) * trade.amount : 0;
  const plPct = trade ? ((currentPrice - trade.entryPrice) / trade.entryPrice) * 100 : 0;
  const isProfitable = pl >= 0;

  // Determine liquidity rank based on currency/ticker for display
  const getLiquidityRank = () => {
    if (ticker.endsWith(".NS") || ticker.endsWith(".BO")) return { label: "MODERATE", color: "text-amber-400" };
    if (ticker.includes("-") || ticker.length > 5) return { label: "MED_STABLE", color: "text-indigo-400" };
    return { label: "HIGH_DEEP", color: "text-green-400" };
  };
  const liq = getLiquidityRank();

  return (
    <div className="clay-card p-4 mt-4 border border-white/5 bg-white/5 rounded-xl overflow-hidden relative group">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Wallet size={16} className="text-indigo-400" />
          <h3 className="text-xs font-black tracking-widest text-slate-300 uppercase">Dummy Investment</h3>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-black/40 border border-white/5">
            <div className={`w-1 h-1 rounded-full bg-current ${liq.color} animate-pulse`} />
            <span className={`text-[8px] font-black tracking-widest uppercase ${liq.color}`}>{liq.label} LIQUIDITY</span>
          </div>
          {trade && (
            <button 
              onClick={handleReset}
              className="text-[9px] font-bold text-slate-500 hover:text-white transition-colors uppercase tracking-tighter"
            >
              Reset
            </button>
          )}
        </div>
      </div>

      {!trade ? (
        <div className="flex flex-col gap-3">
          <p className="text-[10px] text-slate-400 leading-relaxed font-medium">
            Test your conviction with a dummy investment of <span className="text-white font-bold">₹1000</span>. 
            AXIOM will track your P/L in real-time.
          </p>
          <button
            onClick={handleInvest}
            className="w-full py-2.5 bg-indigo-500 hover:bg-indigo-400 text-white rounded-lg text-[10px] font-black tracking-[0.2em] transition-all active:scale-[0.98] shadow-lg shadow-indigo-500/20 uppercase"
          >
            Invest ₹1000
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-4">
          <div className="flex flex-col gap-1">
            <span className="text-[9px] text-slate-500 font-bold uppercase tracking-tighter">Entry Price</span>
            <span className="text-sm font-mono font-black text-white">
              ${trade.entryPrice.toLocaleString()}
            </span>
          </div>
          <div className="flex flex-col gap-1 items-end">
            <span className="text-[9px] text-slate-500 font-bold uppercase tracking-tighter">Current P/L</span>
            <div className="flex items-center gap-1">
              {isProfitable ? <TrendingUp size={14} className="text-green-400" /> : <TrendingDown size={14} className="text-red-400" />}
              <span className="text-sm font-mono font-black" style={{ color: isProfitable ? T.buy : T.sell }}>
                {isProfitable ? '+' : ''}₹{pl.toFixed(2)}
              </span>
            </div>
          </div>
          <div className="col-span-2 mt-2 pt-3 border-t border-white/5 flex flex-col gap-3">
             <div className="flex items-center justify-between">
                <div className="flex flex-col gap-0.5">
                  <span className="text-[8px] text-slate-500 font-bold uppercase tracking-tighter">Performance</span>
                  <span className={`text-[10px] font-black ${isProfitable ? 'text-green-500' : 'text-red-500'}`}>
                    {isProfitable ? '🔥' : '❄️'} {plPct.toFixed(2)}%
                  </span>
                </div>
                <div className="text-[8px] text-slate-600 font-mono italic">
                  Opened: {new Date(trade.timestamp).toLocaleTimeString()}
                </div>
             </div>

             {isProfitable && (
               <button className="w-full py-2 bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-500 hover:to-emerald-500 text-white text-[9px] font-black tracking-widest uppercase rounded-md shadow-lg shadow-green-900/20 transition-all active:scale-[0.98]">
                 Convert to Real Account 🚀
               </button>
             )}
          </div>
        </div>
      )}
      
      {/* Decorative background element */}
      <div className="absolute -right-4 -bottom-4 opacity-[0.03] pointer-events-none group-hover:opacity-[0.05] transition-opacity">
        <DollarSign size={80} />
      </div>
    </div>
  );
}
