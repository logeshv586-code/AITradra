import React, { useRef, useEffect, useState, useMemo, useCallback } from "react";
import Globe from "react-globe.gl";
import { T } from "../theme";
import { Activity, TrendingUp, TrendingDown, Zap } from "lucide-react";

// ─── Premium Neon Color Palette for Hex Polygons ──────────────────────────────
const NEON_PALETTE = [
  'rgba(0, 240, 255, 0.55)',
  'rgba(99, 102, 241, 0.50)',
  'rgba(168, 85, 247, 0.45)',
  'rgba(59, 130, 246, 0.40)',
  'rgba(6, 182, 212, 0.50)',
  'rgba(99, 102, 241, 0.35)',
  'rgba(139, 92, 246, 0.45)',
  'rgba(14, 165, 233, 0.50)',
];

function getCountryColor(isoCode) {
  if (!isoCode || isoCode === '-99') return 'rgba(30, 41, 59, 0.3)';
  let hash = 0;
  for (let i = 0; i < isoCode.length; i++) {
    hash = isoCode.charCodeAt(i) + ((hash << 5) - hash);
  }
  return NEON_PALETTE[Math.abs(hash) % NEON_PALETTE.length];
}

export default function GlobeView({ onSelect, stocks = [] }) {
  const globeRef = useRef();
  const containerRef = useRef();
  const [countries, setCountries] = useState({ features: [] });
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });

  // Dynamically build globe data from live stocks
  const STOCK_POINTS = useMemo(() => stocks.map(s => ({
    lat: s.lat || s.latitude || 40.7,
    lng: s.lng || s.longitude || -74.0,
    size: 0.6,
    color: (s.pct_chg || s.chg || 0) >= 0 ? '#00f0ff' : '#ff2a5f',
    stock: s,
  })), [stocks]);

  const ARCS_DATA = useMemo(() => {
    if (stocks.length < 2) return [];
    const arcs = [];
    for (let i = 0; i < Math.min(stocks.length - 1, 6); i++) {
      const a = stocks[i];
      const b = stocks[(i + 1) % stocks.length];
      if (a.lat && b.lat && a.lng && b.lng) {
        arcs.push({
          startLat: a.lat, startLng: a.lng,
          endLat: b.lat, endLng: b.lng,
          color: ['rgba(0,240,255,0.6)', 'rgba(168,85,247,0.6)'],
        });
      }
    }
    return arcs;
  }, [stocks]);

  const RINGS_DATA = useMemo(() => stocks.filter(s => s.lat && s.lng).map((s, index) => {
    const key = String(s.id || s.ticker || s.name || index);
    const pulseOffset = [...key].reduce((sum, char) => sum + char.charCodeAt(0), index * 97) % 800;
    return {
      lat: s.lat,
      lng: s.lng,
      maxR: (s.pct_chg || s.chg || 0) >= 0 ? 3 : 2,
      propagationSpeed: 2,
      repeatPeriod: 1200 + pulseOffset,
      color: (s.pct_chg || s.chg || 0) >= 0 ? 'rgba(0,240,255,0.5)' : 'rgba(255,42,95,0.4)',
    };
  }), [stocks]);

  // Load GeoJSON
  useEffect(() => {
    fetch('https://raw.githubusercontent.com/vasturiano/react-globe.gl/master/example/datasets/ne_110m_admin_0_countries.geojson')
      .then(res => res.json())
      .then(data => setCountries(data));
  }, []);

  // Responsive sizing
  useEffect(() => {
    const updateSize = () => {
      if (containerRef.current) {
        setDimensions({
          width: containerRef.current.offsetWidth,
          height: containerRef.current.offsetHeight
        });
      }
    };
    updateSize();
    window.addEventListener('resize', updateSize);
    return () => window.removeEventListener('resize', updateSize);
  }, []);

  // Setup globe after mount
  useEffect(() => {
    if (!globeRef.current) return;
    const globe = globeRef.current;
    globe.controls().autoRotate = true;
    globe.controls().autoRotateSpeed = 0.6;
    globe.controls().enableDamping = true;
    globe.controls().dampingFactor = 0.1;
    globe.controls().minDistance = 150;
    globe.controls().maxDistance = 500;
    globe.pointOfView({ lat: 20, lng: 0, altitude: 2.2 });
  }, [countries]);

  const hexLabel = useCallback((d) => {
    const props = d.properties;
    if (!props) return '';
    return `
      <div style="
        padding: 10px 14px;
        background: rgba(10, 15, 30, 0.85);
        backdrop-filter: blur(16px);
        border: 1px solid rgba(99, 102, 241, 0.4);
        border-radius: 10px;
        font-family: 'Inter', sans-serif;
        color: #f8fafc;
        box-shadow: 0 0 25px rgba(99,102,241,0.3), 0 8px 32px rgba(0,0,0,0.4);
        min-width: 140px;
      ">
        <div style="font-size: 13px; font-weight: 700; margin-bottom: 4px; color: #818cf8;">
          ${props.ADMIN || props.NAME || 'Unknown'}
        </div>
        <div style="font-size: 10px; color: #94a3b8; letter-spacing: 1px; text-transform: uppercase;">
          ${props.ISO_A2 || ''} · ${props.CONTINENT || ''}
        </div>
      </div>
    `;
  }, []);

  const pointLabel = useCallback((d) => {
    const s = d.stock;
    const col = s.chg >= 0 ? '#00f0ff' : '#ff2a5f';
    const dir = s.chg >= 0 ? '▲' : '▼';
    return `
      <div style="
        padding: 12px 16px;
        background: rgba(10, 15, 30, 0.9);
        backdrop-filter: blur(20px);
        border: 1px solid ${col}60;
        border-radius: 12px;
        font-family: 'Inter', sans-serif;
        color: #f8fafc;
        box-shadow: 0 0 30px ${col}40, 0 8px 32px rgba(0,0,0,0.5);
        min-width: 180px;
      ">
        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px;">
          <span style="font-size: 15px; font-weight: 800; font-family: 'JetBrains Mono', monospace; text-shadow: 0 0 10px ${col};">${s.id}</span>
          <span style="font-size: 9px; padding: 2px 6px; border-radius: 4px; font-weight: 700; background: ${col}20; color: ${col}; border: 1px solid ${col}40;">${s.ex || 'N/A'}</span>
        </div>
        <div style="font-size: 11px; color: #94a3b8; margin-bottom: 8px;">${s.name}</div>
        <div style="display: flex; align-items: center; gap: 10px;">
          <span style="font-size: 16px; font-weight: 800; font-family: 'JetBrains Mono', monospace;">$${(s.px || 0).toFixed(2)}</span>
          <span style="font-size: 13px; font-weight: 700; color: ${col}; text-shadow: 0 0 10px ${col}80;">
            ${dir} ${Math.abs(s.chg || 0)}%
          </span>
        </div>
        <div style="margin-top: 8px; padding-top: 6px; border-top: 1px solid rgba(255,255,255,0.08); font-size: 9px; color: #64748b; letter-spacing: 1px; text-transform: uppercase;">
          MKTCAP: ${s.mcap || 'N/A'} · VOL: ${s.vol || 'N/A'}
        </div>
      </div>
    `;
  }, []);

  const handlePointClick = useCallback((point) => {
    if (point && point.stock) {
      onSelect(point.stock);
    }
  }, [onSelect]);

  return (
    <div className="flex-1 relative flex items-center justify-center overflow-hidden select-none" ref={containerRef}>
      <div className="absolute inset-0 pointer-events-none z-0">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[70vmin] h-[70vmin] rounded-full bg-indigo-500/8 blur-[100px]" />
        <div className="absolute top-[40%] left-[45%] -translate-x-1/2 -translate-y-1/2 w-[50vmin] h-[50vmin] rounded-full bg-cyan-500/6 blur-[80px]" />
      </div>

      <div className="relative z-10 w-full h-full">
        <Globe
          ref={globeRef}
          width={dimensions.width}
          height={dimensions.height}
          backgroundColor="rgba(0,0,0,0)"
          globeImageUrl="//cdn.jsdelivr.net/npm/three-globe/example/img/earth-night.jpg"
          bumpImageUrl="//cdn.jsdelivr.net/npm/three-globe/example/img/earth-topology.png"
          atmosphereColor="#6366f1"
          atmosphereAltitude={0.25}
          hexPolygonsData={countries.features}
          hexPolygonResolution={3}
          hexPolygonMargin={0.4}
          hexPolygonUseDots={true}
          hexPolygonColor={d => getCountryColor(d.properties?.ISO_A2)}
          hexPolygonLabel={hexLabel}
          hexPolygonAltitude={0.01}
          pointsData={STOCK_POINTS}
          pointAltitude={0.07}
          pointRadius="size"
          pointColor="color"
          pointLabel={pointLabel}
          onPointClick={handlePointClick}
          pointsMerge={false}
          arcsData={ARCS_DATA}
          arcColor="color"
          arcDashLength={0.4}
          arcDashGap={0.2}
          arcDashAnimateTime={2500}
          arcStroke={0.5}
          arcAltitudeAutoScale={0.3}
          ringsData={RINGS_DATA}
          ringColor="color"
          ringMaxRadius="maxR"
          ringPropagationSpeed="propagationSpeed"
          ringRepeatPeriod="repeatPeriod"
        />
      </div>

      {/* ── Bottom HUD Bar ── */}
      <div className="absolute bottom-6 left-1/2 -translate-x-1/2 z-30">
        <div className="flex items-center gap-5 px-5 py-2.5 rounded-2xl"
          style={{
            background: 'rgba(10, 15, 30, 0.65)',
            backdropFilter: 'blur(20px)',
            border: '1px solid rgba(99, 102, 241, 0.25)',
            boxShadow: '0 0 30px rgba(99,102,241,0.15), 0 8px 32px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.05)',
          }}>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse shadow-[0_0_8px_rgba(0,240,255,0.6)]" />
            <span className="text-[10px] font-bold tracking-[0.15em] text-slate-300 uppercase">
              {stocks.length > 0 ? `${stocks.length} Assets Live` : 'Loading...'}
            </span>
          </div>
          <div className="w-px h-4 bg-white/10" />
          <div className="flex items-center gap-1.5 text-[10px] font-medium text-slate-400">
            <Zap size={10} className="text-indigo-400" />
            <span className="tracking-wider uppercase">Drag · Zoom · Click Node</span>
          </div>
        </div>
      </div>

      {/* ── Stock Quick Stats Floating Panel ── */}
      <div className="absolute top-4 right-4 z-30 space-y-2">
        {stocks.slice(0, 5).map(s => {
          const col = s.chg >= 0 ? T.buy : T.sell;
          return (
            <button key={s.id} onClick={() => onSelect(s)}
              className="flex items-center gap-3 px-3 py-2 rounded-xl w-48 transition-all hover:scale-[1.03] cursor-pointer group"
              style={{
                background: 'rgba(10, 15, 30, 0.55)',
                backdropFilter: 'blur(16px)',
                border: '1px solid rgba(255,255,255,0.06)',
                boxShadow: 'inset -4px -4px 8px rgba(0,0,0,0.3), inset 4px 4px 8px rgba(255,255,255,0.02), 4px 4px 8px rgba(0,0,0,0.2)',
              }}>
              <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
                style={{ background: `${col}15`, border: `1px solid ${col}30` }}>
                {s.chg >= 0 ? <TrendingUp size={14} style={{ color: col }} /> : <TrendingDown size={14} style={{ color: col }} />}
              </div>
              <div className="text-left flex-1 min-w-0">
                <div className="font-mono font-bold text-xs text-white group-hover:text-cyan-300 transition-colors">{s.id}</div>
                <div className="flex items-center gap-2">
                  <span className="font-mono text-[11px] text-slate-300">${(s.px || 0).toFixed(0)}</span>
                  <span className="font-mono text-[10px] font-bold" style={{ color: col }}>
                    {s.chg >= 0 ? '+' : ''}{s.chg}%
                  </span>
                </div>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
