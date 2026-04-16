import React, { useState, useEffect } from "react";
import { Activity, AlertTriangle, BarChart3, Layout, Loader2, Newspaper, Shield, TrendingDown, TrendingUp, Zap } from "lucide-react";
import { API_BASE } from "../api_config";
import CandlestickChart from "./CandlestickChart";

export default function StockDetailView({ stock }) {
  const [news, setNews] = useState([]);
  const [loading, setLoading] = useState(true);

  const tickerId = stock?.id || "";

  useEffect(() => {
    if (!tickerId) return;
    let cancelled = false;
    const load = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/stock/${tickerId}/news`);
        if (res.ok) {
          const data = await res.json();
          if (!cancelled) setNews(data.news || data.articles || []);
        }
      } catch (err) {
        console.error("News fetch failed:", err);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    load();
    return () => { cancelled = true; };
  }, [tickerId]);

  const px = stock?.px || stock?.price || 0;
  const chg = stock?.chg || 0;
  const isUp = chg >= 0;
  const color = isUp ? "var(--positive)" : "var(--negative)";

  return (
    <div className="flex-1 overflow-y-auto w-full p-4 md:p-6 lg:p-8 max-w-[1440px] mx-auto animate-fade-in flex flex-col gap-6 lg:gap-8">
      
      {/* ── Header Card ── */}
      <header className="surface-card p-6 flex flex-col lg:flex-row lg:items-center justify-between gap-6">
         <div className="flex items-center gap-4">
            <div className="flex h-14 w-14 items-center justify-center rounded-[var(--radius-md)] bg-[#1e232b] border border-[var(--border-color)] text-white font-bold text-lg">
               {tickerId.slice(0, 2)}
            </div>
            <div className="flex flex-col">
               <div className="flex items-center gap-3">
                  <h1 className="heading-1">{tickerId}</h1>
                  <span className="surface-badge">{stock?.name || "Equity"}</span>
               </div>
               <div className="flex items-center gap-4 mt-1">
                  <span className="font-mono text-xl font-semibold text-white">${px.toFixed(2)}</span>
                  <span className="flex items-center gap-1 text-[13px] font-mono font-medium" style={{ color }}>
                     {isUp ? <TrendingUp size={14}/> : <TrendingDown size={14}/>}
                     {isUp ? "+" : ""}{chg.toFixed(2)}%
                  </span>
               </div>
            </div>
         </div>

         {/* Mini Stats Grid */}
         <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {[
               { label: "Volume", value: stock?.volume ? `${(stock.volume / 1e6).toFixed(1)}M` : "n/a" },
               { label: "52W High", value: stock?.week52_high ? `$${stock.week52_high.toFixed(0)}` : "n/a" },
               { label: "52W Low", value: stock?.week52_low ? `$${stock.week52_low.toFixed(0)}` : "n/a" },
               { label: "Market Cap", value: stock?.market_cap ? `$${(stock.market_cap / 1e9).toFixed(1)}B` : "n/a" },
            ].map((s) => (
               <div key={s.label} className="flex flex-col border-l border-[var(--border-color)] pl-4">
                  <span className="text-small-caps">{s.label}</span>
                  <span className="font-mono text-[14px] text-white mt-1">{s.value}</span>
               </div>
            ))}
         </div>
      </header>

      {/* ── Main Layout ── */}
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_360px] gap-6 lg:gap-8">
         
         {/* Left Col: Chart & Setup */}
         <div className="flex flex-col gap-6 lg:gap-8">
            <section className="surface-card flex flex-col">
               <div className="p-5 border-b border-[var(--border-color)] flex items-center gap-2 bg-[#1b1f27]">
                  <BarChart3 size={16} className="text-[var(--accent)]" />
                  <h2 className="heading-3">Price Action</h2>
               </div>
               <div className="p-5 h-[340px] md:h-[400px]">
                  <CandlestickChart ticker={tickerId} />
               </div>
            </section>

            <section className="surface-card flex flex-col">
               <div className="p-5 border-b border-[var(--border-color)] flex items-center gap-2 bg-[#1b1f27]">
                  <Activity size={16} className="text-[var(--accent)]" />
                  <h2 className="heading-3">Key Fundamentals</h2>
               </div>
               <div className="p-6 grid grid-cols-2 md:grid-cols-4 gap-6">
                  {[
                     { l: "P/E R.", v: stock?.pe_ratio?.toFixed(1) || "n/a" },
                     { l: "EPS", v: stock?.eps ? `$${stock.eps.toFixed(2)}` : "n/a" },
                     { l: "Div Y.", v: stock?.dividend_yield ? `${stock.dividend_yield.toFixed(2)}%` : "n/a" },
                     { l: "Beta", v: stock?.beta?.toFixed(2) || "n/a" },
                     { l: "Sec.", v: stock?.sector || "n/a" },
                     { l: "Exch.", v: stock?.exchange || "n/a" },
                     { l: "Vol.", v: stock?.avg_volume ? `${(stock.avg_volume / 1e6).toFixed(1)}M` : "n/a" },
                     { l: "Float", v: stock?.float_shares ? `${(stock.float_shares / 1e6).toFixed(0)}M` : "n/a" }
                  ].map((m) => (
                     <div key={m.l} className="flex flex-col gap-1">
                        <span className="text-small-caps">{m.l}</span>
                        <span className="text-[13px] text-white font-medium">{m.v}</span>
                     </div>
                  ))}
               </div>
            </section>
         </div>

         {/* Right Col: Signal, Risk & News */}
         <div className="flex flex-col gap-6">
            
            <section className="surface-card flex flex-col">
               <div className="p-5 border-b border-[var(--border-color)] flex items-center gap-2 bg-[#1b1f27]">
                  <Zap size={16} className="text-[var(--warning)]" />
                  <h2 className="heading-3">Mythic Signal</h2>
               </div>
               <div className="p-6 flex flex-col items-center justify-center text-center">
                  <p className="text-small-caps mb-3">Consensus Direction</p>
                  <div className={`inline-flex items-center gap-2 px-6 py-2 rounded-[var(--radius-lg)] border ${isUp ? "bg-[#10b98115] border-[#10b98130] text-[var(--positive)]" : "bg-[#ef444415] border-[#ef444430] text-[var(--negative)]"}`}>
                     {isUp ? <TrendingUp size={16}/> : <TrendingDown size={16}/>}
                     <span className="font-bold tracking-wider">{isUp ? "BULLISH" : "BEARISH"}</span>
                  </div>
                  <p className="mt-4 text-[11px] text-[var(--text-muted)] leading-relaxed">
                     Derived from 5 specialized agent outputs within the past hour.
                  </p>
               </div>
            </section>

            <section className="surface-card flex flex-col">
               <div className="p-5 border-b border-[var(--border-color)] flex items-center gap-2 bg-[#1b1f27]">
                  <Shield size={16} className="text-[var(--accent)]" />
                  <h2 className="heading-3">Risk Overview</h2>
               </div>
               <div className="p-6 flex flex-col gap-5">
                  {[
                     { l: "Volatility", v: stock?.volatility || 24, max: 100, c: "var(--warning)" },
                     { l: "Risk Score", v: stock?.risk_score || 4, max: 10, c: "var(--negative)" },
                  ].map((m) => {
                     const pct = Math.min((m.v / m.max) * 100, 100);
                     return (
                        <div key={m.l} className="flex flex-col gap-2">
                           <div className="flex justify-between items-center text-[11px]">
                              <span className="font-medium text-[var(--text-muted)] uppercase tracking-wider">{m.l}</span>
                              <span className="font-mono text-white">{m.v}</span>
                           </div>
                           <div className="h-1.5 w-full bg-[#1e232b] rounded-full overflow-hidden">
                              <div className="h-full rounded-full" style={{ width: `${pct}%`, backgroundColor: m.c }} />
                           </div>
                        </div>
                     );
                  })}
               </div>
            </section>

            <section className="surface-card flex flex-col flex-1">
               <div className="p-5 border-b border-[var(--border-color)] flex items-center justify-between bg-[#1b1f27]">
                  <div className="flex items-center gap-2">
                     <Newspaper size={16} className="text-[var(--accent)]" />
                     <h2 className="heading-3">Latest News</h2>
                  </div>
                  <span className="surface-badge">{news.length}</span>
               </div>
               
               <div className="p-4 flex flex-col gap-3 max-h-[400px] overflow-y-auto no-scrollbar">
                  {loading ? (
                     <div className="py-8 flex justify-center w-full">
                        <Loader2 size={20} className="text-[var(--accent)] animate-spin" />
                     </div>
                  ) : news.length === 0 ? (
                     <p className="py-8 text-center text-[12px] text-[var(--text-muted)]">No recent news available.</p>
                  ) : (
                     news.slice(0, 8).map((item, i) => (
                        <a key={i} href={item.url || "#"} target="_blank" rel="noopener noreferrer"
                           className="group flex flex-col gap-2 p-3 rounded-[var(--radius-md)] border border-transparent hover:border-[var(--border-color)] hover:bg-[#1e232b] transition-colors">
                           <p className="text-[12px] font-medium text-[var(--text-main)] leading-snug line-clamp-2 group-hover:text-[var(--accent)] transition-colors">
                              {item.title || item.headline}
                           </p>
                           <div className="flex items-center justify-between">
                              <span className="text-[10px] text-[var(--text-muted)]">{item.source || "Feed"}</span>
                              {item.sentiment && (
                                 <span className={`text-[9px] font-bold uppercase tracking-wider ${
                                    item.sentiment === "positive" ? "text-[var(--positive)]" : item.sentiment === "negative" ? "text-[var(--negative)]" : "text-[var(--text-muted)]"
                                 }`}>
                                    {item.sentiment}
                                 </span>
                              )}
                           </div>
                        </a>
                     ))
                  )}
               </div>
            </section>
         </div>
      </div>
    </div>
  );
}
