import React, { useRef, useEffect, useState, useMemo } from "react";
import Globe from "react-globe.gl";
import { TrendingUp, TrendingDown, Zap, Search, X } from "lucide-react";
import countriesGeo from "../world.json";

// Restoration of the "Neon Claymorphism" Palette
const NEON_PALETTE = [
  'rgba(0, 240, 255, 0.55)', // Cyan
  'rgba(99, 102, 241, 0.50)', // Indigo
  'rgba(168, 85, 247, 0.45)', // Purple
  'rgba(59, 130, 246, 0.40)', // Blue
  'rgba(6, 182, 212, 0.50)',  // Teal
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
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });
  const [searchQuery, setSearchQuery] = useState("");
  const [showAllStocks, setShowAllStocks] = useState(false);
  const [globeConfig, setGlobeConfig] = useState({
    autoRotate: true,
    autoRotateSpeed: 0.8,
  });
  const [selectedStock, setSelectedStock] = useState(null);
  const [autoRotate, setAutoRotate] = useState(true);

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

    if (globeRef.current) {
      globeRef.current.controls().autoRotate = autoRotate;
      globeRef.current.controls().autoRotateSpeed = globeConfig.autoRotateSpeed;
    }

    return () => window.removeEventListener('resize', updateSize);
  }, [autoRotate, globeConfig.autoRotateSpeed]);

  const filteredStocks = useMemo(() => {
    if (!Array.isArray(stocks)) return [];
    if (!searchQuery.trim()) return stocks;
    const q = searchQuery.toLowerCase();
    return stocks.filter(s =>
      (s.id || s.ticker || '').toLowerCase().includes(q) ||
      (s.name || '').toLowerCase().includes(q)
    );
  }, [stocks, searchQuery]);

  // Vibrant "Clay" Contrast Palette
  const COL_POSITIVE = "#00f0ff"; // Original Cyan
  const COL_NEGATIVE = "#ff2a5f"; // Original Red-Pink

  const STOCK_POINTS = useMemo(() => {
    if (!Array.isArray(stocks)) return [];
    return stocks.map((s, index) => {
      const { lat, lng } = s;
      
      // Deterministic jitter to prevent stacking in financial hubs (like NYC)
      // Generates a tiny spiral-like offset based on the stock index
      const jitterAmount = 0.5; // Degrees
      const angle = (index * 137.5) * (Math.PI / 180); // Golden angle
      const radius = index > 0 ? (index % 5) * (jitterAmount / 5) : 0;
      
      const jitteredLat = (lat || 40.7) + (radius * Math.sin(angle));
      const jitteredLng = (lng || -74.0) + (radius * Math.cos(angle));

      return {
        lat: jitteredLat,
        lng: jitteredLng,
        size: 0.15,
        color: (s.chg || s.pct_chg || 0) >= 0 ? 'rgba(0, 240, 255, 0.8)' : 'rgba(255, 42, 95, 0.7)',
        label: `
          <div class="p-4 bg-[#0a0f1e]/90 backdrop-blur-xl border border-indigo-500/30 rounded-2xl shadow-2xl min-w-[150px]">
            <div class="flex items-center justify-between mb-2">
              <span class="text-xs font-black text-white uppercase tracking-tighter">${s.id}</span>
              <span class="text-[9px] font-bold ${(s.chg || 0) >= 0 ? 'text-cyan-400' : 'text-rose-400'}">
                ${(s.chg || 0) >= 0 ? '▲' : '▼'} ${Math.abs(s.chg || 0).toFixed(2)}%
              </span>
            </div>
            <div class="space-y-1">
              <div class="flex justify-between">
                <span class="text-[8px] text-slate-500 font-bold uppercase">Price</span>
                <span class="text-[10px] font-mono text-cyan-300">$${s.px?.toFixed(2)}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-[8px] text-slate-500 font-bold uppercase">MCAP</span>
                <span class="text-[10px] font-mono text-indigo-300 font-bold">${s.mcap || 'N/A'}</span>
              </div>
            </div>
          </div>
        `,
        ticker: s.id || s.ticker,
        raw: s
      };
    });
  }, [stocks]);

  const ARCS_DATA = useMemo(() => {
    const stockArcs = [];
    if (Array.isArray(stocks) && stocks.length >= 2) {
      stocks.slice(0, 10).forEach((s, i) => {
        const next = stocks[(i + 1) % stocks.length];
        if (s.lat && next.lat) {
          stockArcs.push({
            startLat: s.lat, startLng: s.lng,
            endLat: next.lat, endLng: next.lng,
            color: ['rgba(0, 240, 255, 0.6)', 'rgba(168, 85, 247, 0.6)'],
            arcAlt: 0.3
          });
        }
      });
    }

    return stockArcs;
  }, [stocks]);

  const RINGS_DATA = useMemo(() => {
    if (!Array.isArray(stocks) || stocks.length === 0) return [];
    return stocks.filter(s => s.lat && s.lng && s.px > 0).map((s, index) => {
      const key = String(s.id || s.ticker || s.name || index);
      const pulseOffset = [...key].reduce((sum, char) => sum + char.charCodeAt(0), index * 97) % 800;
      return {
        lat: s.lat,
        lng: s.lng,
        maxR: (s.chg || s.pct_chg || 0) >= 0 ? 3 : 2,
        propagationSpeed: 2,
        repeatPeriod: 1200 + pulseOffset,
        color: (s.chg || s.pct_chg || 0) >= 0 ? 'rgba(0, 240, 255, 0.5)' : 'rgba(255, 42, 95, 0.4)',
      };
    });
  }, [stocks]);

  const sidebarStocks = showAllStocks ? filteredStocks : filteredStocks.slice(0, 10);

  const getSignalStyle = (chg) => {
    if (chg > 0.4) return { bg: 'rgba(34, 197, 94, 0.15)', border: 'rgba(34, 197, 94, 0.3)', text: '#4ade80', label: 'BUY' };
    if (chg < -0.4) return { bg: 'rgba(239, 68, 68, 0.15)', border: 'rgba(239, 68, 68, 0.3)', text: '#f87171', label: 'SELL' };
    return { bg: 'rgba(251, 191, 36, 0.15)', border: 'rgba(251, 191, 36, 0.3)', text: '#fbbf24', label: 'HOLD' };
  };

  const handlePointClick = (point) => {
    setAutoRotate(false);
    setSelectedStock(point.raw);
    if (globeRef.current) {
      globeRef.current.pointOfView({ lat: point.lat, lng: point.lng, altitude: 0.5 }, 1000);
    }
  };

  return (
    <div className="w-full h-full relative overflow-hidden" ref={containerRef}>
      
      {/* Enhanced Environment Glow */}
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

        atmosphereColor={globeConfig.atmosphereColor}
        atmosphereAltitude={globeConfig.atmosphereAltitude}
        showAtmosphere={globeConfig.showAtmosphere}

        hexPolygonsData={countriesGeo.features}
        hexPolygonResolution={3}
        hexPolygonMargin={0.7}
        hexPolygonUseDots={true}
        hexPolygonColor={() => globeConfig.polygonColor}
        hexPolygonAltitude={globeConfig.polygonAltitude || 0.01}

        pointsData={STOCK_POINTS}
        pointAltitude={0.07}
        pointRadius="size"
        pointColor="color"
        pointLabel="label"
        onPointHover={(point) => {
          if (point) setAutoRotate(false);
          else if (!selectedStock) setAutoRotate(true);
        }}
        onPointClick={handlePointClick}

        arcsData={ARCS_DATA}
        arcColor="color"
        arcDashLength={globeConfig.arcLength}
        arcDashAnimateTime={globeConfig.arcTime}
        arcAltitude="arcAlt"

        ringsData={RINGS_DATA}
        ringColor="color"
        ringMaxRadius="maxR"
      />

      {/* Selected Stock Summary Overlay */}
      {selectedStock && (
        <div className="absolute bottom-24 p-6 left-6 z-40 w-80 bg-[#0a1020]/90 backdrop-blur-3xl border border-indigo-500/30 rounded-3xl shadow-2xl animate-in fade-in slide-in-from-bottom-4 duration-300">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-xl font-black text-white tracking-tight">{selectedStock.id}</h3>
              <p className="text-[10px] text-slate-400 font-bold uppercase tracking-widest">{selectedStock.sector}</p>
            </div>
            <button 
              onClick={() => { setSelectedStock(null); setAutoRotate(true); }}
              className="p-2 hover:bg-white/10 rounded-full transition-colors text-slate-400"
            >
              <X size={16} />
            </button>
          </div>
          
          <div className="grid grid-cols-2 gap-4 mb-6">
            <div className="p-3 bg-white/5 rounded-2xl border border-white/5">
              <span className="text-[9px] text-slate-500 font-bold uppercase block mb-1">Price</span>
              <span className="text-lg font-mono font-bold text-cyan-400">${selectedStock.px}</span>
            </div>
            <div className="p-3 bg-white/5 rounded-2xl border border-white/5">
              <span className="text-[9px] text-slate-500 font-bold uppercase block mb-1">Market Cap</span>
              <span className="text-lg font-mono font-bold text-indigo-400">{selectedStock.mcap}</span>
            </div>
          </div>

          <div className="flex gap-2">
            <button onClick={() => onStockSelect?.(selectedStock.id)}
              className="flex-1 py-3 bg-indigo-600 hover:bg-indigo-500 text-white text-[11px] font-bold rounded-2xl transition-all shadow-lg shadow-indigo-600/20 uppercase tracking-widest">
              Stock Terminal
            </button>
            <button onClick={() => setAutoRotate(true)}
              className="p-3 bg-white/5 hover:bg-white/10 text-slate-300 rounded-2xl transition-all border border-white/10">
              <Zap size={14} />
            </button>
          </div>
        </div>
      )}

      {/* Clay HUD Control - Bubbled Aesthetic */}
      <div className="absolute bottom-10 left-1/2 -translate-x-1/2 z-30">
        <div className="flex items-center gap-6 px-6 py-3 rounded-2xl bg-[#0a0f1e]/65 backdrop-blur-2xl border border-indigo-500/25 shadow-[0_10px_40px_rgba(0,0,0,0.6),inset_0_1px_1px_rgba(255,255,255,0.05)]">
          <div className="flex items-center gap-3">
             <div className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse shadow-[0_0_8px_rgba(0,240,255,0.6)]" />
             <span className="text-[10px] font-bold tracking-[0.15em] text-slate-300 uppercase">
               Global Cluster Nodes // {stocks.length} Live
             </span>
          </div>
          <div className="w-[1px] h-4 bg-white/10" />
          <div className="flex items-center gap-2">
            <Zap size={10} className="text-indigo-400" />
            <span className="text-[9px] font-mono text-slate-500 font-bold uppercase tracking-widest">AITradra PRO Active</span>
          </div>
        </div>
      </div>

      {/* Floating Stock Navigator (Clay Style Cards) */}
      <div className="absolute top-6 right-6 z-30 w-64 flex flex-col gap-3 pointer-events-auto">
        {/* Soft Search Bar */}
        <div className="relative group mb-1">
          <Search size={14} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500 group-focus-within:text-cyan-400 transition-colors" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search stocks..."
            className="w-full pl-11 pr-10 py-3 rounded-2xl bg-[#0a0f1e]/75 backdrop-blur-2xl border border-white/10 text-[11px] text-white placeholder:text-slate-600 outline-none focus:border-indigo-500/40 transition-all shadow-xl"
          />
          {searchQuery && (
            <button onClick={() => setSearchQuery("")} className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-600 hover:text-white">
              <X size={14} />
            </button>
          )}
        </div>

        {/* Bubbled Data Stack */}
        <div className="space-y-2 max-h-[60vh] overflow-y-auto no-scrollbar py-1">
          {sidebarStocks.map(s => {
            const chg = s.chg || s.pct_chg || 0;
            const signal = getSignalStyle(chg);
            return (
              <button key={s.id || s.ticker} onClick={() => onStockSelect?.(s.id || s.ticker)}
                className="flex items-center gap-4 px-3 py-2.5 rounded-2xl w-full transition-all hover:scale-[1.02] bg-[#0a0f1e]/60 backdrop-blur-xl border border-white/5 hover:border-indigo-500/20 shadow-lg group relative overflow-hidden text-left">
                <div className="w-8 h-8 rounded-xl flex items-center justify-center shrink-0 border transition-all duration-120 group-hover:scale-110"
                   style={{ background: `${signal.text}15`, borderColor: `${signal.text}30`, color: signal.text }}>
                   {chg >= 0 ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between mb-0.5">
                    <span className="font-bold text-[12px] text-white group-hover:text-cyan-400 transition-colors uppercase tracking-tight">{s.id || s.ticker}</span>
                    <span className="text-[7px] px-1.5 py-0.5 rounded font-black tracking-widest uppercase"
                      style={{ background: signal.bg, border: `1px solid ${signal.border}`, color: signal.text }}>
                      {signal.label}
                    </span>
                  </div>
                  <div className="flex items-center gap-3 font-mono">
                    <span className="text-[10px] font-bold text-slate-300">${s.px > 0 ? s.px.toLocaleString() : '---'}</span>
                    <span className="text-[9px] font-bold" style={{ color: signal.text }}>
                      {chg >= 0 ? '+' : ''}{typeof chg === 'number' ? chg.toFixed(2) : chg}%
                    </span>
                  </div>
                </div>
              </button>
            );
          })}
        </div>

        {filteredStocks.length > 10 && (
          <button
            onClick={() => setShowAllStocks(!showAllStocks)}
            className="w-full py-2.5 rounded-2xl bg-[#0a0f1e]/40 border border-white/5 text-[9px] text-indigo-400 font-bold tracking-[0.2em] uppercase hover:bg-indigo-500/10 transition-all active:scale-95 shadow-md"
          >
            {showAllStocks ? `Collapse Search` : `Expanding ${filteredStocks.length} Nodes`}
          </button>
        )}
      </div>
    </div>
  );
}
