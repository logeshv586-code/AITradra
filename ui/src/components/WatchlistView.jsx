import React, { useState } from "react";
import { List, ArrowUpRight, ArrowDownRight, Search, Activity, Zap, Loader2 } from "lucide-react";
import { T } from "../theme";
import { Sparkline } from "./Shared";

const FILTERS = ['All Markets', 'US Tech', 'Asia-Pac', 'EU', 'Crypto', 'India'];

const SECTOR_FILTER_MAP = {
  'US Tech': ['Technology', 'Communication Services', 'Consumer Cyclical', 'Semiconductors'],
  'Asia-Pac': ['TYO', 'HKG', 'SHH', 'ASX', 'SGX'],
  'EU': ['LSE', 'FRA', 'PAR', 'SWX'],
  'Crypto': ['Crypto', 'CCC'],
  'India': ['NSI', 'BSE'],
};

export default function WatchlistView({ onSelect, stocks = [], marketIndices = [], loading = false }) {
  const [activeFilter, setActiveFilter] = useState('All Markets');
  const [searchTerm, setSearchTerm] = useState('');
  const [sortCol, setSortCol] = useState(null);
  const [sortDir, setSortDir] = useState('desc');

  const filtered = stocks.filter(s => {
    const matchesSearch = s.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (s.name || '').toLowerCase().includes(searchTerm.toLowerCase());
    
    if (activeFilter === 'All Markets') return matchesSearch;
    
    const filterKeys = SECTOR_FILTER_MAP[activeFilter] || [];
    const matchesFilter = filterKeys.some(f => 
      (s.sector || '').toLowerCase().includes(f.toLowerCase()) ||
      (s.ex || '').includes(f) ||
      (s.id || '').includes('-USD') && activeFilter === 'Crypto'
    );
    return matchesSearch && matchesFilter;
  });

  const sorted = sortCol ? [...filtered].sort((a, b) => {
    const va = sortCol === 'px' ? (a.px || 0) : sortCol === 'chg' ? (a.chg || 0) : sortCol === 'vol' ? parseInt(a.vol) || 0 : 0;
    const vb = sortCol === 'px' ? (b.px || 0) : sortCol === 'chg' ? (b.chg || 0) : sortCol === 'vol' ? parseInt(b.vol) || 0 : 0;
    return sortDir === 'asc' ? va - vb : vb - va;
  }) : filtered;

  const handleSort = (col) => {
    if (sortCol === col) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    else { setSortCol(col); setSortDir('desc'); }
  };

  const bullish = stocks.filter(s => (s.chg || 0) >= 0).length;
  const bearish = stocks.length - bullish;
  const avgChange = stocks.length > 0 ? (stocks.reduce((s, x) => s + (x.chg || 0), 0) / stocks.length).toFixed(2) : '0.00';

  const sectors = [...new Set(sorted.map(s => s.sector || 'Others'))];

  return (
    <div className="flex-1 p-8 overflow-y-auto no-scrollbar animate-fade-in">
      <div className="max-w-7xl mx-auto space-y-10">
        {/* Header */}
        <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-8 border-b border-white/5 pb-8">
          <div className="space-y-3">
            <div className="flex items-center gap-5">
              <div className="p-3.5 bg-indigo-500/10 rounded-2xl border border-indigo-500/30 clay-organic shadow-lg">
                <List size={24} className="text-indigo-400" />
              </div>
              <div>
                <h2 className="text-4xl font-black text-white tracking-tighter uppercase text-shadow-glow">Asset Command</h2>
                <p className="text-[11px] font-mono text-slate-500 tracking-[0.3em] uppercase mt-2 flex items-center gap-3">
                  <Activity size={12} className="text-indigo-500" />
                  {stocks.length} INSTRUMENTS // {loading ? 'FETCHING_STREAM' : 'NETWORK_LIVE'}
                </p>
              </div>
            </div>
          </div>

          {/* Index Summary Metrics */}
          <div className="flex gap-4 p-2 bg-black/40 rounded-[24px] border border-white/10 shadow-2xl overflow-x-auto no-scrollbar">
            {(marketIndices.length > 0 ? marketIndices : [
              { name: 'S&P 500', value: 5241, change: 1.2 },
              { name: 'NASDAQ', value: 16428, change: 0.8 },
              { name: 'DOW J', value: 39475, change: -0.2 }
            ]).map((idx) => (
              <div key={idx.name} className="px-6 py-4 flex flex-col items-start min-w-[140px] clay-inset bg-white/5">
                <span className="text-[9px] uppercase tracking-[0.2em] mb-2 text-slate-500 font-black">{idx.name}</span>
                <span className="font-mono text-base font-black flex items-center gap-2" style={{ color: (idx.change || 0) >= 0 ? T.buy : T.sell }}>
                  {(idx.value || 0).toLocaleString()}
                  <span className="text-[10px] opacity-80">{(idx.change || 0) >= 0 ? '↑' : '↓'} {Math.abs(idx.change || 0)}%</span>
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Toolbar */}
        <div className="flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="flex gap-3 flex-wrap">
            {FILTERS.map(f => (
              <button key={f} onClick={() => setActiveFilter(f)}
                className={`px-5 py-2.5 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all ${
                  activeFilter === f
                    ? 'bg-indigo-600 text-white shadow-2xl shadow-indigo-900/50 scale-105'
                    : 'text-slate-500 hover:text-white hover:bg-white/10 border border-white/5'
                }`}>
                {f}
              </button>
            ))}
          </div>
          <div className="relative group min-w-[300px]">
            <Search size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500 group-focus-within:text-indigo-400 transition-colors" />
            <input
              value={searchTerm} onChange={e => setSearchTerm(e.target.value)}
              placeholder="SEARCH ASSET CODENAME..."
              className="clay-input pl-11 pr-5 py-3.5 w-full text-xs font-mono tracking-wider"
            />
          </div>
        </div>

        {/* Loading State */}
        {loading && (
          <div className="flex flex-col items-center justify-center py-24 gap-6">
            <div className="relative">
              <div className="w-16 h-16 rounded-full border-4 border-indigo-500/20 border-t-indigo-500 animate-spin" />
              <Zap size={24} className="absolute inset-0 m-auto text-indigo-400 animate-pulse" />
            </div>
            <span className="text-sm text-slate-400 font-mono tracking-widest animate-pulse">SYNCHRONIZING GLOBAL ORDER BOOKS...</span>
          </div>
        )}

        {/* Data List (Grouped by Sector) */}
        {!loading && sectors.map(sector => {
          const sectorStocks = sorted.filter(s => (s.sector || 'Others') === sector);
          if (sectorStocks.length === 0) return null;
          
          return (
            <div key={sector} className="space-y-4">
              <div className="flex items-center gap-4 px-2">
                <span className="text-[11px] font-black text-indigo-400 tracking-[0.4em] uppercase">{sector}</span>
                <div className="flex-1 h-px bg-gradient-to-r from-indigo-500/20 to-transparent" />
                <span className="text-[9px] font-mono text-slate-600 uppercase tracking-widest">{sectorStocks.length} ASSETS</span>
              </div>
              
              <div className="grid gap-3">
                {sectorStocks.map((s) => {
                  const isUp = (s.chg || 0) >= 0;
                  const col = isUp ? T.buy : T.sell;
                  const signal = isUp ? ((s.chg || 0) > 2 ? 'CORE_ACCUMULATE' : 'BULLISH') : ((s.chg || 0) < -1 ? 'DISTRIBUTE' : 'NEUTRAL');
                  const signalColor = isUp ? T.buy : ((s.chg || 0) < -1 ? T.sell : T.warn);
                  
                  return (
                    <div key={s.id} onClick={() => onSelect(s)}
                      className="group clay-card interactive p-2 pl-4 flex items-center justify-between gap-6 hover:scale-[1.01] transition-transform">
                      {/* Asset Identity */}
                      <div className="flex items-center gap-6 min-w-[200px]">
                        <div className="w-14 h-14 rounded-2xl flex items-center justify-center text-lg font-black transition-all clay-organic shadow-inner"
                          style={{
                            background: `linear-gradient(135deg, ${col}30, ${col}10)`,
                            border: `1px solid ${col}40`,
                            color: col,
                          }}>
                          {(s.id || '?')[0]}
                        </div>
                        <div>
                          <div className="font-mono font-black text-lg text-white group-hover:text-indigo-400 transition-colors tracking-tight">{s.id}</div>
                          <div className="text-[10px] text-slate-500 font-bold uppercase tracking-widest truncate max-w-[120px]">{s.name}</div>
                        </div>
                      </div>

                      {/* Market Value */}
                      <div className="flex-1 grid grid-cols-4 items-center gap-8">
                        <div className="flex flex-col">
                          <span className="text-[9px] font-black text-slate-600 uppercase tracking-widest mb-1">PRICE_USD</span>
                          <span className="font-mono text-base font-black text-white">
                            {s.id.includes('-USD') ? '' : '$'}{(s.px || 0).toLocaleString(undefined, {minimumFractionDigits: 2})}
                          </span>
                        </div>

                        <div className="flex flex-col">
                          <span className="text-[9px] font-black text-slate-600 uppercase tracking-widest mb-1">DELTA_24H</span>
                          <div className="flex items-center gap-2 font-mono text-base font-black" style={{ color: col }}>
                            {isUp ? <ArrowUpRight size={18}/> : <ArrowDownRight size={18}/>}
                            {Math.abs(s.chg || 0).toFixed(2)}%
                          </div>
                        </div>

                        <div className="flex flex-col">
                          <span className="text-[9px] font-black text-slate-600 uppercase tracking-widest mb-1">MICRO_TREND</span>
                          {s.ohlcv && s.ohlcv.length > 0 ? (
                            <div className="pt-1">
                              <Sparkline data={s.ohlcv} color={col} w={120} h={32} />
                            </div>
                          ) : (
                            <span className="text-[9px] text-slate-700 font-mono">NO_FEED</span>
                          )}
                        </div>

                        <div className="flex flex-col items-end pr-4">
                          <span className="text-[9px] font-black text-slate-600 uppercase tracking-widest mb-2">SIGNAL_PRECISION</span>
                          <span className="py-1 px-3 rounded-xl text-[9px] font-black border tracking-[0.1em]" style={{
                            background: `${signalColor}20`,
                            color: signalColor,
                            borderColor: `${signalColor}40`,
                            boxShadow: `0 0 12px ${signalColor}20`
                          }}>
                            {signal}
                          </span>
                        </div>
                      </div>

                      {/* Action */}
                      <div className="pr-4">
                        <div className="p-3 bg-white/5 rounded-2xl border border-white/5 text-slate-500 group-hover:bg-indigo-500/10 group-hover:border-indigo-500/30 group-hover:text-indigo-400 transition-all">
                          <ArrowUpRight size={20} />
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}

        {!loading && sorted.length === 0 && (
          <div className="flex flex-col items-center justify-center py-24 gap-4 opacity-50">
            <Activity size={48} className="text-slate-800 animate-pulse" />
            <span className="text-base text-slate-500 font-mono tracking-widest uppercase">Null set return // refine search filters</span>
          </div>
        )}
      </div>
    </div>
  );
}
