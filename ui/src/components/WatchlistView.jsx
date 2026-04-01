import React, { useState } from "react";
import { 
  ArrowUpRight, 
  ArrowDownRight, 
  Search, 
  Activity, 
  Zap, 
  Info, 
  TrendingUp, 
  TrendingDown, 
  Layers, 
  Loader2 
} from "lucide-react";

const FILTERS = ['All Markets', 'US Tech', 'Asia-Pac', 'EU', 'Crypto', 'India'];

const SECTOR_FILTER_MAP = {
  'US Tech': ['Technology', 'Communication Services', 'Consumer Cyclical', 'Semiconductors'],
  'Asia-Pac': ['TYO', 'HKG', 'SHH', 'ASX', 'SGX'],
  'EU': ['LSE', 'FRA', 'PAR', 'SWX'],
  'Crypto': ['Crypto', 'CCC'],
  'India': ['NSI', 'BSE'],
};

const MiniSparkline = ({ data = [], color, w = 100, h = 30 }) => {
  if (!data || data.length < 2) return <div className="h-[30px] w-[100px] bg-white/5 rounded-md animate-pulse" />;
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
      <path d={pathData} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
};

export default function WatchlistView({ onSelect, stocks = [], marketIndices = [], loading = false }) {
  const [activeFilter, setActiveFilter] = useState('All Markets');
  const [searchTerm, setSearchTerm] = useState('');

  const filtered = stocks.filter(s => {
    const matchesSearch = (s.id || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
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
    <div className="flex-1 overflow-y-auto no-scrollbar animate-fade-in page-padding">
      <div className="content-max-w space-y-6 md:space-y-10">
        
        {/* SHARP Header Alignment */}
        <header className="flex flex-col lg:flex-row lg:items-end justify-between gap-6 md:gap-8 border-b border-white/[0.08] pb-6 md:pb-10">
          <div className="flex items-center gap-4 md:gap-6">
            <div className="w-11 h-11 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center shadow-sm">
              <Layers size={22} className="text-indigo-400" />
            </div>
            <div className="flex flex-col gap-0.5">
              <h1 className="text-xl md:text-2xl font-bold text-white tracking-tight uppercase leading-none">
                Market Command
              </h1>
              <p className="text-[10px] font-mono text-slate-500 tracking-[0.4em] uppercase flex items-center gap-2 mt-1">
                <Activity size={10} className="text-indigo-500" />
                {loading ? 'SYNCING_CLUSTER...' : `CLUSTER_NODES // ${stocks.length} READY`}
              </p>
            </div>
          </div>

          {/* Indices Scrollable Strip */}
          <div className="flex gap-3 overflow-x-auto no-scrollbar pb-2 lg:pb-0">
            {(marketIndices.length > 0 ? marketIndices : [
              { name: 'S&P 500', value: 5254.35, change: 0.12 },
              { name: 'NASDAQ', value: 16384.42, change: -0.05 },
              { name: 'DOW J', value: 39475.90, change: 0.08 }
            ]).map((idx) => (
              <div key={idx.name} className="px-4 py-2.5 min-w-[130px] md:min-w-[150px] glass-card flex flex-col gap-1 hover:bg-white/[0.04]">
                <span className="text-[8px] uppercase tracking-[0.2em] text-slate-500 font-bold font-mono">{idx.name}</span>
                <div className="flex items-center justify-between">
                  <span className="text-[13px] font-bold text-white font-mono">{(idx.value || 0).toLocaleString()}</span>
                  <span className={`text-[9px] font-bold font-mono ${idx.change >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                    {idx.change >= 0 ? '+' : ''}{idx.change}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        </header>

        {/* Toolbar - Precision & Mobile Friendly */}
        <section className="flex flex-col md:flex-row items-center justify-between gap-4 md:gap-6">
          <div className="skeuo-toggle w-full md:w-auto overflow-x-auto no-scrollbar">
            {FILTERS.map(f => (
              <button key={f} onClick={() => setActiveFilter(f)}
                className={`skeuo-toggle-item whitespace-nowrap px-4 ${activeFilter === f ? 'active' : ''}`}>
                {f}
              </button>
            ))}
          </div>

          <div className="relative w-full md:w-[300px]">
            <Search size={14} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-600" />
            <input
              value={searchTerm} 
              onChange={e => setSearchTerm(e.target.value)}
              placeholder="SCAN IDENTIFIER..."
              className="bg-black/20 w-full h-10 pl-11 pr-4 text-[10px] font-mono tracking-widest rounded-md outline-none border border-white/[0.08] focus:border-indigo-500/40 transition-all text-white placeholder:text-slate-700 font-bold"
            />
          </div>
        </section>

        {/* Asset List - High Density Matrix */}
        <div className="space-y-8 md:space-y-12">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-20 gap-4">
              <Loader2 size={24} className="text-indigo-500 animate-spin" />
              <span className="text-[9px] text-slate-600 font-mono tracking-widest uppercase animate-pulse">Syncing Liquidity Matrix...</span>
            </div>
          ) : (
            sectors.map(sector => {
              const sectorStocks = filtered.filter(s => (s.sector || 'Others') === sector);
              if (sectorStocks.length === 0) return null;
              
              return (
                <div key={sector} className="space-y-4">
                  <div className="flex items-center gap-4 px-1">
                    <div className="h-1 w-1 rounded-sm bg-indigo-500 shadow-[0_0_8px_#6366f1]" />
                    <span className="text-[10px] font-black text-indigo-400/80 tracking-[0.2em] uppercase">{sector}</span>
                    <div className="flex-1 h-[1px] bg-white/[0.04]" />
                    <span className="text-[9px] font-mono text-slate-700 uppercase tracking-widest">{sectorStocks.length} NODES</span>
                  </div>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-1 gap-3 md:gap-4">
                    {sectorStocks.map((s) => {
                      const isUp = (s.chg || 0) >= 0;
                      const col = isUp ? 'var(--accent-positive)' : 'var(--accent-negative)';
                      const trendData = s.ohlcv || [];
                      return (
                        <div key={s.id} onClick={() => onSelect(s)}
                          className="group min-h-[64px] glass-card flex flex-col xl:flex-row items-center p-4 xl:px-6 xl:py-2 gap-4 xl:gap-8 interactive border-white/[0.05]">
                          
                          {/* Symbol Column */}
                          <div className="flex items-center gap-4 w-full xl:w-[220px] shrink-0">
                            <div className="w-9 h-9 rounded-md flex items-center justify-center text-sm font-bold border shrink-0 transition-transform group-hover:scale-105"
                              style={{ background: `${col}08`, borderColor: `${col}15`, color: col }}>
                              {(s.id || '?')[0]}
                            </div>
                            <div className="flex flex-col truncate">
                              <span className="font-bold text-[15px] xl:text-lg text-white group-hover:text-indigo-400 transition-colors leading-tight">
                                {s.id}
                              </span>
                              <span className="text-[8px] text-slate-600 font-bold tracking-widest uppercase truncate">
                                {s.name}
                              </span>
                            </div>
                            <div className="xl:hidden flex-1"/>
                            <div className="xl:hidden status-badge" style={{ color: col, borderColor: `${col}20` }}>
                              {isUp ? '+' : ''}{s.chg?.toFixed(1)}%
                            </div>
                          </div>

                          {/* Detail Matrix - Desktop Grid / Mobile Stack */}
                          <div className="flex flex-1 w-full items-center justify-between gap-4 md:gap-8">
                            <div className="flex flex-col w-20 md:w-32">
                              <span className="text-[8px] font-bold text-slate-600 uppercase tracking-widest mb-0.5">Price</span>
                              <span className="font-mono text-[12px] md:text-sm font-bold text-white">
                                {s.id.includes('-USD') ? '' : '$'}{(s.px || 0).toLocaleString(undefined, {minimumFractionDigits: 1})}
                              </span>
                            </div>

                            <div className="hidden md:flex flex-col w-32">
                              <span className="text-[8px] font-bold text-slate-600 uppercase tracking-widest mb-0.5">Change</span>
                              <div className="flex items-center gap-1.5 font-mono text-sm font-bold" style={{ color: col }}>
                                {isUp ? <TrendingUp size={12}/> : <TrendingDown size={12}/>}
                                {Math.abs(s.chg || 0).toFixed(2)}%
                              </div>
                            </div>

                            <div className="hidden lg:flex flex-1 justify-center max-w-[100px]">
                              <MiniSparkline data={trendData} color={isUp ? '#6366f1' : col} w={80} h={20} />
                            </div>

                            <div className="hidden md:flex flex-col items-end w-24 shrink-0">
                               <div className="status-badge" style={{ color: col, borderColor: `${col}15`, background: `${col}05` }}>
                                 {isUp ? 'ACCUMULATE' : 'LIQUIDITY'}
                               </div>
                            </div>
                          </div>

                          {/* Quick Action */}
                          <div className="hidden xl:flex w-9 h-9 items-center justify-center rounded-md border border-white/[0.04] bg-white/[0.02] text-slate-700 group-hover:text-white group-hover:bg-indigo-600 group-hover:border-indigo-500 transition-all">
                            <ArrowUpRight size={16} />
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

        {/* Empty State */}
        {!loading && filtered.length === 0 && (
          <div className="flex flex-col items-center justify-center py-20 gap-4 border border-dashed border-white/[0.08] rounded-lg animate-fade-in bg-black/10">
            <Info size={28} className="text-slate-800" />
            <div className="text-center">
              <h3 className="text-[10px] font-bold text-slate-600 uppercase tracking-widest">No Node Consensus</h3>
              <p className="text-[9px] text-slate-800 font-mono mt-1 uppercase">Refine query parameters for terminal sync.</p>
            </div>
            <button 
              onClick={() => {setSearchTerm(''); setActiveFilter('All Markets')}}
              className="mt-2 skeuo-button px-5 py-1.5"
            >
              Reset Terminal
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
