import React, { useState, useEffect } from "react";
import { Flame, TrendingUp, TrendingDown, Activity, Loader2, ArrowUpRight, Zap } from "lucide-react";
import { Sparkline } from "./Shared";
import { API_BASE } from "../api_config";

function TrendCard({ stock, rank, type, onSelect }) {
  const isGainer = type === "gainer";
  const isVolatile = type === "volatile";
  const color = isGainer ? "var(--accent-positive)" : isVolatile ? "var(--accent-indigo)" : "var(--accent-negative)";
  const chg = stock.change_pct || 0;
  const Icon = chg >= 0 ? TrendingUp : TrendingDown;

  return (
    <div onClick={() => onSelect && onSelect(stock.ticker)}
      className="glass-card p-5 group hover:bg-white/[0.02] transition-all duration-120 cursor-pointer relative overflow-hidden border border-white/[0.06] hover:border-white/[0.15]">
      {/* Rank badge */}
      <div className="absolute top-4 right-4 w-6 h-6 rounded-md flex items-center justify-center text-[9px] font-bold font-mono border"
        style={{ background: `${color}08`, color, borderColor: `${color}20` }}>
        #{rank}
      </div>

      <div className="space-y-4">
        {/* Ticker + Name */}
        <div className="flex items-center gap-4">
          <div className="w-10 h-10 rounded-lg flex items-center justify-center text-sm font-bold border"
            style={{ background: `${color}08`, borderColor: `${color}20`, color }}>
            {stock.ticker?.[0] || "?"}
          </div>
          <div className="flex flex-col gap-0.5">
            <div className="font-bold text-white text-[15px] group-hover:text-indigo-400 transition-colors uppercase tracking-tight">{stock.ticker}</div>
            <div className="text-[9px] text-slate-500 font-bold uppercase tracking-wider truncate max-w-[120px]">{stock.name}</div>
          </div>
        </div>

        {/* Price + Change */}
        <div className="flex items-center justify-between">
          <span className="font-mono text-[16px] font-bold text-white">
            ${stock.price?.toLocaleString(undefined, { minimumFractionDigits: 2 })}
          </span>
          <div className="flex items-center gap-1.5 font-mono text-[12px] font-bold" style={{ color }}>
            {chg >= 0 ? "+" : ""}{chg.toFixed(2)}%
          </div>
        </div>

        {/* Sparkline */}
        {stock.ohlcv && stock.ohlcv.length > 0 && (
          <div className="pt-1 h-8 flex items-center">
            <Sparkline data={stock.ohlcv} color={color} w={200} h={24} />
          </div>
        )}

        {/* Meta Segmented Control Look */}
        <div className="flex items-center justify-between pt-3 border-t border-white/[0.06]">
          <span className="text-[9px] text-slate-600 font-bold uppercase tracking-widest">{stock.sector}</span>
          <span className="text-[9px] text-slate-700 font-mono font-bold uppercase">VOL: {stock.volume}</span>
        </div>
      </div>
    </div>
  );
}

export default function TrendingStocksView({ onSelect }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("gainers");

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/market/trending`);
        const d = await res.json();
        setData(d);
      } catch (err) {
        console.error("Trending data fetch failed:", err);
      }
      setLoading(false);
    };
    fetchData();
    const interval = setInterval(fetchData, 60000);
    return () => clearInterval(interval);
  }, []);

  if (loading) return (
    <div className="flex-1 flex items-center justify-center institutional-bg">
      <div className="text-center space-y-4">
        <Loader2 size={24} className="text-indigo-500 animate-spin mx-auto" />
        <p className="text-[10px] font-mono text-slate-500 tracking-[0.3em] uppercase animate-pulse">Scanning Flux Waves...</p>
      </div>
    </div>
  );

  if (!data) return null;

  const TABS = [
    { id: "gainers",    label: "Top Gainers",    icon: TrendingUp,   color: "var(--accent-positive)", data: data.gainers },
    { id: "losers",     label: "Top Losers",     icon: TrendingDown, color: "var(--accent-negative)", data: data.losers },
    { id: "volatile",   label: "Volatile",   icon: Activity,     color: "var(--accent-indigo)", data: data.most_volatile },
  ];

  const activeTabData = TABS.find(t => t.id === activeTab);

  return (
    <div className="flex-1 p-8 overflow-y-auto no-scrollbar animate-fade-in institutional-bg">
      <div className="max-w-6xl mx-auto space-y-10">
        {/* Institutional Header */}
        <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-6 border-b border-white/[0.08] pb-8">
          <div className="flex items-center gap-5">
            <div className="w-12 h-12 rounded-xl bg-orange-500/10 border border-orange-500/20 flex items-center justify-center shadow-lg">
              <Flame size={24} className="text-orange-400" />
            </div>
            <div className="flex flex-col gap-1">
              <h1 className="text-[24px] font-bold text-white tracking-tight uppercase leading-none">Market Momentum</h1>
              <p className="text-[10px] font-mono text-slate-500 tracking-[0.4em] uppercase">
                ACTIVE_MOVERS // { (data.gainers?.length || 0) + (data.losers?.length || 0) } NODES_TRACKED
              </p>
            </div>
          </div>
        </div>

        {/* Precision Tabs */}
        <div className="skeuo-toggle inline-flex min-w-fit">
          {TABS.map(tab => {
            const isActive = activeTab === tab.id;
            return (
              <button key={tab.id} onClick={() => setActiveTab(tab.id)}
                className={`skeuo-toggle-item !px-6 flex items-center gap-3 ${isActive ? 'active' : ''}`}
                style={isActive ? { color: tab.color } : {}}>
                <tab.icon size={12} style={{ color: isActive ? tab.color : 'inherit' }} />
                <span>{tab.label.toUpperCase()}</span>
                <span className="text-[8px] font-mono opacity-60">
                  {tab.data?.length || 0}
                </span>
              </button>
            );
          })}
        </div>

        {/* Output Matrix */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {(activeTabData?.data || []).map((stock, i) => (
            <TrendCard
              key={stock.ticker}
              stock={stock}
              rank={i + 1}
              type={activeTab === "gainers" ? "gainer" : activeTab === "losers" ? "loser" : "volatile"}
              onSelect={onSelect}
            />
          ))}
        </div>

        {(activeTabData?.data?.length === 0) && (
          <div className="flex flex-col items-center justify-center py-20 gap-4 opacity-40">
            <Activity size={32} className="text-slate-800 animate-pulse" />
            <p className="text-[10px] font-mono font-bold text-slate-700 uppercase tracking-widest">Awaiting Pulse Detection...</p>
          </div>
        )}
      </div>
    </div>
  );
}
