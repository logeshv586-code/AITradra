import React from "react";
import { List, ArrowUpRight } from "lucide-react";
import { T } from "../theme";
import { STOCKS } from "../data";
import { GlassCard, Sparkline } from "./Shared";

export default function WatchlistView({ onSelect }) {
  return (
    <div className="flex-1 p-8 overflow-y-auto">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <h2 className="text-2xl font-bold flex items-center gap-3 text-white text-shadow-glow">
            <List size={24} style={{ color: T.ai }} /> Market Watchlist
          </h2>
          <div className="flex gap-2">
            <button className="btn-primary">All Markets</button>
            <button className="btn-ghost">Tech Focus</button>
          </div>
        </div>

        <GlassCard className="rounded-2xl">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr style={{ background: T.glass2, borderBottom:`1px solid ${T.border}` }}>
                {['Asset','Price','24h Δ','Vol','Trend','AI Signal','Action'].map(h => (
                  <th key={h} className="px-6 py-4 text-[10px] font-bold uppercase tracking-wider text-slate-400">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {STOCKS.map(s => {
                const isUp = s.chg >= 0;
                const col = isUp ? T.buy : T.sell;
                return (
                  <tr key={s.id} className="cursor-pointer group border-b border-white/5 transition-all hover:bg-white/[0.03]" onClick={() => onSelect(s)}>
                    <td className="px-6 py-4">
                      <div className="font-mono font-bold text-sm text-white group-hover:text-shadow-glow">{s.id}</div>
                      <div className="text-xs text-slate-400 mt-0.5">{s.name}</div>
                    </td>
                    <td className="px-6 py-4 font-mono text-sm text-white">${s.px.toFixed(2)}</td>
                    <td className="px-6 py-4 font-mono text-sm font-bold" style={{ color: col, textShadow: `0 0 10px ${col}60` }}>
                      {isUp ? '▲' : '▼'} {Math.abs(s.chg)}%
                    </td>
                    <td className="px-6 py-4 font-mono text-xs text-slate-400">{s.vol}</td>
                    <td className="px-6 py-4">
                      <Sparkline data={s.ohlcv} color={col} w={100} h={36} />
                    </td>
                    <td className="px-6 py-4">
                      <span className="px-2.5 py-1 rounded text-[10px] font-bold" style={{ background: `${col}15`, color: col, border:`1px solid ${col}40`, boxShadow: `0 0 10px ${col}20` }}>
                        {isUp ? 'STRONG BUY' : 'SELL'}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <button className="opacity-0 group-hover:opacity-100 p-2 rounded-lg transition-all" style={{ background: `${T.ai}20`, color: T.text, boxShadow: `0 0 10px ${T.ai}40` }}>
                        <ArrowUpRight size={16} />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </GlassCard>
      </div>
    </div>
  );
}
