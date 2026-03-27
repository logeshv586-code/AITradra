import React, { useState, useEffect } from "react";
import { Clock, ShieldCheck } from "lucide-react";
import { T } from "../theme";

export default function LiveTickerBar({ stocks = [] }) {
  const [offset, setOffset] = useState(0);
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    const id = setInterval(() => setOffset(o => (o + 0.05) % 100), 50);
    const clockId = setInterval(() => setTime(new Date()), 1000);
    return () => { clearInterval(id); clearInterval(clockId); };
  }, []);

  // Triple the items for seamless scrolling
  const items = stocks.length > 0 ? [...stocks, ...stocks, ...stocks] : [];

  return (
    <div className="clay-ticker h-9 flex items-center z-40 border-y border-white/5" style={{ fontSize: 10 }}>
      {/* Market Status */}
      <div className="flex-shrink-0 px-5 font-black flex items-center gap-2.5 border-r border-white/10 h-full bg-black/20"
        style={{ color: T.buy, textShadow: `0 0 10px ${T.buy}40` }}>
        <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse shadow-[0_0_8px_rgba(34,197,94,0.6)]" />
        <span className="tracking-[0.2em] uppercase">
          {stocks.length > 0 ? `LIVE_DATA // ${stocks.length} ASSETS` : 'LOADING...'}
        </span>
      </div>

      <div className="flex-1 overflow-hidden relative h-full flex items-center">
        {items.length > 0 ? (
          <div className="flex gap-12 whitespace-nowrap absolute transition-transform ease-linear"
            style={{ transform: `translateX(-${offset}%)` }}>
            {items.map((s, i) => {
              const isUp = (s.chg || 0) >= 0;
              const col = isUp ? T.buy : T.sell;
              return (
                <span key={`${s.id}-${i}`} className="flex items-center gap-3 group cursor-pointer hover:bg-white/5 px-2 py-1 rounded-md transition-colors">
                  <span className="font-black text-white tracking-widest">{s.id}</span>
                  <span className="font-mono text-slate-400 font-bold">
                    {s.id.includes('-USD') ? '' : '$'}{(s.px || 0).toLocaleString(undefined, {minimumFractionDigits: 2})}
                  </span>
                  <span className="font-mono font-black flex items-center" style={{ color: col, textShadow: `0 0 8px ${col}30` }}>
                    {isUp ? '▲' : '▼'}{Math.abs(s.chg || 0).toFixed(2)}%
                  </span>
                  <div className="w-px h-3 bg-white/10 mx-1" />
                </span>
              );
            })}
          </div>
        ) : (
          <div className="flex items-center gap-2 px-4 text-slate-600 font-mono animate-pulse">
            <div className="w-1.5 h-1.5 rounded-full bg-indigo-500 animate-ping" />
            Fetching live market data...
          </div>
        )}
      </div>

      <div className="flex-shrink-0 px-6 flex items-center gap-6 border-l border-white/10 h-full bg-black/20">
        <div className="flex items-center gap-2 text-slate-400 font-bold">
          <ShieldCheck size={12} className="text-indigo-400" />
          <span className="tracking-widest">YFINANCE_LIVE</span>
        </div>
        <div className="h-4 w-px bg-white/10" />
        <div className="flex items-center gap-2.5 font-mono font-black text-white">
          <Clock size={12} className="text-slate-500" />
          <span className="tracking-tighter">{time.toLocaleTimeString('en-US', { hour12: false })}</span>
          <span className="text-[9px] text-slate-500 tracking-widest ml-1">LOCAL</span>
        </div>
      </div>
    </div>
  );
}
