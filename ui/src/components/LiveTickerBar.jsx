import React, { useState, useEffect } from "react";
import { Clock, ShieldCheck, Zap } from "lucide-react";
import MarketStatusBadges from "./MarketStatusBadges";

export default function LiveTickerBar({ stocks = [] }) {
  const [offset, setOffset] = useState(0);
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    const id = setInterval(() => setOffset(o => (o + 0.04) % 100), 50);
    const clockId = setInterval(() => setTime(new Date()), 1000);
    return () => { clearInterval(id); clearInterval(clockId); };
  }, []);

  const items = stocks.length > 0 ? [...stocks, ...stocks, ...stocks] : [];

  return (
    <div className="h-9 flex items-center z-40 border-y border-white/[0.08] bg-black/40 backdrop-blur-md overflow-hidden">
      {/* Market Status */}
      <div className="flex-shrink-0 px-6 flex items-center gap-3 border-r border-white/[0.08] h-full bg-white/[0.02]">
        <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)] animate-pulse" />
        <span className="text-[10px] font-bold tracking-[0.2em] uppercase text-white">
          {stocks.length > 0 ? `LIVE_AXIOM` : 'L-DRIVE_UP'}
        </span>
      </div>

      <MarketStatusBadges />

      <div className="flex-1 overflow-hidden relative h-full flex items-center bg-black/20">
        {items.length > 0 ? (
          <div className="flex gap-12 whitespace-nowrap absolute transition-transform ease-linear"
            style={{ transform: `translateX(-${offset}%)` }}>
            {items.map((s, i) => {
              const isUp = (s.chg || 0) >= 0;
              const col = isUp ? 'var(--accent-positive)' : 'var(--accent-negative)';
              return (
                <span key={`${s.id}-${i}`} className="flex items-center gap-4 group cursor-pointer px-2 transition-all duration-120">
                  <span className="text-[11px] font-bold text-white tracking-widest uppercase">{s.id}</span>
                  <span className="text-[11px] font-mono text-slate-500 font-bold tabular-nums">
                    {s.id.includes('-USD') ? '' : '$'}{(s.px || 0).toLocaleString(undefined, {minimumFractionDigits: 2})}
                  </span>
                  <span className="text-[11px] font-mono font-bold flex items-center tabular-nums" style={{ color: col }}>
                    {isUp ? '+' : ''}{s.chg || 0}%
                  </span>
                  <div className="w-[1px] h-3 bg-white/[0.05]" />
                </span>
              );
            })}
          </div>
        ) : (
          <div className="flex items-center gap-3 px-6 text-slate-700 font-mono text-[9px] tracking-widest uppercase animate-pulse">
            <Zap size={10} className="text-indigo-500/40" />
            Synchronizing global liquidity pools...
          </div>
        )}
      </div>

      <div className="flex-shrink-0 px-6 flex items-center gap-6 border-l border-white/[0.08] h-full bg-white/[0.02]">
        <div className="flex items-center gap-2 text-slate-500 font-bold">
          <ShieldCheck size={12} className="text-indigo-400/60" />
          <span className="text-[9px] tracking-widest uppercase">SYNERGY_LINK_STABLE</span>
        </div>
        <div className="h-4 w-[1px] bg-white/10" />
        <div className="flex items-center gap-2.5 font-mono font-bold text-white tabular-nums">
          <Clock size={12} className="text-slate-600" />
          <span className="text-[10px] tracking-tighter leading-none">{time.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })}</span>
          <span className="text-[8px] text-slate-600 tracking-widest uppercase mb-0.5">LOCAL</span>
        </div>
      </div>
    </div>
  );
}
