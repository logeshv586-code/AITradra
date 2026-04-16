import React, { useState, useEffect } from "react";
import { ArrowUp, ArrowDown, Activity, RefreshCcw, Loader2, BarChart2 } from "lucide-react";
import { API_BASE } from "../api_config";

export default function TrendingStocksView({ stocks: liveStocks }) {
  const [data, setData] = useState(liveStocks || []);
  const [loading, setLoading] = useState(!liveStocks || liveStocks.length === 0);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState("ALL");

  useEffect(() => {
    if (liveStocks && liveStocks.length > 0) {
      setData(liveStocks);
      setLoading(false);
    }
  }, [liveStocks]);

  const fetchTrending = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/market/trending`);
      if (!res.ok) throw new Error("Could not fetch trending stocks");
      setData(await res.json());
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!liveStocks || liveStocks.length === 0) {
       fetchTrending();
    }
  }, [liveStocks]);

  let filtered = [...data];
  if (filter === "GAINERS") filtered = filtered.filter((s) => s.chg >= 0).sort((a, b) => b.chg - a.chg);
  if (filter === "LOSERS") filtered = filtered.filter((s) => s.chg < 0).sort((a, b) => a.chg - b.chg);

  return (
    <div className="flex-1 overflow-y-auto w-full p-4 md:p-6 lg:p-8 max-w-[1440px] mx-auto animate-fade-in">
       {/* Page Header */}
       <div className="flex flex-col gap-2 mb-6">
          <div className="flex items-center gap-3">
             <BarChart2 size={20} className="text-[var(--accent)]" />
             <h1 className="heading-1">Market Pulse</h1>
          </div>
          <p className="text-[13px] text-[var(--text-muted)]">Live monitoring of top market movers and high-volume equities.</p>
       </div>

       {/* Toolbar Area */}
       <div className="flex flex-col sm:flex-row gap-4 mb-6 justify-between items-center bg-[var(--card-bg)] p-4 rounded-[var(--radius-lg)] border border-[var(--border-color)] shadow-sm">
          <div className="toggle-group w-full sm:w-auto overflow-x-auto">
             <button onClick={() => setFilter("ALL")} className={`toggle-item ${filter === "ALL" ? "active" : ""}`}>All Movers</button>
             <button onClick={() => setFilter("GAINERS")} className={`toggle-item ${filter === "GAINERS" ? "active" : ""}`}>Top Gainers</button>
             <button onClick={() => setFilter("LOSERS")} className={`toggle-item ${filter === "LOSERS" ? "active" : ""}`}>Top Losers</button>
          </div>

          <button onClick={fetchTrending} disabled={loading} className="btn-standard w-full sm:w-auto">
             <RefreshCcw size={12} className={loading ? "animate-spin" : ""} />
             Refresh
          </button>
       </div>

       {/* Content Area */}
       {loading && data.length === 0 ? (
         <div className="h-64 flex flex-col items-center justify-center gap-4 bg-[var(--card-bg)] border border-[var(--border-color)] rounded-[var(--radius-lg)]">
           <Loader2 size={24} className="text-[var(--accent)] animate-spin" />
           <span className="text-[12px] font-medium text-[var(--text-muted)]">Gathering pulse data...</span>
         </div>
       ) : error ? (
         <div className="h-64 flex flex-col items-center justify-center gap-2 bg-[var(--card-bg)] border border-[var(--border-color)] rounded-[var(--radius-lg)] text-[var(--negative)]">
            <Activity size={24} className="mb-2" />
            <p className="font-semibold text-[13px]">Data Feed Offline</p>
            <p className="text-[11px] font-mono opacity-80">{error}</p>
         </div>
       ) : (
         <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
           {filtered.map((stock) => {
             const isUp = stock.chg >= 0;
             const color = isUp ? "var(--positive)" : "var(--negative)";
             return (
               <article key={stock.ticker || stock.id} className="surface-card p-5 group flex flex-col gap-4 hover:border-slate-500 transition-colors">
                 
                 <div className="flex justify-between items-start">
                   <div>
                     <h3 className="heading-2">{stock.ticker || stock.id}</h3>
                     <p className="text-[11px] text-[var(--text-muted)] truncate max-w-[120px]">{stock.name}</p>
                   </div>
                   <div 
                     className="flex items-center gap-1 rounded bg-[#1e232b] px-2 py-1 text-[11px] font-mono font-bold"
                     style={{ color }}
                   >
                     {isUp ? <ArrowUp size={12}/> : <ArrowDown size={12}/>}
                     {stock.chg?.toFixed(2)}%
                   </div>
                 </div>

                 <div className="flex items-end justify-between border-t border-[var(--border-color)] pt-4 mt-auto">
                   <div>
                     <p className="text-[10px] uppercase text-[var(--text-muted)] mb-1">Last Price</p>
                     <p className="font-mono text-xl font-semibold text-white">
                       ${stock.current_price?.toFixed(2) || stock.px?.toFixed(2)}
                     </p>
                   </div>
                   <div className="text-right">
                     <p className="text-[10px] uppercase text-[var(--text-muted)] mb-1">Volume</p>
                     <p className="font-mono text-[13px] text-white">
                       {(stock.volume / 1e6).toFixed(1)}M
                     </p>
                   </div>
                 </div>

               </article>
             );
           })}
           {filtered.length === 0 && (
             <div className="col-span-1 border border-dashed border-[var(--border-color)] sm:col-span-2 lg:col-span-3 xl:col-span-4 h-48 flex items-center justify-center rounded-[var(--radius-lg)]">
               <span className="text-[12px] text-[var(--text-muted)]">No stocks match current filter.</span>
             </div>
           )}
         </div>
       )}
    </div>
  );
}
