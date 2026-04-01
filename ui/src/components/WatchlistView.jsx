import React, { useState } from "react";
import { List, ArrowUpRight, ArrowDownRight, Search, Activity, Zap, Info, TrendingUp, TrendingDown, Layers, Loader2 } from "lucide-react";

/**
 * THEME DEFINITION
 * High-contrast, vibrant UI colors for a financial dashboard.
 */
const T = {
  buy: "#22c55e",  // emerald-500
  sell: "#ef4444", // red-500
  warn: "#f59e0b", // amber-500
  accent: "#6366f1", // indigo-500
  bg: "#020617",    // slate-950
};

const FILTERS = ['All Markets', 'US Tech', 'Asia-Pac', 'EU', 'Crypto', 'India'];

const SECTOR_FILTER_MAP = {
  'US Tech': ['Technology', 'Communication Services', 'Consumer Cyclical', 'Semiconductors'],
  'Asia-Pac': ['TYO', 'HKG', 'SHH', 'ASX', 'SGX'],
  'EU': ['LSE', 'FRA', 'PAR', 'SWX'],
  'Crypto': ['Crypto', 'CCC'],
  'India': ['NSI', 'BSE'],
};

/**
 * MINI SPARKLINE COMPONENT
 * Renders a simple SVG trend line.
 */
const MiniSparkline = ({ data = [], color, w = 100, h = 30 }) => {
  if (!data || data.length < 2) return <div className="h-[30px] w-[100px] bg-white/5 rounded animate-pulse" />;
  
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const points = data.map((val, i) => ({
    x: (i / (data.length - 1)) * w,
    y: h - ((val - min) / range) * h
  }));

  const pathData = `M ${points.map(p => `${p.x},${p.y}`).join(' L ')}`;

  return (
    <svg width={w} height={h} className="overflow-visible">
      <path
        d={pathData}
        fill="none"
        stroke={color}
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        className="drop-shadow-[0_0_8px_rgba(255,255,255,0.2)]"
      />
    </svg>
  );
};

