import React, { useState, useEffect } from "react";
import { Flame, TrendingUp, TrendingDown, Activity, Loader2, ArrowUpRight, Zap } from "lucide-react";
import { Sparkline } from "./Shared";

import { API_BASE } from "../constants/config";

function TrendCard({ stock, rank, type, onSelect }) {
  const isGainer = type === "gainer";
  const isVolatile = type === "volatile";
  const color = isGainer ? "#22c55e" : isVolatile ? "#a855f7" : "#ef4444";
  const chg = stock.change_pct || 0;
  const Icon = chg >= 0 ? TrendingUp : TrendingDown;

  return (
    <div onClick={() => onSelect && onSelect(stock.ticker)}
      className="clay-card p-4 group hover:scale-[1.02] transition-all cursor-pointer relative overflow-hidden">
      {/* Rank badge */}
      <div className="absolute top-3 right-3 w-7 h-7 rounded-full flex items-center justify-center text-[10px] font-black font-mono"
        style={{ background: `${color}15`, color, border: `1px solid ${color}25` }}>
        #{rank}
      </div>

      <div className="space-y-3">
        {/* Ticker + Name */}
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl flex items-center justify-center text-sm font-black"
            style={{ background: `${color}15`, border: `1px solid ${color}30`, color }}>
            {stock.ticker?.[0] || "?"}
          </div>
          <div>
            <div className="font-mono font-bold text-white text-sm group-hover:text-indigo-400 transition-colors">{stock.ticker}</div>
            <div className="text-[9px] text-slate-500 truncate max-w-[120px]">{stock.name}</div>
          </div>
        </div>

        {/* Price + Change */}
        <div className="flex items-center justify-between">
          <span className="font-mono text-base font-bold text-white">
            ${stock.price?.toLocaleString(undefined, { minimumFractionDigits: 2 })}
          </span>
          <div className="flex items-center gap-1 font-mono text-sm font-bold" style={{ color: chg >= 0 ? "#22c55e" : "#ef4444" }}>
            <Icon size={14} />
            {chg >= 0 ? "+" : ""}{chg.toFixed(2)}%
          </div>
        </div>

        {/* Sparkline */}
        {stock.ohlcv && stock.ohlcv.length > 0 && (
          <div className="pt-1">
            <Sparkline data={stock.ohlcv} color={color} w={180} h={28} />
          </div>
        )}

        {/* Meta */}
        <div className="flex items-center justify-between pt-2 border-t border-white/5">
          <span className="text-[9px] text-slate-600 font-mono">{stock.sector}</span>
          <span className="text-[9px] text-slate-600 font-mono">Vol: {stock.volume}</span>
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
    <div className="flex-1 flex items-center justify-center">
      <div className="text-center space-y-3">
        <Loader2 size={32} className="text-orange-400 animate-spin mx-auto" />
        <p className="text-xs font-mono text-slate-500 tracking-widest">SCANNING HOT MARKETS...</p>
      </div>
    </div>
  );

  if (!data) return null;

  const TABS = [
    { id: "gainers",    label: "🟢 Top Gainers",    icon: TrendingUp,   color: "#22c55e", data: data.gainers },
    { id: "losers",     label: "🔴 Top Losers",     icon: TrendingDown, color: "#ef4444", data: data.losers },
    { id: "volatile",   label: "⚡ Most Volatile",   icon: Activity,     color: "#a855f7", data: data.most_volatile },
  ];

  const activeTabData = TABS.find(t => t.id === activeTab);

  return (
    <div className="flex-1 p-8 overflow-y-auto no-scrollbar animate-fade-in">
      <div className="max-w-6xl mx-auto space-y-8">
        {/* Header */}
        <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-6 border-b border-white/5 pb-6">
          <div className="space-y-2">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-orange-500/10 rounded-2xl border border-orange-500/30 shadow-lg">
                <Flame size={24} className="text-orange-400" />
              </div>
              <div>
                <h2 className="text-3xl font-black text-white tracking-tighter uppercase">Trending Stocks</h2>
                <p className="text-[10px] font-mono text-slate-500 tracking-[0.3em] uppercase mt-1">
                  TOP MOVERS • REAL-TIME MOMENTUM • {(data.gainers?.length || 0) + (data.losers?.length || 0)} ACTIVE
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-3">
          {TABS.map(tab => {
            const isActive = activeTab === tab.id;
            return (
              <button key={tab.id} onClick={() => setActiveTab(tab.id)}
                className="px-5 py-3 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all flex items-center gap-2"
                style={{
                  background: isActive ? `${tab.color}15` : "transparent",
                  border: `1px solid ${isActive ? `${tab.color}30` : "rgba(255,255,255,0.05)"}`,
                  color: isActive ? tab.color : "#64748b",
                  boxShadow: isActive ? `0 0 20px ${tab.color}10` : "none",
                }}>
                {tab.label}
                <span className="px-1.5 py-0.5 rounded-md text-[8px] font-mono" style={{ background: isActive ? `${tab.color}20` : "rgba(255,255,255,0.03)", color: isActive ? tab.color : "#475569" }}>
                  {tab.data?.length || 0}
                </span>
              </button>
            );
          })}
        </div>

        {/* Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
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
          <div className="text-center py-16">
            <Activity size={48} className="mx-auto mb-4 text-slate-800 animate-pulse" />
            <p className="text-sm font-mono text-slate-600 tracking-wider">AWAITING MARKET DATA SYNC</p>
          </div>
        )}
      </div>
    </div>
  );
}
