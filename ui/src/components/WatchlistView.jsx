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

  return (
    <div className="flex-1 p-8 overflow-y-auto no-scrollbar animate-fade-in">
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-6">
          <div className="space-y-2">
            <div className="flex items-center gap-4">
              <div className="p-2.5 bg-indigo-500/10 rounded-2xl border border-indigo-500/20">
                <List size={20} className="text-indigo-400" />
              </div>
              <div>
                <h2 className="text-2xl font-black text-white tracking-tight uppercase">Global Asset Tracker</h2>
                <p className="text-[10px] font-mono text-slate-500 tracking-widest uppercase mt-1">
                  MULTI_EXCHANGE // {stocks.length} INSTRUMENTS TRACKED // {loading ? 'FETCHING...' : 'LIVE'}
                </p>
              </div>
            </div>
          </div>

          {/* Index Summary Metrics */}
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4 p-1 bg-black/40 rounded-[18px] border border-white/5">
            {(marketIndices.length > 0 ? marketIndices : [
              { name: 'Loading...', value: 0, change: 0 }
            ]).map((idx) => (
              <div key={idx.name} className="px-5 py-3 flex flex-col items-center">
                <span className="text-[8px] uppercase tracking-[0.2em] mb-1.5 text-slate-500 font-black">{idx.name}</span>
                <span className="font-mono text-sm font-black" style={{ color: (idx.change || 0) >= 0 ? T.buy : T.sell }}>
                  {(idx.value || 0).toLocaleString()} ({(idx.change || 0) >= 0 ? '+' : ''}{idx.change || 0}%)
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Toolbar */}
        <div className="flex items-center justify-between gap-4">
          <div className="flex gap-2 flex-wrap">
            {FILTERS.map(f => (
              <button key={f} onClick={() => setActiveFilter(f)}
                className={`px-4 py-2 rounded-xl text-[10px] font-black uppercase tracking-wider transition-all ${
                  activeFilter === f
                    ? 'bg-indigo-600 text-white shadow-xl shadow-indigo-900/30'
                    : 'text-slate-500 hover:text-white hover:bg-white/5 border border-white/5'
                }`}>
                {f}
              </button>
            ))}
          </div>
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
            <input
              value={searchTerm} onChange={e => setSearchTerm(e.target.value)}
              placeholder="Search ticker..."
              className="clay-input pl-9 pr-4 py-2.5 w-52 text-xs"
            />
          </div>
        </div>

        {/* Loading State */}
        {loading && (
          <div className="flex items-center justify-center py-12 gap-3">
            <Loader2 size={20} className="text-indigo-400 animate-spin" />
            <span className="text-sm text-slate-400 font-mono animate-pulse">Fetching live market data from yfinance...</span>
          </div>
        )}

        {/* Data Table */}
        {!loading && sorted.length > 0 && (
          <div className="clay-card overflow-hidden">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-white/5 bg-black/30">
                  {[
                    { key: 'asset', label: 'ASSET_ID', sortable: false },
                    { key: 'px', label: 'PRICE_USD', sortable: true },
                    { key: 'chg', label: 'DELTA_24H', sortable: true },
                    { key: 'vol', label: 'VOLUME', sortable: true },
                    { key: 'mcap', label: 'MKT_CAP', sortable: false },
                    { key: 'trend', label: 'MICRO_TREND', sortable: false },
                    { key: 'signal', label: 'AI_SIGNAL', sortable: false },
                    { key: 'risk', label: 'RISK_TIER', sortable: false },
                    { key: 'action', label: '', sortable: false },
                  ].map(h => (
                    <th key={h.key}
                      className={`px-5 py-4 text-[8px] font-black uppercase tracking-[0.2em] text-slate-500 ${h.sortable ? 'cursor-pointer hover:text-white transition-colors' : ''}`}
                      onClick={() => h.sortable && handleSort(h.key)}>
                      <div className="flex items-center gap-1.5">
                        {h.label}
                        {sortCol === h.key && <span className="text-indigo-400">{sortDir === 'asc' ? '↑' : '↓'}</span>}
                      </div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {sorted.map((s) => {
                  const isUp = (s.chg || 0) >= 0;
                  const col = isUp ? T.buy : T.sell;
                  const signal = isUp ? ((s.chg || 0) > 2 ? 'STRONG_BUY' : 'BUY') : ((s.chg || 0) < -1 ? 'SELL' : 'HOLD');
                  const signalColor = signal === 'STRONG_BUY' ? T.buy : signal === 'BUY' ? T.buy : signal === 'SELL' ? T.sell : T.warn;
                  const riskData = s.risk || { var: 'N/A', beta: 1.0, vol: 'N/A' };
                  return (
                    <tr key={s.id} className="group border-b border-white/[0.03] hover:bg-white/[0.02] cursor-pointer transition-all"
                      onClick={() => onSelect(s)}>
                      <td className="px-5 py-4">
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 rounded-[14px] flex items-center justify-center text-xs font-black transition-all"
                            style={{
                              background: `linear-gradient(135deg, ${col}20, ${col}08)`,
                              border: `1px solid ${col}30`,
                              color: col,
                            }}>
                            {(s.id || '?')[0]}
                          </div>
                          <div>
                            <div className="font-mono font-black text-sm text-white group-hover:text-indigo-300 transition-colors">{s.id}</div>
                            <div className="text-[10px] text-slate-500 font-medium truncate max-w-[140px]">{s.name}</div>
                          </div>
                        </div>
                      </td>
                      <td className="px-5 py-4">
                        <span className="font-mono text-sm font-bold text-white">
                          {s.id.includes('-USD') ? '' : '$'}{(s.px || 0).toLocaleString(undefined, {minimumFractionDigits: 2})}
                        </span>
                      </td>
                      <td className="px-5 py-4">
                        <div className="flex items-center gap-1.5 font-mono text-sm font-black" style={{ color: col }}>
                          {isUp ? <ArrowUpRight size={14}/> : <ArrowDownRight size={14}/>}
                          {Math.abs(s.chg || 0)}%
                        </div>
                      </td>
                      <td className="px-5 py-4 font-mono text-xs text-slate-400">{s.vol || 'N/A'}</td>
                      <td className="px-5 py-4 font-mono text-xs text-slate-400">{s.mcap || 'N/A'}</td>
                      <td className="px-5 py-4">
                        {s.ohlcv && s.ohlcv.length > 0 ? (
                          <Sparkline data={s.ohlcv} color={col} w={100} h={36} />
                        ) : (
                          <span className="text-[9px] text-slate-600 font-mono">NO DATA</span>
                        )}
                      </td>
                      <td className="px-5 py-4">
                        <span className="py-1 px-2.5 rounded-lg text-[8px] font-black border" style={{
                          background: `${signalColor}15`,
                          color: signalColor,
                          borderColor: `${signalColor}30`,
                        }}>
                          {signal}
                        </span>
                      </td>
                      <td className="px-5 py-4">
                        <span className="text-[9px] font-mono font-bold" style={{ 
                          color: riskData.vol === 'High' ? T.sell : riskData.vol === 'Med' ? T.warn : T.buy 
                        }}>
                          {riskData.vol || 'N/A'}
                        </span>
                      </td>
                      <td className="px-5 py-4">
                        <button className="opacity-0 group-hover:opacity-100 p-2 rounded-xl transition-all bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 hover:bg-indigo-500/20">
                          <ArrowUpRight size={14} />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {!loading && sorted.length === 0 && (
          <div className="flex flex-col items-center justify-center py-16 gap-3">
            <Activity size={28} className="text-slate-700" />
            <span className="text-sm text-slate-500 font-mono">No instruments match current filters</span>
          </div>
        )}
      </div>
    </div>
  );
}
