import React, { useState, useEffect } from "react";
import { 
  Target, 
  TrendingUp, 
  TrendingDown, 
  Info, 
  Zap, 
  ChevronRight, 
  LayoutGrid,
  Activity,
  Shield,
  Search
} from "lucide-react";
import { API_BASE } from "../constants/config";

const ResearchCard = ({ suggestion, onActivate }) => {
  const [showDetail, setShowDetail] = useState(false);
  const breakdown = suggestion.breakdown || {};

  return (
    <div className="clay-card p-6 flex flex-col gap-4 border-indigo-500/10 hover:border-indigo-400/30 transition-all group">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-2xl bg-indigo-500/10 border border-indigo-400/20 flex items-center justify-center font-bold text-sm text-white group-hover:scale-110 transition-transform">
            {suggestion.ticker[0]}
          </div>
          <div>
            <h3 className="font-bold text-lg text-white font-mono uppercase leading-none">{suggestion.ticker}</h3>
            <span className="text-[9px] font-bold tracking-[0.15em] text-indigo-400 uppercase">MISSION_SCORE: {(suggestion.score * 100).toFixed(0)}%</span>
          </div>
        </div>
        <div className={`px-3 py-1 rounded-full text-[9px] font-bold tracking-widest ${suggestion.signal.includes('STRONG') ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' : 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/30'}`}>
          {suggestion.signal}
        </div>
      </div>

      <p className="text-[11px] text-slate-300 leading-relaxed font-medium italic">
        "{suggestion.reasoning}"
      </p>

      <div className="grid grid-cols-2 gap-2 mt-2">
        <div className="clay-inset p-3 flex flex-col gap-1">
          <span className="text-[8px] text-slate-500 uppercase font-bold tracking-tighter">1M PERFORMANCE:</span>
          <span className={`text-sm font-mono font-bold ${suggestion.perf_1m >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
            {suggestion.perf_1m >= 0 ? '+' : ''}{suggestion.perf_1m}%
          </span>
        </div>
        <div className="clay-inset p-3 flex flex-col gap-1">
          <span className="text-[8px] text-slate-500 uppercase font-bold tracking-tighter">AI CONFIDENCE:</span>
          <span className="text-sm font-mono font-bold text-indigo-300">MEDIUM_HIGH</span>
        </div>
      </div>

      <div className="flex flex-col gap-2 mt-2">
        <button 
          onClick={() => setShowDetail(!showDetail)}
          className="w-full py-2.5 rounded-xl bg-white/5 hover:bg-white/10 border border-white/5 text-[10px] font-bold text-slate-400 tracking-widest flex items-center justify-center gap-2 transition-all uppercase font-mono"
        >
          <Search size={12} />
          {showDetail ? 'Hide Deep Research' : 'View 14-Agent Deep Dive'}
        </button>

        {showDetail && (
          <div className="flex flex-col gap-4 p-4 rounded-2xl bg-black/40 border border-white/5 animate-slide-down mt-2">
             <div className="flex flex-col gap-3">
                {Object.entries(breakdown).map(([key, val]) => (
                  <div key={key} className="flex flex-col gap-1.5 p-2 rounded-lg bg-white/5 border border-white/10">
                    <div className="flex items-center justify-between">
                      <span className="text-[9px] font-bold text-indigo-400 uppercase tracking-widest font-mono">{key} ANALYSIS</span>
                      <span className={`text-[8px] font-bold ${val.signal === 'BULLISH' ? 'text-emerald-400' : (val.signal === 'BEARISH' ? 'text-red-400' : 'text-slate-400')}`}>
                        {val.signal}
                      </span>
                    </div>
                    <p className="text-[9px] text-slate-400 leading-snug line-clamp-2">{val.reason}</p>
                  </div>
                ))}
             </div>
          </div>
        )}

        <button 
          onClick={() => onActivate(suggestion.ticker)}
          className="w-full py-3.5 rounded-xl bg-indigo-500 hover:bg-indigo-400 text-white font-bold text-xs tracking-[0.2em] flex items-center justify-center gap-2 transition-all shadow-lg shadow-indigo-500/20 active:scale-95 uppercase font-mono mt-2"
        >
          <Zap size={14} fill="white" />
          ACTIVATE MISSION
        </button>
      </div>
    </div>
  );
};

export default function DeepResearchSuggestions() {
  const [suggestions, setSuggestions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activating, setActivating] = useState(false);

  const fetchSuggestions = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/mission/suggestions`);
      const data = await res.json();
      setSuggestions(data.suggestions || []);
      setLoading(false);
    } catch (err) {
      console.error("Failed to fetch suggestions:", err);
    }
  };

  const handleActivate = async (ticker) => {
    setActivating(true);
    try {
      const res = await fetch(`${API_BASE}/api/mission/activate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ticker, amount: 2000, reasoning: "User approved Mission suggestion." })
      });
      const data = await res.json();
      if (data.status === 'success') {
         alert(`Mission Activated! Virtual trade executed for ${ticker}.`);
      }
    } catch (err) {
      console.error("Failed to activate:", err);
    } finally {
      setActivating(false);
    }
  };

  useEffect(() => {
    fetchSuggestions();
  }, []);

  if (loading && suggestions.length === 0) return (
     <div className="flex flex-col items-center justify-center p-20 gap-4">
        <Activity size={40} className="text-indigo-500 animate-pulse" />
        <span className="text-xs font-mono font-bold text-slate-500 uppercase tracking-widest">Compiling Deep Fleet Consensus...</span>
     </div>
  );

  return (
    <div className="flex flex-col gap-10">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-bold tracking-[0.25em] text-white uppercase font-mono flex items-center gap-3">
          <Target size={18} className="text-indigo-400" />
          High-Conviction Research Suggestions
        </h2>
        <div className="flex items-center gap-2">
           <Shield size={14} className="text-emerald-400" />
           <span className="text-[10px] font-mono text-emerald-400 uppercase tracking-widest">14-AGENT CONSENSUS_VERIFIED</span>
        </div>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
        {suggestions.map((s, i) => (
          <ResearchCard key={s.ticker + i} suggestion={s} onActivate={handleActivate} />
        ))}
        {suggestions.length === 0 && (
           <div className="col-span-full py-24 text-center flex flex-col items-center gap-4 border border-dashed border-white/10 rounded-3xl bg-white/5">
              <LayoutGrid size={32} className="text-slate-600" />
              <div className="flex flex-col gap-1">
                 <span className="text-xs font-mono font-bold text-slate-400 uppercase tracking-widest">No Suggestion Waves Detected</span>
                 <span className="text-[10px] text-slate-600 uppercase font-mono">Mission Control requires 80%+ consensus alignment.</span>
              </div>
           </div>
        )}
      </div>
    </div>
  );
}