export default function WatchlistView({ onSelect, stocks = [], marketIndices = [], loading = false }) {
  const [activeFilter, setActiveFilter] = useState('All Markets');
  const [searchTerm, setSearchTerm] = useState('');

  const filtered = stocks.filter(s => {
    const matchesSearch = s.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (s.name || '').toLowerCase().includes(searchTerm.toLowerCase());
    
    if (activeFilter === 'All Markets') return matchesSearch;
    
    const filterKeys = SECTOR_FILTER_MAP[activeFilter] || [];
    const matchesFilter = filterKeys.some(f => 
      (s.sector || '').toLowerCase().includes(f.toLowerCase()) ||
      (s.ex || '').includes(f) ||
      ((s.id || '').includes('-USD') && activeFilter === 'Crypto')
    );
    return matchesSearch && matchesFilter;
  });

  const sectors = [...new Set(filtered.map(s => s.sector || 'Others'))];

  return (
    <div className="flex-1 p-4 md:p-8 overflow-y-auto no-scrollbar animate-fade-in selection:bg-indigo-500/30">
      <div className="max-w-7xl mx-auto space-y-12">
        
        {/* HEADER SECTION: Glassmorphism + Layout Spacing */}
        <header className="flex flex-col lg:flex-row lg:items-center justify-between gap-10 border-b border-white/5 pb-10">
          <div className="flex items-center gap-6">
            <div className="relative group">
              <div className="absolute -inset-1 bg-gradient-to-r from-indigo-500 to-purple-600 rounded-2xl blur opacity-25 group-hover:opacity-50 transition duration-1000 group-hover:duration-200"></div>
              <div className="relative p-5 bg-slate-900/80 backdrop-blur-xl rounded-2xl border border-white/10 shadow-2xl flex items-center justify-center">
                <Layers size={32} className="text-indigo-400" />
              </div>
            </div>
            <div>
              <h1 className="text-4xl md:text-5xl font-black text-white tracking-tighter uppercase font-mono italic">
                Asset<span className="text-indigo-500">Command</span>
              </h1>
              <p className="text-[10px] font-mono text-slate-500 tracking-[0.5em] uppercase mt-2 flex items-center gap-3">
                <Activity size={12} className="text-indigo-500 animate-pulse" />
                {loading ? 'SYNCHRONIZING_NODES...' : `System Live // ${stocks.length} Global Nodes Connected`}
              </p>
            </div>
          </div>

          {/* SKEUOMORPHIC INDICES PANEL */}
          <div className="flex gap-4 p-2 bg-black/40 rounded-[32px] border border-white/5 shadow-[inset_0_2px_10px_rgba(0,0,0,0.6)] backdrop-blur-2xl overflow-x-auto no-scrollbar">
            {(marketIndices.length > 0 ? marketIndices : [
              { name: 'S&P 500', value: 0, change: 0 },
              { name: 'NASDAQ', value: 0, change: 0 },
              { name: 'DOW J', value: 0, change: 0 }
            ]).map((idx) => (
              <div key={idx.name} className="px-6 py-4 flex flex-col items-start min-w-[160px] bg-gradient-to-b from-white/5 to-transparent rounded-2xl border border-white/5 shadow-lg">
                <span className="text-[9px] uppercase tracking-[0.3em] mb-2 text-slate-500 font-black font-mono">{idx.name}</span>
                <div className="font-mono text-xl font-black flex items-center gap-3">
                  <span className="text-white">{(idx.value || 0).toLocaleString()}</span>
                  <span className={`text-[10px] px-2 py-0.5 rounded-full border ${idx.change >= 0 ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400' : 'bg-red-500/10 border-red-500/20 text-red-400'}`}>
                    {idx.change >= 0 ? '+' : ''}{idx.change}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        </header>

        {/* TOOLBAR: Skeuomorphic Toggles + Glass Input */}
        <section className="flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="flex p-1.5 bg-slate-950 rounded-2xl border border-white/5 shadow-[inset_0_2px_8px_rgba(0,0,0,0.8)] overflow-x-auto no-scrollbar">
            {FILTERS.map(f => (
              <button 
                key={f} 
                onClick={() => setActiveFilter(f)}
                className={`px-6 py-2.5 rounded-xl text-[10px] font-black tracking-widest transition-all duration-300 whitespace-nowrap ${
                  activeFilter === f 
                  ? 'bg-indigo-600 text-white shadow-[0_0_20px_rgba(79,70,229,0.4)] scale-105 z-10' 
                  : 'text-slate-500 hover:text-slate-300'
                }`}
              >
                {f.toUpperCase()}
              </button>
            ))}
          </div>

          <div className="relative group w-full md:w-[400px]">
            <Search size={18} className="absolute left-5 top-1/2 -translate-y-1/2 text-slate-600 group-focus-within:text-indigo-400 transition-colors z-10" />
            <input
              value={searchTerm} 
              onChange={e => setSearchTerm(e.target.value)}
              placeholder="SEARCH INSTRUMENTS..."
              className="bg-slate-900/50 backdrop-blur-md pl-14 pr-6 h-14 w-full text-xs font-mono tracking-widest rounded-2xl outline-none border border-white/5 focus:border-indigo-500/50 focus:bg-slate-900/80 transition-all shadow-[inset_0_2px_4px_rgba(0,0,0,0.3)] text-white"
            />
          </div>
        </section>

        {/* ASSET LIST: Claymorphism Cards + Organized Sections */}
        <div className="space-y-12">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-24 gap-6">
              <div className="relative">
                <div className="w-16 h-16 rounded-full border-4 border-indigo-500/20 border-t-indigo-500 animate-spin" />
                <Zap size={24} className="absolute inset-0 m-auto text-indigo-400 animate-pulse" />
              </div>
              <span className="text-sm text-slate-400 font-mono tracking-widest animate-pulse uppercase">Synchronizing Global Order Books...</span>
            </div>
          ) : (
            sectors.map(sector => {
              const sectorStocks = filtered.filter(s => (s.sector || 'Others') === sector);
              if (sectorStocks.length === 0) return null;
              
              return (
                <div key={sector} className="space-y-6">
                  <div className="flex items-center gap-6 px-2">
                    <div className="h-2 w-2 rounded-full bg-indigo-500 shadow-[0_0_10px_#6366f1]" />
                    <span className="text-xs font-black text-indigo-400 tracking-[0.5em] uppercase italic">{sector}</span>
                    <div className="flex-1 h-px bg-gradient-to-r from-indigo-500/30 via-indigo-500/10 to-transparent" />
                    <span className="text-[9px] font-mono text-slate-600 uppercase tracking-[0.3em] font-bold">{sectorStocks.length} Nodes</span>
                  </div>
                  
                  <div className="grid gap-4">
                    {sectorStocks.map((s) => {
                      const isUp = (s.chg || 0) >= 0;
                      const col = isUp ? T.buy : T.sell;
                      const trendData = s.ohlcv || [];
                      
                      return (
                        <div 
                          key={s.id}
                          onClick={() => onSelect(s)}
                          className="group relative bg-slate-900/40 backdrop-blur-xl p-5 pl-8 rounded-[32px] border border-white/5 flex flex-col lg:flex-row items-center justify-between gap-8 hover:bg-slate-900/60 transition-all duration-500 cursor-pointer shadow-xl hover:shadow-indigo-500/5 hover:-translate-y-1"
                        >
                          {/* Asset Identity: Claymorphism Circle */}
                          <div className="flex items-center gap-8 min-w-[280px] w-full lg:w-auto">
                            <div 
                              className="w-16 h-16 rounded-[22px] flex items-center justify-center text-2xl font-black transition-all shadow-[inset_-4px_-4px_8px_rgba(0,0,0,0.4),inset_4px_4px_8px_rgba(255,255,255,0.1)]"
                              style={{
                                background: `linear-gradient(145deg, ${col}20, ${col}05)`,
                                border: `1px solid ${col}30`,
                                color: col,
                              }}
                            >
                              {(s.id || '?')[0]}
                            </div>
                            <div className="flex flex-col">
                              <span className="font-mono font-black text-2xl text-white group-hover:text-indigo-400 transition-colors tracking-tight uppercase leading-none">
                                {s.id}
                              </span>
                              <span className="text-[10px] text-slate-500 font-bold tracking-[0.3em] uppercase mt-2 opacity-70">
                                {s.name}
                              </span>
                            </div>
                          </div>

                          {/* Metrics Grid */}
                          <div className="flex-1 w-full grid grid-cols-2 md:grid-cols-4 items-center gap-10">
                            <div className="flex flex-col">
                              <span className="text-[10px] font-black text-slate-600 uppercase tracking-widest mb-2 flex items-center gap-2">
                                <Zap size={10} /> Market Price
                              </span>
                              <span className="font-mono text-xl font-black text-white">
                                {s.id.includes('-USD') ? '' : '$'}{(s.px || 0).toLocaleString(undefined, {minimumFractionDigits: 2})}
                              </span>
                            </div>

                            <div className="flex flex-col">
                              <span className="text-[10px] font-black text-slate-600 uppercase tracking-widest mb-2 flex items-center gap-2">
                                {isUp ? <TrendingUp size={10} /> : <TrendingDown size={10} />} Change
                              </span>
                              <div className="flex items-center gap-2 font-mono text-xl font-black" style={{ color: col }}>
                                {isUp ? <ArrowUpRight size={20}/> : <ArrowDownRight size={20}/>}
                                {Math.abs(s.chg || 0).toFixed(2)}%
                              </div>
                            </div>

                            <div className="hidden md:flex flex-col">
                              <span className="text-[10px] font-black text-slate-600 uppercase tracking-widest mb-2 flex items-center gap-2">
                                <Activity size={10} /> Momentum
                              </span>
                              <div className="pt-1 h-10 flex items-center">
                                <MiniSparkline data={trendData} color={col} w={120} h={32} />
                              </div>
                            </div>

                            <div className="hidden md:flex flex-col items-end lg:pr-8">
                              <span className="text-[10px] font-black text-slate-600 uppercase tracking-widest mb-3">System Logic</span>
                              <span className="py-1.5 px-4 rounded-xl text-[9px] font-black border tracking-[0.2em] shadow-lg" 
                                style={{
                                  background: `${col}15`,
                                  color: col,
                                  borderColor: `${col}30`,
                                }}
                              >
                                {isUp ? 'CORE_ACCUMULATE' : 'LIQUIDITY_VOID'}
                              </span>
                            </div>
                          </div>

                          {/* Clay Action Button */}
                          <div className="lg:pr-4">
                            <button className="w-14 h-14 rounded-2xl bg-slate-800 border border-white/5 flex items-center justify-center shadow-[4px_4px_10px_rgba(0,0,0,0.4),-2px_-2px_10px_rgba(255,255,255,0.05),inset_1px_1px_1px_rgba(255,255,255,0.1)] active:shadow-inner active:translate-y-0.5 transition-all group-hover:bg-indigo-600 group-hover:border-indigo-400 group-hover:shadow-[0_0_30px_rgba(79,70,229,0.3)]">
                              <ArrowUpRight size={24} className="text-indigo-400 group-hover:text-white transition-colors" />
                            </button>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* EMPTY STATE */}
        {!loading && filtered.length === 0 && (
          <div className="flex flex-col items-center justify-center py-40 gap-6 bg-slate-900/20 rounded-[40px] border border-dashed border-white/5 animate-fade-in">
            <div className="p-8 bg-slate-900 rounded-full shadow-inner border border-white/5">
              <Info size={48} className="text-slate-800" />
            </div>
            <div className="text-center">
              <h3 className="text-lg font-black text-slate-500 uppercase tracking-[0.3em]">Query Logic Failure</h3>
              <p className="text-xs text-slate-700 font-mono mt-2 uppercase tracking-widest">No matching assets found in the current coordinate system.</p>
            </div>
            <button 
              onClick={() => {setSearchTerm(''); setActiveFilter('All Markets')}}
              className="mt-4 px-8 py-3 bg-indigo-500/10 hover:bg-indigo-500/20 border border-indigo-500/30 rounded-xl text-[10px] font-black tracking-[0.2em] text-indigo-400 transition-all uppercase"
            >
              Reset Terminal
            </button>
          </div>
        )}

      </div>
    </div>
  );
}
