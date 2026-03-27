import React, { useRef, useEffect, useState, useMemo, useCallback } from "react";
import Globe from "react-globe.gl";
import { Activity, TrendingUp, TrendingDown, Zap } from "lucide-react";

// ─── Premium Neon Color Palette ──────────────────────────────────────────────
const NEON_PALETTE = [
  'rgba(0, 240, 255, 0.55)',
  'rgba(99, 102, 241, 0.50)',
  'rgba(168, 85, 247, 0.45)',
  'rgba(59, 130, 246, 0.40)',
  'rgba(6, 182, 212, 0.50)',
];

function getCountryColor(isoCode) {
  if (!isoCode || isoCode === '-99') return 'rgba(30, 41, 59, 0.3)';
  let hash = 0;
  for (let i = 0; i < isoCode.length; i++) {
    hash = isoCode.charCodeAt(i) + ((hash << 5) - hash);
  }
  return NEON_PALETTE[Math.abs(hash) % NEON_PALETTE.length];
}

export default function Globe3D({ onStockSelect, stocks = [] }) {
  const globeRef = useRef();
  const containerRef = useRef();
  const [countries, setCountries] = useState({ features: [] });
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });

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

  const STOCK_POINTS = useMemo(() => stocks.map(s => ({
    lat: s.lat || 40.7,
    lng: s.lon || -74.0,
    size: 0.8,
    color: (s.chg || s.pct_chg) >= 0 ? '#00f0ff' : '#ff2a5f',
    label: `${s.id || s.ticker} $${s.px} (${s.chg || s.pct_chg}%)`,
    ticker: s.id || s.ticker
  })), [stocks]);

  const ARCS_DATA = useMemo(() => {
    if (stocks.length < 2) return [];
    return stocks.slice(0, 6).map((s, i) => {
      const next = stocks[(i + 1) % stocks.length];
      return {
        startLat: s.lat, startLng: s.lon,
        endLat: next.lat, endLng: next.lon,
        color: ['rgba(0,240,255,0.6)', 'rgba(168,85,247,0.6)'],
      };
    }).filter(a => a.startLat && a.endLat);
  }, [stocks]);

  const RINGS_DATA = useMemo(() => stocks.filter(s => s.lat && s.lon).map(s => ({
    lat: s.lat,
    lng: s.lon,
    maxR: (s.chg || s.pct_chg) >= 0 ? 3 : 2,
    propagationSpeed: 2,
    repeatPeriod: 1200 + Math.random() * 800,
    color: (s.chg || s.pct_chg) >= 0 ? 'rgba(0,240,255,0.5)' : 'rgba(255,42,95,0.4)',
  })), [stocks]);

  return (
    <div className="w-full h-full relative overflow-hidden" ref={containerRef}>
      {/* Background Glow */}
      <div className="absolute inset-0 pointer-events-none z-0">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[70vmin] h-[70vmin] rounded-full bg-indigo-500/8 blur-[100px]" />
      </div>

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
        hexPolygonAltitude={0.01}

        pointsData={STOCK_POINTS}
        pointAltitude={0.07}
        pointRadius="size"
        pointColor="color"
        pointLabel="label"
        onPointClick={(p) => onStockSelect(p.ticker)}

        arcsData={ARCS_DATA}
        arcColor="color"
        arcDashLength={0.4}
        arcDashAnimateTime={2500}
        arcAltitudeAutoScale={0.3}

        ringsData={RINGS_DATA}
        ringColor="color"
        ringMaxRadius="maxR"
      />

      {/* Bottom HUD Bar */}
      <div className="absolute bottom-6 left-1/2 -translate-x-1/2 z-30">
        <div className="flex items-center gap-5 px-5 py-2.5 rounded-2xl bg-[#0a0f1e]/60 backdrop-blur-xl border border-indigo-500/25 shadow-2xl">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse shadow-[0_0_8px_rgba(0,240,255,0.6)]" />
            <span className="text-[10px] font-bold tracking-[0.15em] text-slate-300 uppercase">
              {stocks.length} Assets Live
            </span>
          </div>
          <div className="w-px h-4 bg-white/10" />
          <div className="flex items-center gap-1.5 text-[10px] font-medium text-slate-400">
            <Zap size={10} className="text-indigo-400" />
            <span className="tracking-wider uppercase">Neural Link Active</span>
          </div>
        </div>
      </div>

      {/* Floating Stock List (The "with stock showing" part) */}
      <div className="absolute top-4 right-4 z-30 space-y-2 hidden md:block">
        {stocks.slice(0, 5).map(s => {
          const col = (s.chg || s.pct_chg) >= 0 ? '#4ade80' : '#f87171';
          return (
            <button key={s.id || s.ticker} onClick={() => onStockSelect(s.id || s.ticker)}
              className="flex items-center gap-3 px-3 py-2 rounded-xl w-48 transition-all hover:scale-[1.03] bg-[#0a0f1e]/55 backdrop-blur-md border border-white/5 shadow-lg group">
              <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
                style={{ background: `${col}15`, border: `1px solid ${col}30` }}>
                {(s.chg || s.pct_chg) >= 0 ? <TrendingUp size={14} color={col} /> : <TrendingDown size={14} color={col} />}
              </div>
              <div className="text-left flex-1 min-w-0">
                <div className="font-mono font-bold text-xs text-white group-hover:text-cyan-300 transition-colors">{s.id || s.ticker}</div>
                <div className="flex items-center gap-2">
                  <span className="font-mono text-[11px] text-slate-300">${s.px}</span>
                  <span className="font-mono text-[10px] font-bold" style={{ color: col }}>
                    {((s.chg || s.pct_chg) >= 0 ? '+' : '') + (s.chg || s.pct_chg)}%
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
