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
  Shield,
  Zap,
  PieChart
} from "lucide-react";
import { T } from "../theme";

import { API_BASE } from "../api_config";

const StatCard = ({ title, value, subValue, icon: Icon, color }) => (
  <div className="glass-card p-5 flex flex-col gap-3 min-w-[200px] flex-1 interactive animate-slide-up">
    <div className="flex items-center justify-between">
      <span className="text-[10px] font-bold tracking-[0.2em] text-slate-500 uppercase">{title}</span>
      <div className="w-10 h-10 rounded-2xl flex items-center justify-center bg-indigo-500/10 border border-indigo-400/20 soft-glow">
        <Icon size={16} style={{ color }} />
      </div>
    </div>
    <div className="text-2xl font-mono font-black text-white tracking-tighter">{value}</div>
    {subValue && (
      <div className="text-[10px] font-mono font-bold flex items-center gap-1" style={{ color }}>
        <TrendingUp size={10} /> {subValue}
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
        <div className="glass-card p-12 max-w-lg w-full flex flex-col items-center gap-8 text-center bg-black/40">
          <div className="w-20 h-20 rounded-[32px] bg-indigo-500/10 border border-indigo-400/20 flex items-center justify-center mb-2 soft-glow">
            <Wallet size={40} className="text-indigo-400" />
          </div>
          <div className="space-y-2">
            <h2 className="text-3xl font-black tracking-tighter text-white font-mono uppercase">VIRTUAL TERMINAL</h2>
            <p className="text-[11px] text-slate-500 font-mono tracking-widest uppercase">SYTEM_SIMULATION_V4.0</p>
          </div>
          <p className="text-sm text-slate-400 leading-relaxed max-w-xs">
            Deploy OMNI-AXIOM's institutional-grade intelligence with zero risk exposure.
          </p>
          
          <div className="w-full flex flex-col gap-3 items-start mt-4">
            <label className="text-[10px] font-black tracking-[0.3em] text-indigo-400/60 uppercase ml-1">ALLOCATION_RESERVE (USD/INR)</label>
            <input 
              type="number" 
              value={initialBalance}
              onChange={(e) => setInitialBalance(e.target.value)}
              className="w-full bg-black/40 border border-white/10 rounded-2xl px-6 py-4 text-white font-mono text-lg focus:outline-none focus:border-indigo-500/50 transition-all shadow-inner"
              placeholder="e.g. 50000"
            />
          </div>

          <button 
            onClick={initializeSimulation}
            className="skeuo-button w-full h-16 py-0 text-sm tracking-[0.2em] gap-3"
          >
            <PlayCircle size={20} />
            INIT_SIMULATION
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-8 custom-scrollbar">
      <div className="max-w-7xl mx-auto flex flex-col gap-8">
        
        {/* DASHBOARD HEADER */}
        <div className="flex items-end justify-between border-b border-white/5 pb-8 mb-4">
          <div>
            <div className="flex items-center gap-2 text-indigo-400/60 mb-2">
              <div className={`w-2 h-2 rounded-full ${isRefreshing ? "animate-spin border-t-2 border-indigo-400" : "bg-emerald-500 soft-glow"}`} />
              <span className="text-[10px] font-black tracking-[0.3em] uppercase font-mono">SIMULATION_CORE_V4::STABLE</span>
            </div>
            <h1 className="text-4xl font-black tracking-tighter text-white font-mono uppercase bg-gradient-to-r from-white to-slate-500 bg-clip-text text-transparent">
              🏦 Virtual Portfolio
            </h1>
          </div>
          <div className="flex gap-3">
            <button className="skeuo-button h-10 px-5 gap-2 text-[10px] tracking-widest font-mono" onClick={handleUpdate}>
              <RefreshCw size={14} className={isRefreshing ? "animate-spin" : ""} />
              FORCE_SYNC
            </button>
            <button className="skeuo-button h-10 px-5 gap-2 text-[10px] tracking-widest font-mono !bg-indigo-600/20 !border-indigo-400/30">
              <Zap size={14} className="text-indigo-400" />
              AUTO_DEPLOY
            </button>
          </div>
        </div>


        {/* SUMMARY STATS */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6">
          <StatCard 
            title="Equity Value" 
            value={`$${(data.total_balance ?? 0).toLocaleString()}`} 
            subValue={(data.profit_loss_percentage ?? 0) >= 0 ? `${(data.profit_loss_percentage ?? 0).toFixed(2)}%` : `${(data.profit_loss_percentage ?? 0).toFixed(2)}%`}
            icon={Wallet} 
            color={(data.profit_loss_percentage ?? 0) >= 0 ? T.buy : T.sell} 
          />
          <StatCard 
            title="Available Liquidity" 
            value={`$${(data.available_cash ?? 0).toLocaleString()}`} 
            icon={RefreshCw} 
            color="#94a3b8" 
          />
          <StatCard 
            title="Deployed Capital" 
            value={`$${(data.invested_amount ?? 0).toLocaleString()}`} 
            icon={TrendingUp} 
            color="#818cf8" 
          />
          <StatCard 
            title="Floating P/L" 
            value={`${(data.total_profit_loss ?? 0) >= 0 ? "+" : ""}$${(data.total_profit_loss ?? 0).toLocaleString()}`} 
            icon={(data.total_profit_loss ?? 0) >= 0 ? TrendingUp : TrendingDown} 
            color={(data.total_profit_loss ?? 0) >= 0 ? T.buy : T.sell} 
          />
           <StatCard 
            title="Algorithm Reliability" 
            value={`${(data.accuracy_metrics?.accuracy_score ?? 100).toFixed(1)}%`} 
            subValue={`${data.accuracy_metrics?.total_trades ?? 0} OPERATIONS`}
            icon={Shield} 
            color="#6366f1" 
          />
        </div>


        {/* POSITIONS TABLE */}
        <div className="glass-card bg-black/20 animate-slide-up" style={{ animationDelay: '0.1s' }}>
          <div className="px-8 py-6 border-b border-white/5 flex items-center justify-between bg-white/[0.02]">
            <div className="flex items-center gap-3">
              <div className="w-1.5 h-6 bg-indigo-500 rounded-full" />
              <h3 className="text-sm font-black tracking-[0.2em] text-white uppercase font-mono">Institutional Holdings</h3>
            </div>
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
                    <tr key={pos.ticker} className="hover:bg-white/[0.04] transition-colors cursor-pointer group border-b border-white/[0.04]" onClick={() => onSelect(pos.ticker)}>
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3">
                          <div className="w-9 h-9 rounded-xl bg-slate-900 border border-white/10 flex items-center justify-center font-bold text-[11px] text-white shadow-inner">
                            {pos.ticker[0]}
                          </div>
                          <span className="font-bold text-white group-hover:text-indigo-400 transition-colors tracking-tight">{pos.ticker}</span>
                        </div>
                      </td>
                      <td className="px-6 py-4 font-mono text-[11px] text-slate-400">₹{(pos.buy_price || 0).toLocaleString()}</td>
                      <td className="px-6 py-4 font-mono text-[11px] text-white">₹{(pos.current_price || pos.buy_price || 0).toLocaleString()}</td>
                      <td className="px-6 py-4 font-mono text-[11px] text-slate-500">{ (pos.quantity || 0).toFixed(4) }</td>
                      <td className="px-6 py-4 font-mono text-[11px] text-slate-400">₹{(pos.invested_value || 0).toLocaleString()}</td>
                      <td className="px-6 py-4 font-mono text-[11px] text-white font-black">₹{(pos.current_value || pos.invested_value || 0).toLocaleString()}</td>
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-2 font-mono font-black text-[11px]" style={{ color: (pos.profit_loss || 0) >= 0 ? T.buy : T.sell }}>
                          {(pos.profit_loss || 0) >= 0 ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
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

        {/* PERFORMANCE SECTION grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-12">
           <div className="glass-card p-8 lg:col-span-2 bg-black/20 animate-slide-up" style={{ animationDelay: '0.2s' }}>
              <div className="flex items-center justify-between mb-8">
                <h3 className="text-sm font-black tracking-[0.2em] text-white uppercase font-mono">Audit Log :: Transactions</h3>
                <span className="text-[10px] text-slate-500 font-mono tracking-widest">{data.history.length} ENTRIES</span>
              </div>
              <div className="flex flex-col gap-4">
                {data.history.slice(-8).reverse().map((h, i) => (
                  <div key={i} className="flex items-center justify-between p-4 rounded-xl bg-white/[0.02] border border-white/5 hover:border-indigo-500/30 hover:bg-white/[0.04] transition-all group">
                    <div className="flex items-center gap-5">
                      <div className={`w-8 h-8 rounded-lg flex items-center justify-center font-black text-[9px] tracking-widest ${h.type === 'BUY' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-red-500/10 text-red-400 border border-red-500/20'}`}>
                        {h.type}
                      </div>
                      <div>
                        <div className="text-[12px] font-black text-white group-hover:text-indigo-400 transition-colors uppercase font-mono tracking-tight">{h.ticker}</div>
                        <div className="text-[8px] font-mono text-slate-600 mt-0.5 uppercase tracking-tighter">
                          {new Date(h.timestamp).toLocaleString(undefined, {hour:'2-digit', minute:'2-digit', second:'2-digit'})} // NODE_EXEC_01
                        </div>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-[13px] font-mono font-black text-white whitespace-nowrap">₹ {(h.amount || 0).toLocaleString()}</div>
                      <div className="text-[8px] text-slate-700 font-mono uppercase tracking-[0.2em] mt-1">SETTLED</div>
                    </div>
                  </div>
                ))}
                {data.history.length === 0 && (
                   <div className="text-center py-16 opacity-30 grayscale">
                      <RefreshCw size={32} className="mx-auto mb-4" />
                      <span className="text-[10px] text-slate-500 font-mono tracking-widest">ZERO_HISTORY_DATA_AVAILABLE</span>
                   </div>
                )}
              </div>
           </div>
           
           <div className="glass-card p-8 flex flex-col items-center justify-center gap-6 text-center bg-black/30 border-indigo-500/20 animate-slide-up" style={{ animationDelay: '0.3s' }}>
              <div className="flex flex-col items-center gap-2 self-start mb-4">
                <div className="w-1.5 h-6 bg-indigo-500 rounded-full mb-1" />
                <h3 className="text-sm font-black tracking-[0.2em] text-white uppercase font-mono">Mythic_Engine</h3>
              </div>
              
              <div className="relative">
                <div className="w-32 h-32 rounded-full border-2 border-indigo-500/10 flex items-center justify-center relative">
                   <div className="absolute inset-0 rounded-full border-t-2 border-indigo-400 animate-spin transition-all duration-1000" />
                   <span className="text-3xl font-mono font-black text-white tracking-tighter drop-shadow-glow">{(data.accuracy_metrics?.accuracy_score ?? 100).toFixed(0)}%</span>
                </div>
                {/* Orbital dots */}
                <div className="absolute -top-1 -right-1 w-3 h-3 bg-indigo-500 rounded-full soft-glow animate-pulse" />
              </div>

              <div className="space-y-3">
                <p className="text-[11px] text-slate-400 leading-relaxed font-medium">
                  CALIBRATING PREDICTIVE ACCURACY AGAINST LIVE MARKET DELTAS.
                </p>
                <div className="px-6 py-3 rounded-2xl bg-indigo-500/5 border border-indigo-400/20 text-[10px] font-mono text-indigo-400 font-black uppercase tracking-[0.2em] shadow-inner">
                  LVL: {(data.accuracy_metrics?.accuracy_score ?? 100) > 70 ? 'PREDICTIVE_STABLE' : 'CALIBRATING'}
                </div>
              </div>

              <button className="skeuo-button w-full mt-4 h-12 gap-2 text-[10px] tracking-widest uppercase">
                <Shield size={14} className="text-indigo-400" />
                DEPLOY_RISK_SHIELD
              </button>
           </div>
        </div>


      </div>
    </div>
  );
}
