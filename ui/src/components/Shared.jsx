import React from "react";
import { T } from "../theme";

export function GlassCard({ children, className = '', glowCol = 'transparent', interactive = false, style = {}, ...props }) {
  return (
    <div className={`glass-card ${interactive ? 'interactive' : ''} ${className}`}
         style={{
           "--glow-color": glowCol,
           ...style
         }}
         {...props}>

      {children}
    </div>
  );
}

export function Sparkline({ data, color, h = 32, w = 90 }) {
  if (!data || !Array.isArray(data) || data.length < 2) return null;
  const pts = data.slice(-20).map(d => typeof d === 'object' ? d.c : d).filter(v => typeof v === 'number' && !isNaN(v));
  if (pts.length < 2) return null;
  const mn = Math.min(...pts);
  const mx = Math.max(...pts);
  const r = mx - mn || 1;
  const path = pts.map((val, i) => {
    const x = (i / (pts.length - 1)) * w;
    const y = h - ((val - mn) / r) * h;
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
