import React, { useState, useEffect } from "react";
import { Coins, Loader2, Shield, Plus, Minus, Search, Target, Zap, ArrowUpRight } from "lucide-react";
import { API_BASE } from "../api_config";

export default function VirtualPortfolioView({ onSelect }) {
  const [data, setData] = useState(null);
  const [intel, setIntel] = useState(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [inputs, setInputs] = useState({});

  const loadData = async () => {
    try {
      const [res1, res2] = await Promise.all([
        fetch(`${API_BASE}/api/simulation/status`),
        fetch(`${API_BASE}/api/intel/overview`)
      ]);
      if (res1.ok) setData((await res1.json()).status || {});
      if (res2.ok) setIntel(await res2.json());
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const id = setInterval(loadData, 10_000);
    return () => clearInterval(id);
  }, []);

  const handleInit = async () => {
    setActionLoading(true);
    try {
      await fetch(`${API_BASE}/api/simulation/init`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ initial_balance: 100000 })
      });
      await loadData();
    } finally {
       setActionLoading(false);
    }
  };

  const handleTrade = async (type, ticker) => {
    const qty = parseInt(inputs[ticker]) || 1;
    setActionLoading(true);
    try {
      await fetch(`${API_BASE}/api/simulation/${type}`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ticker: ticker.toUpperCase(), shares: qty })
      });
      setInputs({ ...inputs, [ticker]: "" });
      await loadData();
    } catch (e) {
      alert("Trade failed: " + e.message);
    } finally {
       setActionLoading(false);
    }
  };

  if (loading && !data) return (
     <div className="h-full flex flex-col items-center justify-center gap-4 bg-[var(--app-bg)] w-full">
        <Loader2 size={24} className="text-[var(--accent)] animate-spin" />
        <span className="text-[12px] font-medium text-[var(--text-muted)]">Booting Virtual Engine...</span>
     </div>
  );

  if (!data?.initialized) return (
     <div className="h-full flex flex-col items-center justify-center p-6 bg-[var(--app-bg)] w-full">
        <div className="surface-card max-w-md w-full p-8 text-center flex flex-col items-center border border-[var(--border-color)]">
           <div className="flex h-16 w-16 items-center justify-center rounded-full bg-[#1e232b] border border-[var(--border-color)] mb-6">
              <Coins size={32} className="text-[var(--accent)]" />
           </div>
           <h2 className="heading-2">Paper Trading Engine</h2>
           <p className="mt-3 text-[13px] text-[var(--text-muted)] leading-relaxed mb-8">
              Initialize the virtual environment with $100,000 to test models and monitor multi-agent execution risk-free.
           </p>
           <button onClick={handleInit} disabled={actionLoading} className="btn-primary w-full py-3 text-[13px]">
              {actionLoading ? "Initializing..." : "Initialize $100K Account"}
           </button>
        </div>
     </div>
  );

  const bal = data.balance || 0;
  const eq = data.total_equity || 0;
  const ret = ((eq - 100000) / 100000) * 100;
  const positions = data.positions || {};
  const isUp = ret >= 0;

  return (
    <div className="flex-1 overflow-y-auto w-full p-4 md:p-6 lg:p-8 max-w-[1440px] mx-auto animate-fade-in flex flex-col gap-6 lg:gap-8">

      {/* Page Header */}
      <div className="flex flex-col md:flex-row gap-6 justify-between items-start md:items-center">
         <div className="flex flex-col gap-2">
            <div className="flex items-center gap-3">
               <Coins size={20} className="text-[var(--accent)]" />
               <h1 className="heading-1">Paper Trading</h1>
            </div>
            <p className="text-[13px] text-[var(--text-muted)]">Execute trades using live data entirely risk-free.</p>
         </div>
         
         <div className="flex items-center gap-6 p-4 border border-[var(--border-color)] bg-[var(--card-bg)] rounded-[var(--radius-lg)] shadow-sm">
            <div className="flex flex-col text-right">
               <span className="text-small-caps mb-1">Cash Balance</span>
               <span className="text-lg font-mono text-white">${bal.toLocaleString(undefined, {minimumFractionDigits: 2})}</span>
            </div>
            <div className="h-10 w-px bg-[var(--border-color)] hidden sm:block" />
            <div className="flex flex-col text-right">
               <span className="text-small-caps mb-1">Total Equity</span>
               <div className="flex items-center gap-2">
                  <span className="text-xl font-mono font-bold text-white">${eq.toLocaleString(undefined, {minimumFractionDigits: 2})}</span>
                  <span className="font-mono text-[11px] font-bold" style={{ color: isUp ? "var(--positive)" : "var(--negative)" }}>
                     {isUp ? "+" : ""}{ret.toFixed(2)}%
                  </span>
               </div>
            </div>
         </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_360px] gap-6 lg:gap-8">
         
         {/* Left: Positions Area */}
         <div className="flex flex-col gap-6">
            
            {/* Order Entry */}
            <section className="bg-[var(--card-bg)] border border-[var(--border-color)] rounded-[var(--radius-lg)] shadow-sm p-5 md:p-6">
               <div className="flex items-center gap-2 mb-5 border-b border-[var(--border-color)] pb-3">
                  <Zap size={16} className="text-[var(--accent)]" />
                  <h2 className="heading-3">Quick Trade Entry</h2>
               </div>
               <div className="flex flex-col sm:flex-row items-center gap-4">
                  <div className="flex w-full gap-4">
                     <div className="relative flex-1">
                        <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-muted)]" />
                        <input 
                           placeholder="TICKER" 
                           value={inputs["_NEW"]?.ticker || ""}
                           onChange={(e) => setInputs(prev => ({...prev, _NEW: {...prev._NEW, ticker: e.target.value.toUpperCase()}}))}
                           className="input-standard pl-9 font-mono"
                        />
                     </div>
                     <input 
                        type="number" 
                        placeholder="SHARES" 
                        value={inputs["_NEW"]?.shares || ""}
                        onChange={(e) => setInputs(prev => ({...prev, _NEW: {...prev._NEW, shares: e.target.value}}))}
                        className="input-standard flex-1 font-mono"
                     />
                  </div>
                  <div className="flex w-full sm:w-auto gap-3">
                     <button onClick={() => {
                        if (inputs["_NEW"]?.ticker && inputs["_NEW"]?.shares) {
                           handleTrade("buy", inputs["_NEW"].ticker);
                           setInputs(prev => ({...prev, _NEW: {ticker: "", shares: ""}}));
                        }
                     }} disabled={actionLoading} className="btn-standard border-[var(--positive)] text-[var(--positive)] hover:bg-[#10b98115]">
                        <Plus size={14}/> BUY
                     </button>
                     <button onClick={() => {
                        if (inputs["_NEW"]?.ticker && inputs["_NEW"]?.shares) {
                           handleTrade("sell", inputs["_NEW"].ticker);
                           setInputs(prev => ({...prev, _NEW: {ticker: "", shares: ""}}));
                        }
                     }} disabled={actionLoading} className="btn-standard border-[var(--negative)] text-[var(--negative)] hover:bg-[#ef444415]">
                        <Minus size={14}/> SELL
                     </button>
                  </div>
               </div>
            </section>

            {/* Positions */}
            <section className="bg-[var(--card-bg)] border border-[var(--border-color)] rounded-[var(--radius-lg)] shadow-sm overflow-hidden">
               <div className="p-5 border-b border-[var(--border-color)] flex items-center justify-between bg-[#1b1f27]">
                  <h2 className="heading-3">Active Holdings</h2>
                  <span className="surface-badge">{Object.keys(positions).length} Trades</span>
               </div>
               
               {Object.keys(positions).length > 0 ? (
                  <div className="overflow-x-auto">
                     <table className="table-standard min-w-[700px]">
                        <thead>
                           <tr>
                              <th className="w-[20%]">Symbol</th>
                              <th className="w-[15%] text-right">Shares</th>
                              <th className="w-[20%] text-right hidden sm:table-cell">Avg Price</th>
                              <th className="w-[20%] text-right">Return</th>
                              <th className="w-[25%] text-center">Manage</th>
                           </tr>
                        </thead>
                        <tbody>
                           {Object.entries(positions).map(([ticker, p]) => {
                              const ret = ((p.current_price - p.avg_price) / p.avg_price) * 100;
                              const isPos = ret >= 0;
                              return (
                              <tr key={ticker}>
                                 <td className="font-semibold text-white">{ticker}</td>
                                 <td className="text-right font-mono text-[var(--text-muted)]">{p.shares}</td>
                                 <td className="text-right font-mono text-[var(--text-muted)] hidden sm:table-cell">${p.avg_price?.toFixed(2)}</td>
                                 <td className="text-right font-mono font-bold" style={{ color: isPos ? "var(--positive)" : "var(--negative)" }}>
                                    {isPos ? "+" : ""}{ret.toFixed(2)}%
                                 </td>
                                 <td className="px-4 py-2">
                                    <div className="flex items-center justify-center gap-2">
                                       <input 
                                          type="number" min="1" max={p.shares} placeholder="Qty"
                                          value={inputs[ticker] || ""}
                                          onChange={(e) => setInputs({...inputs, [ticker]: e.target.value})}
                                          className="input-standard !w-16 !p-1.5 text-center"
                                       />
                                       <button onClick={() => handleTrade("sell", ticker)} disabled={actionLoading}
                                          className="btn-standard !px-2.5 !py-1.5 border-[var(--negative)] text-[var(--negative)] hover:bg-[#ef444415]">
                                          SELL
                                       </button>
                                    </div>
                                 </td>
                              </tr>
                           )})}
                        </tbody>
                     </table>
                  </div>
               ) : (
                  <div className="p-12 text-center text-[13px] text-[var(--text-muted)]">
                     No active positions. Submit an order above to execute.
                  </div>
               )}
            </section>
         </div>

         {/* Right: Intel Guidance */}
         <div className="flex flex-col gap-6">
            <section className="surface-card flex flex-col">
               <div className="p-5 border-b border-[var(--border-color)] flex items-center gap-2 bg-[#1b1f27]">
                  <Target size={16} className="text-[var(--accent)]" />
                  <h2 className="heading-3">Mythic Advice</h2>
               </div>
               
               <div className="p-5 flex flex-col gap-5">
                  {intel?.summary ? (
                     <div className="p-4 bg-[#1e232b] border border-[var(--border-color)] rounded-[var(--radius-md)]">
                        <p className="text-[13px] leading-relaxed text-[var(--text-main)]">{intel.summary}</p>
                     </div>
                  ) : (
                     <p className="text-[12px] text-[var(--text-muted)] italic">Awaiting macro analysis from Mythic network...</p>
                  )}

                  {intel?.top_picks?.length > 0 && (
                     <div>
                        <p className="text-small-caps mb-3">High Conviction Ideas</p>
                        <div className="flex flex-wrap gap-2">
                           {intel.top_picks.map(p => (
                              <button key={p} onClick={() => setInputs(prev => ({...prev, _NEW: {ticker: p, shares: ""}}))}
                                 className="btn-standard !px-3 !py-1.5">
                                 {p} <ArrowUpRight size={12} className="ml-1 text-[var(--text-muted)]"/>
                              </button>
                           ))}
                        </div>
                     </div>
                  )}
               </div>
            </section>
         </div>

      </div>
    </div>
  );
}
