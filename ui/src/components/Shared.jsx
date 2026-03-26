import React from "react";
import { T } from "../theme";

export function GlassCard({ children, className = '', glowCol = 'transparent', interactive = false, style = {}, ...props }) {
  return (
    <div className={`relative overflow-hidden rounded-xl backdrop-blur-md transition-all duration-300 ${interactive ? 'hover:-translate-y-1 hover:shadow-2xl' : ''} ${className}`}
         style={{ background: T.glass, border: `1px solid ${T.border}`, boxShadow: `0 8px 32px rgba(0,0,0,0.3), inset 0 1px 0 ${T.borderHl}`, ...style }}
         {...props}>
      {interactive && <div className="absolute inset-0 opacity-0 hover:opacity-10 transition-opacity duration-300 pointer-events-none" style={{ background: `radial-gradient(circle at center, ${glowCol}, transparent 70%)` }} />}
      {children}
    </div>
  );
}

export function Sparkline({ data, color, h = 32, w = 90 }) {
  const pts = data.slice(-20);
  const mn = Math.min(...pts.map(d => d.c));
  const mx = Math.max(...pts.map(d => d.c));
  const r = mx - mn || 1;
  const path = pts.map((d, i) => {
    const x = (i / (pts.length - 1)) * w;
    const y = h - ((d.c - mn) / r) * h;
    return `${i === 0 ? 'M' : 'L'}${x},${y}`;
  }).join(' ');
  const area = path + ` L${w},${h} L0,${h} Z`;
  const gradId = `sg-${color.replace('#','')}`;
  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} className="overflow-visible">
      <defs>
        <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity={0.4} />
          <stop offset="100%" stopColor={color} stopOpacity={0} />
        </linearGradient>
      </defs>
      <path d={area} fill={`url(#${gradId})`} />
      <path d={path} stroke={color} strokeWidth={1.5} fill="none" style={{ filter: `drop-shadow(0 2px 4px ${color}60)` }} />
    </svg>
  );
}
