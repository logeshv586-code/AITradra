import React, { useRef, useEffect, useState, useMemo, useCallback } from "react";
import Globe from "react-globe.gl";
import { Activity, TrendingUp, TrendingDown, Zap, Search, X } from "lucide-react";

// Premium Neon Color Palette
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
  const [searchQuery, setSearchQuery] = useState("");
  const [showAllStocks, setShowAllStocks] = useState(false);

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

  // Filter stocks by search
  const filteredStocks = useMemo(() => {
    if (!searchQuery.trim()) return stocks;
    const q = searchQuery.toLowerCase();
    return stocks.filter(s =>
      (s.id || s.ticker || '').toLowerCase().includes(q) ||
      (s.name || '').toLowerCase().includes(q)
    );
  }, [stocks, searchQuery]);

  const STOCK_POINTS = useMemo(() => stocks.map(s => ({
    lat: s.lat || 40.7,
    lng: s.lon || -74.0,
    size: s.px > 0 ? 0.8 : 0.3,
    color: (s.chg || s.pct_chg || 0) >= 0 ? '#00f0ff' : '#ff2a5f',
    label: `${s.id || s.ticker} $${s.px || 0} (${(s.chg || s.pct_chg || 0).toFixed?.(2) || 0}%)`,
    ticker: s.id || s.ticker
  })), [stocks]);

  const ARCS_DATA = useMemo(() => {
    if (stocks.length < 2) return [];
    return stocks.slice(0, 8).map((s, i) => {
      const next = stocks[(i + 1) % stocks.length];
      return {
        startLat: s.lat, startLng: s.lon,
        endLat: next.lat, endLng: next.lon,
        color: ['rgba(0,240,255,0.6)', 'rgba(168,85,247,0.6)'],
      };
    }).filter(a => a.startLat && a.endLat);
  }, [stocks]);

  const RINGS_DATA = useMemo(() => stocks.filter(s => s.lat && s.lon && s.px > 0).map(s => ({
    lat: s.lat,
    lng: s.lon,
    maxR: (s.chg || s.pct_chg || 0) >= 0 ? 3 : 2,
    propagationSpeed: 2,
    repeatPeriod: 1200 + Math.random() * 800,
    color: (s.chg || s.pct_chg || 0) >= 0 ? 'rgba(0,240,255,0.5)' : 'rgba(255,42,95,0.4)',
  })), [stocks]);

  // Stocks to show in the sidebar list
  const sidebarStocks = showAllStocks ? filteredStocks : filteredStocks.slice(0, 8);

  // Signal color
  const getSignalColor = (chg) => {
    if (chg > 0.5) return { bg: 'rgba(34,197,94,0.15)', border: 'rgba(34,197,94,0.3)', text: '#4ade80', label: 'BUY' };
    if (chg < -0.5) return { bg: 'rgba(239,68,68,0.15)', border: 'rgba(239,68,68,0.3)', text: '#f87171', label: 'SELL' };
    return { bg: 'rgba(251,191,36,0.15)', border: 'rgba(251,191,36,0.3)', text: '#fbbf24', label: 'HOLD' };
  };

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
            <span className="tracking-wider uppercase">Qwen 1.5B Active</span>
          </div>
          <div className="w-px h-4 bg-white/10" />
          <div className="flex items-center gap-1.5">
            <div className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
            <span className="text-[9px] font-mono text-green-400/80">{stocks.filter(s => s.px > 0).length} synced</span>
          </div>
        </div>
      </div>

      {/* Floating Stock List with Search */}
      <div className="absolute top-4 right-4 z-30 hidden md:block w-56">
        {/* Search Bar */}
        <div className="relative mb-2">
          <Search size={12} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search stocks..."
            className="w-full pl-8 pr-8 py-2 rounded-xl bg-[#0a0f1e]/70 backdrop-blur-xl border border-white/10 text-[11px] text-white placeholder:text-slate-600 outline-none focus:border-indigo-500/50 transition-colors"
          />
          {searchQuery && (
            <button onClick={() => setSearchQuery("")} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-white">
              <X size={12} />
            </button>
          )}
        </div>

        {/* Stock Cards */}
        <div className="space-y-1.5 max-h-[60vh] overflow-y-auto no-scrollbar">
          {sidebarStocks.map(s => {
            const chg = s.chg || s.pct_chg || 0;
            const col = chg >= 0 ? '#4ade80' : '#f87171';
            const signal = getSignalColor(chg);
            return (
              <button key={s.id || s.ticker} onClick={() => onStockSelect(s.id || s.ticker)}
                className="flex items-center gap-2.5 px-2.5 py-2 rounded-xl w-full transition-all hover:scale-[1.02] bg-[#0a0f1e]/55 backdrop-blur-md border border-white/5 shadow-lg group">
                <div className="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0"
                  style={{ background: `${col}15`, border: `1px solid ${col}30` }}>
                  {chg >= 0 ? <TrendingUp size={12} color={col} /> : <TrendingDown size={12} color={col} />}
                </div>
                <div className="text-left flex-1 min-w-0">
                  <div className="flex items-center gap-1.5">
                    <span className="font-mono font-bold text-[11px] text-white group-hover:text-cyan-300 transition-colors">{s.id || s.ticker}</span>
                    <span className="text-[7px] px-1.5 py-0.5 rounded font-black tracking-wider"
                      style={{ background: signal.bg, border: `1px solid ${signal.border}`, color: signal.text }}>
                      {signal.label}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-[10px] text-slate-300">{s.px > 0 ? `$${s.px}` : '...'}</span>
                    <span className="font-mono text-[9px] font-bold" style={{ color: col }}>
                      {chg >= 0 ? '+' : ''}{typeof chg === 'number' ? chg.toFixed(2) : chg}%
                    </span>
                  </div>
                </div>
              </button>
            );
          })}
        </div>

        {/* Show All / Show Less */}
        {filteredStocks.length > 8 && (
          <button
            onClick={() => setShowAllStocks(!showAllStocks)}
            className="w-full mt-2 py-1.5 rounded-xl bg-[#0a0f1e]/40 border border-white/5 text-[9px] text-indigo-400 font-bold tracking-wider uppercase hover:bg-indigo-500/10 transition-colors"
          >
            {showAllStocks ? `Show Less` : `Show All ${filteredStocks.length} Stocks`}
          </button>
        )}
      </div>
    </div>
  );
}
