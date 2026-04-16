import React, { useState, useEffect } from "react";
import { Clock, Zap } from "lucide-react";
import MarketStatusBadges from "./MarketStatusBadges";

export default function LiveTickerBar({ stocks = [] }) {
  const [offset, setOffset] = useState(0);
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    const id = setInterval(() => setOffset((o) => (o + 0.04) % 100), 50);
    const clockId = setInterval(() => setTime(new Date()), 1000);
    return () => { clearInterval(id); clearInterval(clockId); };
  }, []);

  const items = stocks.length > 0 ? [...stocks, ...stocks, ...stocks] : [];

  return (
    <div className="ticker-strip">
      {/* Live indicator */}
      <div className="flex-shrink-0 flex items-center gap-2.5 px-5 border-r border-white/[0.06] h-full">
        <div className="h-1.5 w-1.5 rounded-full bg-emerald-500 shadow-[0_0_6px_rgba(16,185,129,0.5)] animate-pulse" />
        <span className="text-[9px] font-bold tracking-[0.18em] uppercase text-white">
          {stocks.length > 0 ? "LIVE" : "SYNC"}
        </span>
      </div>

      <MarketStatusBadges />

      {/* Scrolling Ticker */}
      <div className="flex-1 overflow-hidden relative h-full flex items-center">
        {items.length > 0 ? (
          <div
            className="flex gap-10 whitespace-nowrap absolute"
            style={{ transform: `translateX(-${offset}%)`, transition: "transform 50ms linear" }}
          >
            {items.map((s, i) => {
              const isUp = (s.chg || 0) >= 0;
              const col = isUp ? "var(--positive)" : "var(--negative)";
              return (
                <span
                  key={`${s.id}-${i}`}
                  className="flex items-center gap-3 cursor-pointer px-1"
                >
                  <span className="text-[10px] font-bold text-white tracking-wider uppercase">
                    {s.id}
                  </span>
                  <span className="text-[10px] font-mono text-slate-500 font-semibold tabular-nums">
                    {s.id.includes("-USD") ? "" : "$"}
                    {(s.px || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                  </span>
                  <span
                    className="text-[10px] font-mono font-bold tabular-nums"
                    style={{ color: col }}
                  >
                    {isUp ? "+" : ""}
                    {s.chg || 0}%
                  </span>
                  <div className="w-px h-3 bg-white/[0.05]" />
                </span>
              );
            })}
          </div>
        ) : (
          <div className="flex items-center gap-2 px-5 text-slate-700 font-mono text-[9px] tracking-widest uppercase animate-pulse">
            <Zap size={10} className="text-indigo-500/40" />
            Synchronizing market feeds…
          </div>
        )}
      </div>

      {/* Clock */}
      <div className="flex-shrink-0 flex items-center gap-3 px-5 border-l border-white/[0.06] h-full">
        <div className="flex items-center gap-2 font-mono font-semibold text-white tabular-nums">
          <Clock size={11} className="text-slate-600" />
          <span className="text-[10px] tracking-tight leading-none">
            {time.toLocaleTimeString("en-US", {
              hour12: false,
              hour: "2-digit",
              minute: "2-digit",
              second: "2-digit",
            })}
          </span>
        </div>
      </div>
    </div>
  );
}
