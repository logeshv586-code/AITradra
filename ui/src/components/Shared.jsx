import React from "react";
import { T } from "../theme";

export function GlassCard({ children, className = '', glowCol = 'transparent', interactive = false, style = {}, ...props }) {
  return (
    <div className={`clay-card ${interactive ? 'interactive' : ''} ${className}`}
         style={{
           ...style
         }}
         {...props}>
      <div className="scanline" />
      {interactive && (
        <div className="absolute inset-0 opacity-0 hover:opacity-[0.06] transition-opacity duration-500 pointer-events-none rounded-[inherit]"
          style={{ background: `radial-gradient(circle at 30% 30%, ${glowCol}, transparent 70%)` }} />
      )}
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
          <stop offset="0%" stopColor={color} stopOpacity={0.35} />
          <stop offset="100%" stopColor={color} stopOpacity={0} />
        </linearGradient>
      </defs>
      <path d={area} fill={`url(#${gradId})`} />
      <path d={path} stroke={color} strokeWidth={1.5} fill="none" style={{ filter: `drop-shadow(0 2px 6px ${color}50)` }} />
    </svg>
  );
}
