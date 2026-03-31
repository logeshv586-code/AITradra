import React, { useState, useEffect } from "react";
import { 
  Wallet, 
  TrendingUp, 
  TrendingDown, 
  ArrowUpRight, 
  ArrowDownRight, 
  PlayCircle,
  RefreshCw,
  Plus,
  Shield
} from "lucide-react";
import { T } from "../theme";

import { API_BASE } from "../constants/config";

const StatCard = ({ title, value, subValue, icon: Icon, color }) => (
  <div className="clay-card p-4 flex flex-col gap-2 min-w-[200px] flex-1">
    <div className="flex items-center justify-between">
      <span className="text-[10px] font-bold tracking-widest text-slate-400 uppercase">{title}</span>
      <div className="w-8 h-8 rounded-xl flex items-center justify-center bg-white/5 border border-white/10">
        <Icon size={14} style={{ color }} />
      </div>
    </div>
    <div className="text-xl font-mono font-bold text-white tracking-tight">{value}</div>
    {subValue && (
      <div className="text-[10px] font-mono font-bold" style={{ color }}>
        {subValue}
      </div>
    )}
  </div>
);

export default function VirtualPortfolioView({ onSelect }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [initialBalance, setInitialBalance] = useState("2000");
  const [isRefreshing, setIsRefreshing] = useState(false);

  const fetchStatus = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/simulation/status`);
      const result = await res.json();
      setData(result);
      setLoading(false);
    } catch (err) {
      console.error("Failed to fetch simulation status:", err);
      setLoading(false);
    }
  };

  const initializeSimulation = async () => {
    try {
      setLoading(true);
      const res = await fetch(`${API_BASE}/api/simulation/init`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ initial_balance: parseFloat(initialBalance) }),
      });
      const result = await res.json();
      setData(result);
      setLoading(false);
    } catch (err) {
      console.error("Failed to init simulation:", err);
      setLoading(false);
    }
  };

  const handleUpdate = async () => {
    setIsRefreshing(true);
    try {
      const res = await fetch(`${API_BASE}/api/simulation/update`);
      const result = await res.json();
      setData(result);
    } catch (err) {
      console.error("Failed to update simulation portfolio:", err);
    } finally {
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(handleUpdate, 10000); // Poll every 10s
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center font-mono text-xs text-indigo-400 animate-pulse">
        CONNECTING TO SIMULATION ENGINE...
      </div>
    );
  }

  if (!data?.initialized) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8 animate-fade-in">
        <div className="clay-card p-10 max-w-md w-full flex flex-col items-center gap-6 text-center">
          <div className="w-16 h-16 rounded-3xl bg-indigo-500/10 border border-indigo-400/20 flex items-center justify-center mb-2">
            <Wallet size={32} className="text-indigo-400" />
          </div>
          <h2 className="text-2xl font-bold tracking-tight text-white font-mono uppercase">Initialize Virtual Portfolio</h2>
          <p className="text-sm text-slate-400 leading-relaxed">
            Test OMNI-AXIOM's mythic-tier signals with zero risk. Set your starting dummy balance to begin the simulation.
          </p>
          
          <div className="w-full flex flex-col gap-2 items-start mt-4">
            <label className="text-[10px] font-bold tracking-widest text-slate-500 uppercase ml-1">Virtual Balance (₹ or $)</label>
            <input 
              type="number" 
              value={initialBalance}
              onChange={(e) => setInitialBalance(e.target.value)}
              className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white font-mono focus:outline-none focus:border-indigo-500/50 transition-colors"
              placeholder="e.g. 2000"
            />
          </div>

          <button 
            onClick={initializeSimulation}
            className="w-full mt-4 py-4 rounded-xl bg-indigo-500 hover:bg-indigo-400 text-white font-bold font-mono tracking-widest flex items-center justify-center gap-2 transition-all shadow-lg shadow-indigo-500/20"
          >
            <PlayCircle size={18} />
            START SIMULATION
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-8 custom-scrollbar">
      <div className="max-w-7xl mx-auto flex flex-col gap-8">
        
        {/* DASHBOARD HEADER */}
        <div className="flex items-end justify-between">
          <div>
            <div className="flex items-center gap-2 text-indigo-400 mb-1">
              <RefreshCw size={12} className={isRefreshing ? "animate-spin" : ""} />
              <span className="text-[10px] font-bold tracking-[0.2em] uppercase">SYSTEM.SIM_STATUS: ONLINE</span>
            </div>
            <h1 className="text-3xl font-bold tracking-tight text-white font-mono uppercase">💰 Virtual Portfolio</h1>
          </div>
          <div className="flex gap-4">
            <button className="clay-btn-secondary px-4 py-2 flex items-center gap-2" onClick={handleUpdate}>
              <RefreshCw size={14} className={isRefreshing ? "animate-spin" : ""} />
              REFRESH
            </button>
          </div>
        </div>

        {/* SUMMARY STATS */}
        <div className="flex flex-wrap gap-4">
          <StatCard 
            title="Total Balance" 
            value={`₹${(data.total_balance ?? 0).toFixed(2)}`} 
            subValue={(data.profit_loss_percentage ?? 0) >= 0 ? `+${(data.profit_loss_percentage ?? 0).toFixed(2)}%` : `${(data.profit_loss_percentage ?? 0).toFixed(2)}%`}
            icon={Wallet} 
            color={(data.profit_loss_percentage ?? 0) >= 0 ? T.buy : T.sell} 
          />
          <StatCard 
            title="Available Cash" 
            value={`₹${(data.available_cash ?? 0).toFixed(2)}`} 
            icon={RefreshCw} 
            color="#94a3b8" 
          />
          <StatCard 
            title="Invested Amount" 
            value={`₹${(data.invested_amount ?? 0).toFixed(2)}`} 
            icon={TrendingUp} 
            color="#818cf8" 
          />
          <StatCard 
            title="Total P/L" 
            value={`${(data.total_profit_loss ?? 0) >= 0 ? "+" : ""}₹${(data.total_profit_loss ?? 0).toFixed(2)}`} 
            icon={(data.total_profit_loss ?? 0) >= 0 ? TrendingUp : TrendingDown} 
            color={(data.total_profit_loss ?? 0) >= 0 ? T.buy : T.sell} 
          />
           <StatCard 
            title="AI Accuracy" 
            value={`${(data.accuracy_metrics?.accuracy_score ?? 100).toFixed(1)}%`} 
            subValue={`${data.accuracy_metrics?.total_trades ?? 0} TRADES TOTAL`}
            icon={Shield} 
            color={T.accent} 
          />
        </div>

        {/* POSITIONS TABLE */}
        <div className="clay-card overflow-hidden">
          <div className="px-6 py-4 border-b border-white/10 flex items-center justify-between">
            <h3 className="text-xs font-bold tracking-widest text-white uppercase font-mono">Current Positions</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-white/5 border-b border-white/10">
                  <th className="px-6 py-3 text-[10px] font-bold text-slate-400 uppercase tracking-widest">Ticker</th>
                  <th className="px-6 py-3 text-[10px] font-bold text-slate-400 uppercase tracking-widest">Buy Price</th>
                  <th className="px-6 py-3 text-[10px] font-bold text-slate-400 uppercase tracking-widest">Live Price</th>
                  <th className="px-6 py-3 text-[10px] font-bold text-slate-400 uppercase tracking-widest">Quantity</th>
                  <th className="px-6 py-3 text-[10px] font-bold text-slate-400 uppercase tracking-widest">Invested</th>
                  <th className="px-6 py-3 text-[10px] font-bold text-slate-400 uppercase tracking-widest">Cur. Value</th>
                  <th className="px-6 py-3 text-[10px] font-bold text-slate-400 uppercase tracking-widest">P/L</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {data.positions.length === 0 ? (
                  <tr>
                    <td colSpan="7" className="px-6 py-12 text-center text-slate-500 font-mono text-[10px] uppercase tracking-widest">
                      No active virtual positions. Choose a stock from the search or map to invest.
                    </td>
                  </tr>
                ) : (
                  data.positions.map((pos) => (
                    <tr key={pos.ticker} className="hover:bg-white/5 transition-colors cursor-pointer group" onClick={() => onSelect(pos.ticker)}>
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-lg bg-indigo-500/10 border border-indigo-400/20 flex items-center justify-center font-bold text-[10px] text-white">
                            {pos.ticker[0]}
                          </div>
                          <span className="font-bold text-white group-hover:text-indigo-400 transition-colors">{pos.ticker}</span>
                        </div>
                      </td>
                      <td className="px-6 py-4 font-mono text-xs text-slate-300">₹{pos.buy_price.toFixed(2)}</td>
                      <td className="px-6 py-4 font-mono text-xs text-white">₹{(pos.current_price || pos.buy_price).toFixed(2)}</td>
                      <td className="px-6 py-4 font-mono text-xs text-slate-400">{pos.quantity.toFixed(4)}</td>
                      <td className="px-6 py-4 font-mono text-xs text-slate-300">₹{pos.invested_value.toFixed(2)}</td>
                      <td className="px-6 py-4 font-mono text-xs text-white font-bold">₹{(pos.current_value || pos.invested_value).toFixed(2)}</td>
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-2 font-mono font-bold text-xs" style={{ color: (pos.profit_loss || 0) >= 0 ? T.buy : T.sell }}>
                          {(pos.profit_loss || 0) >= 0 ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}
                          {((pos.profit_loss || 0) >= 0 ? "+" : "")}{(pos.profit_loss || 0).toFixed(2)} ({(pos.profit_loss_pct || 0).toFixed(2)}%)
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* PERFORMANCE SECTION */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
           <div className="clay-card p-6">
              <h3 className="text-xs font-bold tracking-widest text-white uppercase font-mono mb-4">Trade History</h3>
              <div className="flex flex-col gap-3">
                {data.history.slice(-5).reverse().map((h, i) => (
                  <div key={i} className="flex items-center justify-between p-3 rounded-xl bg-white/5 border border-white/10">
                    <div className="flex items-center gap-3">
                      <div className={`px-2 py-0.5 rounded text-[8px] font-bold tracking-widest ${h.type === 'BUY' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400'}`}>
                        {h.type}
                      </div>
                      <span className="font-bold text-xs text-white uppercase">{h.ticker}</span>
                    </div>
                    <div className="text-right">
                      <div className="text-[10px] font-mono font-bold text-white">₹{h.amount.toFixed(2)}</div>
                      <div className="text-[8px] text-slate-500 font-mono">{new Date(h.timestamp).toLocaleString()}</div>
                    </div>
                  </div>
                ))}
                {data.history.length === 0 && (
                   <span className="text-[10px] text-slate-500 font-mono text-center py-8">NO TRANSACTION HISTORY YET</span>
                )}
              </div>
           </div>
           
           <div className="clay-card p-6 flex flex-col items-center justify-center gap-4 text-center">
              <h3 className="text-xs font-bold tracking-widest text-white uppercase font-mono self-start mb-2">Mythic Insight</h3>
              <div className="w-20 h-20 rounded-full border-4 border-indigo-500/30 border-t-indigo-400 flex items-center justify-center">
                 <span className="text-xl font-mono font-bold text-indigo-400">{(data.accuracy_metrics?.accuracy_score ?? 100).toFixed(0)}%</span>
              </div>
              <p className="text-xs text-slate-400 leading-relaxed max-w-xs">
                Your AI-guided accuracy score represents the delta between mythic predictions and your simulated outcomes.
              </p>
              <div className="px-4 py-2 rounded-xl bg-indigo-500/10 border border-indigo-400/20 text-[10px] font-mono text-indigo-300 font-bold uppercase tracking-widest">
                Accuracy Level: {(data.accuracy_metrics?.accuracy_score ?? 100) > 70 ? 'PREDICTIVE_STABLE' : 'CALIBRATING'}
              </div>
           </div>
        </div>

      </div>
    </div>
  );
}
