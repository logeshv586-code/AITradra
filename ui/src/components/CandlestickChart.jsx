import React, { useState, useRef } from "react";
import { Loader2 } from "lucide-react";
import { computeMA } from "../data";

export default function AdvancedCandlestickChart({ data }) {
  const [hover, setHover] = useState(null);
  const ref = useRef(null);

  if (!data || data.length === 0) return (
    <div className="h-60 flex flex-col items-center justify-center gap-4 bg-black/20 rounded-xl border border-white/[0.05]">
      <div className="flex items-center gap-3">
        <Loader2 size={16} className="text-[var(--accent)] animate-spin" />
        <span className="text-[10px] font-bold font-mono text-slate-400 uppercase tracking-[0.3em]">
          Synchronizing Price Stream...
        </span>
      </div>
      <p className="text-[9px] text-slate-600 font-mono text-center max-w-[200px]">
        Waiting for high-fidelity market data from the knowledge store.
      </p>
    </div>
  );

  const D = data.slice(-Math.min(60, data.length));
  const ma20 = computeMA(D, 20);
  const ma50 = computeMA(D, 50);

  const priceMin = Math.min(...D.map(d => d.l)) * 0.998;
  const priceMax = Math.max(...D.map(d => d.h)) * 1.002;
  const volMax = Math.max(...D.map(d => d.v)) || 1;
  const pRange = (priceMax - priceMin) || 1;
  const W = 720, PH = 160, VH = 35, GAP = 8, TH = PH + GAP + VH;
  
  const py = v => {
    const val = PH - ((v - priceMin) / pRange) * PH;
    return isNaN(val) ? 0 : val;
  };

  const handleMove = (e) => {
    if (!ref.current) return;
    const r = ref.current.getBoundingClientRect();
    const pct = (e.clientX - r.left) / r.width;
    const i = Math.max(0, Math.min(D.length - 1, Math.floor(pct * D.length)));
    setHover(i);
  };

  const pathMA = (maArr, startI) => {
    const pts = maArr.map((v, i) => {
      if (v === null) return null;
      const x = (i + 0.5) * (W / D.length);
      return `${i === startI ? 'M' : 'L'}${x},${py(v)}`;
    }).filter(Boolean);
    return pts.join(' ');
  };

  const candleW = Math.max(1, (W / D.length) * 0.7);

  // Institutional Palette Variables (mapped to index.css)
  const COL_UP = "var(--accent-positive)";
  const COL_DOWN = "var(--accent-negative)";
  const COL_MA20 = "#fbbf24";
  const COL_MA50 = "var(--accent-indigo)";
  const COL_MUTED = "#475569";
  const COL_TEXT = "#94a3b8";

  return (
    <div className="relative select-none rounded-xl overflow-hidden glass-card border-white/[0.06] bg-black/20">
      {/* Precision Legend / Hover Data */}
      {hover !== null && (
        <div className="absolute top-4 left-4 z-20 flex items-center gap-4 px-4 py-2 rounded-lg bg-[#0B0F14]/80 backdrop-blur-md border border-white/[0.1] shadow-2xl">
          <div className="flex flex-col">
            <span className="text-[8px] font-bold text-slate-600 uppercase tracking-widest">Snapshot</span>
            <span className="text-[10px] font-mono font-bold text-white uppercase">T{D[hover].t}</span>
          </div>
          <div className="w-[1px] h-6 bg-white/[0.08]" />
          <div className="grid grid-cols-2 gap-x-4 gap-y-0.5">
            <div className="flex items-center gap-2">
              <span className="text-[8px] font-bold text-slate-600 uppercase">O</span>
              <span className="text-[10px] font-mono font-bold text-slate-300">{D[hover].o.toFixed(2)}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[8px] font-bold text-slate-600 uppercase">H</span>
              <span className="text-[10px] font-mono font-bold text-slate-300">{D[hover].h.toFixed(2)}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[8px] font-bold text-slate-600 uppercase">L</span>
              <span className="text-[10px] font-mono font-bold text-slate-300">{D[hover].l.toFixed(2)}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[8px] font-bold text-slate-600 uppercase">C</span>
              <span className="text-[10px] font-mono font-bold" style={{ color: D[hover].c >= D[hover].o ? COL_UP : COL_DOWN }}>{D[hover].c.toFixed(2)}</span>
            </div>
          </div>
          <div className="w-[1px] h-6 bg-white/[0.08]" />
          <div className="flex flex-col">
            <span className="text-[8px] font-bold text-slate-600 uppercase tracking-widest">Volume (M)</span>
            <span className="text-[10px] font-mono font-bold text-slate-400">{(D[hover].v/1e6).toFixed(1)}M</span>
          </div>
        </div>
      )}

      {/* MA Legend */}
      <div className="absolute top-4 right-4 flex gap-4 text-[9px] font-bold tracking-widest uppercase z-10 transition-opacity" style={{ opacity: hover !== null ? 0.4 : 1 }}>
        <div className="flex items-center gap-2">
          <div className="w-2.5 h-0.5 rounded-full" style={{ background: COL_MA20, boxShadow: `0 0 4px ${COL_MA20}40` }} />
          <span className="text-slate-500">MA20</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-2.5 h-0.5 rounded-full" style={{ background: COL_MA50, boxShadow: `0 0 4px ${COL_MA50}40` }} />
          <span className="text-slate-500">MA50</span>
        </div>
      </div>

      <svg viewBox={`0 0 ${W} ${TH + 4}`} className="w-full" style={{ height: 260 }}
        ref={ref} onMouseMove={handleMove} onMouseLeave={() => setHover(null)}>
        <defs>
          <linearGradient id="volGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--accent-indigo)" stopOpacity={0.25} />
            <stop offset="100%" stopColor="var(--accent-indigo)" stopOpacity={0.02} />
          </linearGradient>
        </defs>

        {/* Horizontal Grid Lines */}
        {[0.25, 0.5, 0.75, 1].map(f => (
          <line key={f} x1={0} y1={PH * f} x2={W} y2={PH * f} stroke="rgba(255,255,255,0.03)" strokeWidth={1} strokeDasharray="4,6" />
        ))}

        {/* MA Plots */}
        <path d={pathMA(ma20, 19)} stroke={COL_MA20} strokeWidth={1.2} fill="none" opacity={0.6} style={{ filter: `drop-shadow(0 0 2px ${COL_MA20}20)` }} />
        <path d={pathMA(ma50, 49)} stroke={COL_MA50} strokeWidth={1.2} fill="none" opacity={0.6} style={{ filter: `drop-shadow(0 0 2px ${COL_MA50}20)` }} />

        {/* Candles */}
        {D.map((d, i) => {
          const isUp = d.c >= d.o;
          const col = isUp ? COL_UP : COL_DOWN;
          const cx = (i + 0.5) * (W / D.length);
          const bodyTop = py(Math.max(d.o, d.c));
          const bodyH = Math.max(1, Math.abs(py(d.o) - py(d.c)));
          const vH = Math.max(1, (d.v / volMax) * VH);
          const isHov = hover === i;
          
          return (
            <g key={i} opacity={hover === null || isHov ? 1 : 0.3} className="transition-opacity duration-120">
              {isHov && (
                <>
                  <line x1={cx} y1={0} x2={cx} y2={TH} stroke="rgba(255,255,255,0.15)" strokeWidth={1} strokeDasharray="4,4" />
                  <line x1={0} y1={py(d.c)} x2={W} y2={py(d.c)} stroke="rgba(255,255,255,0.15)" strokeWidth={1} strokeDasharray="4,4" />
                </>
              )}
              {/* Wick */}
              <line x1={cx} y1={py(d.h)} x2={cx} y2={py(d.l)} stroke={col} strokeWidth={1} opacity={0.8} />
              {/* Body */}
              <rect 
                x={cx - candleW/2} 
                y={bodyTop} 
                width={candleW} 
                height={bodyH} 
                fill={isUp ? col : 'transparent'} 
                fillOpacity={0.6}
                stroke={col} 
                strokeWidth={1} 
                className="transition-all duration-120"
                style={{ filter: isHov ? `drop-shadow(0 0 6px ${col}40)` : 'none' }} 
              />
              {/* Volume Bar */}
              <rect x={cx - candleW/2} y={PH + GAP + (VH - vH)} width={candleW} height={vH} fill="url(#volGrad)" opacity={isHov ? 0.8 : 0.4} />
            </g>
          );
        })}
        
        {/* Last Price Trace */}
        <line x1={0} y1={py(D[D.length-1].c)} x2={W} y2={py(D[D.length-1].c)} stroke={D[D.length-1].c >= D[D.length-1].o ? COL_UP : COL_DOWN} strokeWidth={0.5} strokeDasharray="4,4" opacity={0.6} />
      </svg>
    </div>
  );
}
