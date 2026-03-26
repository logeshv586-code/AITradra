import React, { useState, useRef, useEffect, useCallback } from "react";
import { Activity } from "lucide-react";
import { T } from "../theme";
import { STOCKS, CONTINENTS } from "../data";

export default function GlobeView({ onSelect }) {
  const canvasRef = useRef(null);
  const animRef = useRef(null);
  const stateRef = useRef({
    lon: 0, tilt: 0.28, autoSpin: true, isDragging: false,
    lastMouseX: 0, lastMouseY: 0, velX: 0, hover: null,
  });
  const [hovered, setHovered] = useState(null);
  const [tooltip, setTooltip] = useState(null);

  const R = 210, SIZE = 600;
  const CX = SIZE / 2, CY = SIZE / 2;

  const toXYZ = (lat, lon, lonRot) => {
    const p = (lat * Math.PI) / 180;
    const l = ((lon - lonRot) * Math.PI) / 180;
    return { x: R * Math.cos(p) * Math.sin(l), y: -R * Math.sin(p), z: R * Math.cos(p) * Math.cos(l) };
  };

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const s = stateRef.current;
    ctx.clearRect(0, 0, SIZE, SIZE);

    const atm = ctx.createRadialGradient(CX, CY, R * 0.85, CX, CY, R * 1.3);
    atm.addColorStop(0, 'rgba(0, 240, 255, 0.12)');
    atm.addColorStop(0.4,'rgba(99, 102, 241, 0.05)');
    atm.addColorStop(1,  'rgba(0,0,0,0)');
    ctx.beginPath(); ctx.arc(CX, CY, R * 1.3, 0, Math.PI * 2); ctx.fillStyle = atm; ctx.fill();

    const baseGrad = ctx.createRadialGradient(CX - R * 0.3, CY - R * 0.3, R * 0.1, CX, CY, R);
    baseGrad.addColorStop(0, '#0f172a'); baseGrad.addColorStop(0.7, '#020617'); baseGrad.addColorStop(1, '#000000');
    ctx.beginPath(); ctx.arc(CX, CY, R, 0, Math.PI * 2); ctx.fillStyle = baseGrad; ctx.fill();

    ctx.save(); ctx.beginPath(); ctx.arc(CX, CY, R, 0, Math.PI * 2); ctx.clip();

    ctx.strokeStyle = 'rgba(99, 102, 241, 0.15)'; ctx.lineWidth = 0.8;
    for (let lat = -80; lat <= 80; lat += 20) {
      ctx.beginPath(); let first = true;
      for (let lon = -180; lon <= 180; lon += 4) {
        const { x, y, z } = toXYZ(lat, lon, s.lon);
        if (z > 0) { const sx = CX + x, sy = CY + y; first ? ctx.moveTo(sx, sy) : ctx.lineTo(sx, sy); first = false; } else first = true;
      } ctx.stroke();
    }
    for (let lon = -180; lon < 180; lon += 20) {
      ctx.beginPath(); let first = true;
      for (let lat = -90; lat <= 90; lat += 3) {
        const { x, y, z } = toXYZ(lat, lon, s.lon);
        if (z > 0) { const sx = CX + x, sy = CY + y; first ? ctx.moveTo(sx, sy) : ctx.lineTo(sx, sy); first = false; } else first = true;
      } ctx.stroke();
    }

    CONTINENTS.forEach(poly => {
      ctx.beginPath(); let started = false;
      poly.forEach(([lat, lon]) => {
        const { x, y, z } = toXYZ(lat, lon, s.lon);
        if (z > -15) { const sx = CX + x, sy = CY + y; if (!started) { ctx.moveTo(sx, sy); started = true; } else ctx.lineTo(sx, sy); } else { if (started) ctx.closePath(); started = false; }
      });
      ctx.fillStyle = 'rgba(0, 240, 255, 0.08)'; ctx.strokeStyle = 'rgba(99, 102, 241, 0.4)'; ctx.lineWidth = 1.2; ctx.fill(); ctx.stroke();
    });
    ctx.restore();

    ctx.beginPath(); ctx.arc(CX, CY, R, 0, Math.PI * 2); ctx.strokeStyle = 'rgba(0, 240, 255, 0.25)'; ctx.lineWidth = 2; ctx.stroke();

    const markerPositions = [];
    STOCKS.forEach(stock => {
      const { x, y, z } = toXYZ(stock.lat, stock.lon, s.lon);
      if (z < -R * 0.15) return;
      const sx = CX + x, sy = CY + y;
      const isUp = stock.chg >= 0; const col = isUp ? T.buy : T.sell;
      const isHov = s.hover === stock.id;
      const fadeFactor = Math.max(0.2, Math.min(1, (z + R * 0.15) / (R * 0.6)));

      ctx.save(); ctx.globalAlpha = fadeFactor;
      ctx.beginPath(); ctx.arc(sx, sy, isHov ? 16 : 10, 0, Math.PI * 2);
      ctx.fillStyle = isHov ? `${col}60` : `${col}30`; ctx.shadowColor = col; ctx.shadowBlur = 15; ctx.fill();
      ctx.beginPath(); ctx.arc(sx, sy, isHov ? 5 : 3, 0, Math.PI * 2); ctx.fillStyle = '#fff'; ctx.fill();
      ctx.restore();

      if (z > R * 0.2 || isHov) {
        ctx.save(); ctx.globalAlpha = Math.min(1, fadeFactor * 1.5);
        const lx = sx + 12, ly = sy - 4;
        const label = `${stock.id} ${stock.chg >= 0 ? '+' : ''}${stock.chg}%`;
        ctx.font = 'bold 12px monospace';
        const tw = ctx.measureText(label).width;
        ctx.fillStyle = 'rgba(2, 4, 10, 0.85)'; ctx.strokeStyle = `${col}60`; ctx.lineWidth = 1;
        ctx.beginPath(); ctx.roundRect(lx - 4, ly - 12, tw + 12, 18, 4); ctx.fill(); ctx.stroke();
        ctx.fillStyle = col; ctx.shadowColor = col; ctx.shadowBlur = 5; ctx.fillText(label, lx + 2, ly + 1);
        ctx.restore();
      }
      markerPositions.push({ id: stock.id, sx, sy, r: 14 });
    });
    stateRef.current._markers = markerPositions;
  }, []);

  useEffect(() => {
    let lastTime = 0;
    const loop = (ts) => {
      const s = stateRef.current;
      if (s.autoSpin && !s.isDragging) s.lon = (s.lon + 0.05) % 360;
      if (!s.isDragging && Math.abs(s.velX) > 0.01) { s.lon += s.velX; s.velX *= 0.92; }
      draw();
      animRef.current = requestAnimationFrame(loop);
    };
    animRef.current = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(animRef.current);
  }, [draw]);

  const handleMouse = (e, type) => {
    const s = stateRef.current;
    const r = canvasRef.current.getBoundingClientRect();
    const mx = e.clientX - r.left, my = e.clientY - r.top;
    if (type === 'down') { s.isDragging = true; s.autoSpin = false; s.velX = 0; s.lastMouseX = mx; s.lastMouseY = my; }
    else if (type === 'move') {
      const markers = s._markers || []; let found = null;
      for (const m of markers) { if (Math.hypot(mx - m.sx, my - m.sy) < m.r) { found = m.id; break; } }
      if (found !== s.hover) { s.hover = found; setHovered(found); setTooltip(found ? { id: found, x: mx, y: my } : null); }
      if (s.isDragging) { const dx = mx - s.lastMouseX; s.velX = dx * 0.4; s.lon += s.velX; s.lastMouseX = mx; s.lastMouseY = my; }
    } else if (type === 'up') {
      s.isDragging = false;
      setTimeout(() => { if (!stateRef.current.isDragging) stateRef.current.autoSpin = true; }, 3000);
      if (Math.abs(s.velX) < 0.5 && s.hover) { const fullStock = STOCKS.find(st => st.id === s.hover); if (fullStock) onSelect(fullStock); }
    } else if (type === 'leave') { s.isDragging = false; setHovered(null); setTooltip(null); s.hover = null; setTimeout(() => { if (!stateRef.current.isDragging) stateRef.current.autoSpin = true; }, 3000); }
  };

  return (
    <div className="flex-1 relative flex items-center justify-center overflow-hidden select-none">
      <canvas ref={canvasRef} width={SIZE} height={SIZE}
        className="relative z-10 drop-shadow-[0_0_50px_rgba(0,240,255,0.1)]"
        style={{ cursor: hovered ? 'pointer' : 'grab', maxWidth:'min(95vw,600px)', maxHeight:'min(95vw,600px)' }}
        onMouseDown={e => handleMouse(e, 'down')} onMouseMove={e => handleMouse(e, 'move')}
        onMouseUp={e => handleMouse(e, 'up')} onMouseLeave={e => handleMouse(e, 'leave')} />
      {tooltip && (() => {
        const s = STOCKS.find(st => st.id === tooltip.id); if (!s) return null;
        const col = s.chg >= 0 ? T.buy : T.sell;
        return (
          <div className="absolute z-30 pointer-events-none rounded-xl px-4 py-3 backdrop-blur-xl transition-all"
            style={{ left: tooltip.x + 20, top: tooltip.y - 30, background: 'rgba(10,15,25,0.85)', border:`1px solid ${col}60`, boxShadow: `0 0 30px ${col}30` }}>
            <div className="flex items-center gap-2 mb-1.5">
              <span className="font-mono font-bold text-base" style={{ color: T.text, textShadow:`0 0 10px ${T.text}80` }}>{s.id}</span>
              <span className="text-[10px] px-1.5 py-0.5 rounded font-bold" style={{ background:`${col}20`, color: col }}>{s.ex}</span>
            </div>
            <div className="text-xs mb-2" style={{ color: T.muted }}>{s.name}</div>
            <div className="flex items-center gap-3">
              <span className="font-mono font-bold text-base" style={{ color: T.text }}>${s.px.toFixed(2)}</span>
              <span className="font-mono text-sm font-bold" style={{ color: col, textShadow:`0 0 10px ${col}80` }}>
                {s.chg >= 0 ? '▲' : '▼'} {Math.abs(s.chg)}%
              </span>
            </div>
          </div>
        );
      })()}
      <div className="absolute bottom-8 left-1/2 -translate-x-1/2 flex items-center gap-6 px-4 py-2 rounded-full backdrop-blur-md" style={{ background: T.glass, border:`1px solid ${T.border}` }}>
        <div className="flex items-center gap-2 text-xs" style={{ color: T.muted }}>
          <Activity size={12} style={{ color: T.buy }} className="animate-pulse" />
          <span style={{ fontSize:10, textTransform:'uppercase', letterSpacing:'1px' }}>System Live · Drag to Pan</span>
        </div>
      </div>
    </div>
  );
}
