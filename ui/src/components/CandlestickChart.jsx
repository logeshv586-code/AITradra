import React, { useState, useRef } from "react";
import { T } from "../theme";
import { computeMA } from "../data";

export default function AdvancedCandlestickChart({ data }) {
  const [hover, setHover] = useState(null);
  const ref = useRef(null);
  const D = data.slice(-60);
  const ma20 = computeMA(D, 20);
  const ma50 = computeMA(D, 50);

  const priceMin = Math.min(...D.map(d => d.l)) * 0.998;
  const priceMax = Math.max(...D.map(d => d.h)) * 1.002;
  const volMax = Math.max(...D.map(d => d.v));
  const pRange = priceMax - priceMin;
  const W = 720, PH = 160, VH = 35, GAP = 8, TH = PH + GAP + VH;
  const py = v => PH - ((v - priceMin) / pRange) * PH;

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

  const candleW = Math.max(1, (W / D.length) * 0.65);

  return (
    <div className="relative select-none rounded-2xl overflow-hidden"
      style={{ 
        background: 'rgba(8, 12, 24, 0.50)',
        border: '1px solid rgba(255,255,255,0.04)',
        boxShadow: 'inset 4px 4px 10px rgba(0,0,0,0.40), inset -2px -2px 8px rgba(255,255,255,0.02), 0 4px 12px rgba(0,0,0,0.20)'
      }}>
      {hover !== null && (
        <div className="absolute top-3 left-3 z-20 clay-badge px-3 py-2 text-[10px] font-mono flex gap-3"
          style={{ borderRadius: '12px' }}>
          <span style={{ color: T.muted }}>D{D[hover].t}</span>
          <span><span style={{ color: T.muted }}>O:</span>{D[hover].o.toFixed(2)}</span>
          <span><span style={{ color: T.muted }}>H:</span>{D[hover].h.toFixed(2)}</span>
          <span><span style={{ color: T.muted }}>L:</span>{D[hover].l.toFixed(2)}</span>
          <span style={{ color: D[hover].c >= D[hover].o ? T.buy : T.sell, textShadow:`0 0 6px ${D[hover].c >= D[hover].o ? T.buy : T.sell}50` }}>C:{D[hover].c.toFixed(2)}</span>
          <span style={{ color: T.muted }}>V:{(D[hover].v/1e6).toFixed(1)}M</span>
        </div>
      )}
      <div className="absolute top-3 right-3 flex gap-3 text-[10px] font-mono z-10">
        <span className="flex items-center gap-1.5"><span className="w-3 h-0.5" style={{ background: T.warn, boxShadow:`0 0 4px ${T.warn}60` }}></span><span style={{ color: T.muted }}>MA20</span></span>
        <span className="flex items-center gap-1.5"><span className="w-3 h-0.5" style={{ background: T.ai, boxShadow:`0 0 4px ${T.ai}60` }}></span><span style={{ color: T.muted }}>MA50</span></span>
      </div>
      <svg viewBox={`0 0 ${W} ${TH + 4}`} className="w-full" style={{ height: 240 }}
        ref={ref} onMouseMove={handleMove} onMouseLeave={() => setHover(null)}>
        <defs>
          <linearGradient id="volGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={T.ai} stopOpacity={0.3} />
            <stop offset="100%" stopColor={T.ai} stopOpacity={0.05} />
          </linearGradient>
        </defs>
        {[0.25,0.5,0.75,1].map(f => (
          <line key={f} x1={0} y1={PH * f} x2={W} y2={PH * f} stroke={T.border} strokeWidth={1} strokeDasharray="2,4" opacity={0.5} />
        ))}
        <path d={pathMA(ma20, 19)} stroke={T.warn} strokeWidth={1.5} fill="none" style={{ filter: `drop-shadow(0 0 3px ${T.warn}60)` }} />
        <path d={pathMA(ma50, 49)} stroke={T.ai} strokeWidth={1.5} fill="none" style={{ filter: `drop-shadow(0 0 3px ${T.ai}60)` }} />
        {D.map((d, i) => {
          const isUp = d.c >= d.o;
          const col = isUp ? T.buy : T.sell;
          const cx = (i + 0.5) * (W / D.length);
          const bodyTop = py(Math.max(d.o, d.c));
          const bodyH = Math.max(1, Math.abs(py(d.o) - py(d.c)));
          const vH = Math.max(1, (d.v / volMax) * VH);
          const isHov = hover === i;
          return (
            <g key={i} opacity={hover === null || isHov ? 1 : 0.4} className="transition-opacity">
              {isHov && (
                <>
                  <line x1={cx} y1={0} x2={cx} y2={TH} stroke={T.borderHl} strokeWidth={1} strokeDasharray="4,4" />
                  <line x1={0} y1={py(d.c)} x2={W} y2={py(d.c)} stroke={T.borderHl} strokeWidth={1} strokeDasharray="4,4" />
                </>
              )}
              <line x1={cx} y1={py(d.h)} x2={cx} y2={py(d.l)} stroke={col} strokeWidth={1.2} style={{ filter: isHov ? `drop-shadow(0 0 3px ${col}60)` : 'none' }} />
              <rect x={cx - candleW/2} y={bodyTop} width={candleW} height={bodyH} fill={isUp ? col : 'transparent'} stroke={col} strokeWidth={1.2} style={{ filter: isHov ? `drop-shadow(0 0 4px ${col}60)` : 'none' }} />
              <rect x={cx - candleW/2} y={PH + GAP + (VH - vH)} width={candleW} height={vH} fill="url(#volGrad)" />
            </g>
          );
        })}
        <line x1={0} y1={py(D[D.length-1].c)} x2={W} y2={py(D[D.length-1].c)} stroke={T.buy} strokeWidth={1} strokeDasharray="4,4" opacity={0.8} style={{ filter: `drop-shadow(0 0 3px ${T.buy})` }} />
      </svg>
    </div>
  );
}
