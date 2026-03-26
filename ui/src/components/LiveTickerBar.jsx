import React, { useState, useEffect } from "react";
import { Activity, Clock } from "lucide-react";
import { T } from "../theme";
import { STOCKS } from "../data";

export default function LiveTickerBar() {
  const [offset, setOffset] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setOffset(o => (o + 0.3) % 100), 30);
    return () => clearInterval(id);
  }, []);
  const items = [...STOCKS, ...STOCKS];

  return (
    <div className="h-8 border-b flex items-center shadow-md z-40 backdrop-blur-sm"
      style={{ background: 'rgba(2, 4, 10, 0.7)', borderColor: T.border, fontSize: 11 }}>
      <div className="flex-shrink-0 px-4 font-bold text-xs border-r flex items-center gap-2"
        style={{ borderColor: T.border, color: T.buy, textShadow: `0 0 10px ${T.buy}80` }}>
        <Activity size={12} className="animate-pulse" /> LIVE STREAM
      </div>
      <div className="flex-1 overflow-hidden relative h-full flex items-center">
        <div className="flex gap-10 whitespace-nowrap absolute transition-transform"
          style={{ transform: `translateX(-${offset}%)` }}>
          {items.map((s, i) => {
            const isUp = s.chg >= 0;
            const col = isUp ? T.buy : T.sell;
            return (
              <span key={i} className="flex items-center gap-2">
                <span className="font-bold" style={{ color: T.text, fontFamily: 'monospace' }}>{s.id}</span>
                <span style={{ fontFamily: 'monospace', color: T.muted }}>${s.px.toFixed(2)}</span>
                <span style={{ color: col, fontFamily: 'monospace', textShadow: `0 0 8px ${col}60` }}>
                  {isUp ? '▲' : '▼'}{Math.abs(s.chg)}%
                </span>
              </span>
            );
          })}
        </div>
      </div>
      <div className="flex-shrink-0 px-4 text-xs flex items-center gap-1.5" style={{ color: T.muted }}>
        <Clock size={11} /> {new Date().toLocaleTimeString()}
      </div>
    </div>
  );
}
