import React, { useState } from "react";
import { 
  Layers, 
  Sparkles, 
  AlertTriangle, 
  Activity, 
  Zap, 
  Cpu, 
  X, 
  TrendingUp, 
  BarChart2, 
  Shield,
  Loader2,
  ChevronRight
} from "lucide-react";
import { AGENTS } from "../data";

const FrequencyVisualizer = ({ color }) => (
  <div className="flex items-end gap-[1px] h-2 px-1">
    {[0.4, 0.7, 0.5, 0.9, 0.6, 0.8, 0.3].map((h, i) => (
      <div key={i} className="w-[1px] bg-current" 
        style={{ 
          height: `${h * 100}%`, 
          color: color,
          animation: `pulse 1.5s ease-in-out infinite ${i * 0.1}s`,
          opacity: 0.6
        }} 
      />
    ))}
  </div>
);

export default function AgentMatrixView({ agentsStatus = [] }) {
  const [selectedAgent, setSelectedAgent] = useState(null);

  const displayAgents = Object.entries(AGENTS).map(([key, metadata]) => {
    const live = agentsStatus.find(s => s.name === metadata.name);
    return {
      ...metadata,
      id: key,
      status: live ? (live.status === 'active' ? 'Active' : 'Standby') : metadata.status,
    };
  });

  const totalOps = displayAgents.reduce((s, a) => s + a.tasks, 0);
  const avgAcc = (displayAgents.reduce((s, a) => s + a.acc, 0) / displayAgents.length).toFixed(1);

  return (
    <div className="flex-1 overflow-y-auto no-scrollbar page-padding">
      <div className="content-max-w space-y-6 md:space-y-10 animate-fade-in">
        
        {/* SHARP Header Alignment */}
        <div className="flex flex-col lg:flex-row lg:items-end justify-between border-b border-white/[0.08] pb-6 md:pb-8 gap-6">
          <div className="flex flex-col gap-4">
            <div className="flex items-center gap-4 md:gap-6">
              <div className="w-11 h-11 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center shadow-sm">
                <Layers size={22} className="text-indigo-400" />
              </div>
              <h1 className="text-xl md:text-2xl font-bold text-white tracking-tight uppercase leading-none">
                Agent Matrix
              </h1>
            </div>
            <div className="flex items-center gap-4 md:gap-6 text-[9px] text-slate-500 font-bold tracking-[0.2em] px-1 uppercase">
              <span className="flex items-center gap-2"><Activity size={10} className="text-indigo-500/60"/> AVG_ACCURACY: {avgAcc}%</span>
              <div className="w-[1px] h-3 bg-white/10 hidden md:block"/>
              <span className="flex items-center gap-2"><Zap size={10} className="text-amber-500/60"/> AGGREGATE_OPS: {totalOps.toLocaleString()}</span>
            </div>
          </div>
          
          <div className="flex gap-3">
             <div className="px-4 py-2 rounded-md bg-white/[0.02] border border-white/[0.08] text-slate-500 font-mono text-[9px] tracking-widest flex items-center gap-2">
               <Cpu size={12} /> SYNERGY_v4.2
             </div>
             <button className="skeuo-button px-5 py-2 text-[9px] gap-2">
               <Sparkles size={12} className="text-indigo-400" /> REBALANCE
             </button>
          </div>
        </div>

        {/* RESPONSIVE Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 md:gap-6">
          {displayAgents.map((a) => {
            const Icon = a.icon;
            const isWarn = a.status === 'Retraining' || a.status === 'Learning' || a.status === 'Standby';
            const isActive = a.status === 'Active';
            const isMythic = a.tier === 'v4_mythic';
            
            return (
              <div key={a.id} onClick={() => setSelectedAgent(a)} 
                className="group glass-card p-5 md:p-6 flex flex-col gap-6 interactive">
                <div className="flex justify-between items-start">
                  <div className="flex items-center gap-4">
                    <div className="w-11 h-11 rounded-lg flex items-center justify-center border transition-all duration-120 group-hover:scale-105"
                      style={{ background: `${a.color}08`, borderColor: `${a.color}15`, color: a.color }}>
                      <Icon size={20} />
                    </div>
                    <div className="flex flex-col gap-0.5">
                      <span className="text-[14px] font-bold text-white uppercase tracking-tight">{a.name}</span>
                      <div className="flex items-center gap-1.5 text-[8px] text-slate-600 font-bold tracking-widest uppercase">
                        <span>{isMythic ? 'MYTHIC_NODE' : 'STD_NODE'}</span>
                        <FrequencyVisualizer color={a.color} />
                      </div>
                    </div>
                  </div>
                  <div className={`status-badge ${isActive ? 'positive' : ''}`}>
                    {a.status}
                  </div>
                </div>

                <p className="text-[11px] text-slate-400 leading-relaxed min-h-[44px] line-clamp-3 italic opacity-80 group-hover:opacity-100 transition-opacity">
                  "{a.desc}"
                </p>

                <div className="space-y-4">
                  <div className="space-y-1.5">
                    <div className="flex justify-between text-[8px] font-bold text-slate-600 uppercase tracking-widest px-0.5">
                      <span>INTELLIGENCE_QUOTIENT</span>
                      <span className="font-mono text-white">{a.acc}%</span>
                    </div>
                    <div className="h-1 bg-black/40 rounded-sm overflow-hidden border border-white/[0.04]">
                      <div className="h-full bg-indigo-500/60" style={{ width: `${a.acc}%` }} />
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div className="bg-white/[0.01] border border-white/[0.03] p-3 rounded-md flex flex-col gap-1">
                      <span className="text-[8px] text-slate-700 font-black tracking-widest uppercase">Throughput</span>
                      <span className="text-[13px] font-mono font-bold text-white">{a.tasks >= 1000 ? `${(a.tasks/1000).toFixed(1)}k` : a.tasks} <span className="text-[9px] text-slate-800">OPS</span></span>
                    </div>
                    <div className="bg-white/[0.01] border border-white/[0.03] p-3 rounded-md flex flex-col gap-1">
                      <span className="text-[8px] text-slate-700 font-black tracking-widest uppercase">Reliability</span>
                      <div className="flex gap-1 items-center h-4">
                        {[1,2,3,4,5].map(i => (
                          <div key={i} className={`w-1.5 h-1.5 rounded-[1px] ${i <= 4 ? 'bg-indigo-500/50' : 'bg-white/5'}`} />
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* MODAL RESPONSIVE OVERHAUL */}
      {selectedAgent && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 md:p-8 bg-black/90 backdrop-blur-md animate-fade-in">
          <div className="absolute inset-0" onClick={() => setSelectedAgent(null)} />
          <div className="relative w-full max-w-4xl h-full lg:h-[80vh] flex flex-col bg-[#0B0F14] border border-white/[0.08] rounded-lg overflow-hidden shadow-2xl">
            
            <div className="h-14 px-6 flex items-center justify-between border-b border-white/[0.08] shrink-0">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-md flex items-center justify-center border" style={{ background: `${selectedAgent.color}08`, borderColor: `${selectedAgent.color}20`, color: selectedAgent.color }}>
                  {React.createElement(selectedAgent.icon, { size: 16 })}
                </div>
                <h2 className="text-[12px] font-bold text-white uppercase tracking-widest">{selectedAgent.name} // CORE_NODE</h2>
              </div>
              <button onClick={() => setSelectedAgent(null)} className="w-8 h-8 flex items-center justify-center text-slate-600 hover:text-white transition-colors">
                <X size={20} />
              </button>
            </div>

            <div className="flex-1 flex flex-col lg:flex-row overflow-hidden overflow-y-auto lg:overflow-hidden">
              <div className="w-full lg:w-1/3 border-b lg:border-b-0 lg:border-r border-white/[0.08] p-6 md:p-8 flex flex-col gap-8 md:gap-10">
                <div className="space-y-4">
                  <span className="text-[9px] font-bold text-slate-600 tracking-widest uppercase">MODEL_STATUS</span>
                  <div className="grid grid-cols-2 lg:grid-cols-1 gap-3">
                    <div className="p-4 rounded-md bg-black/40 border border-white/[0.04] flex flex-col gap-1">
                      <span className="text-[8px] font-bold text-slate-700 uppercase">Input Stream</span>
                      <span className="text-lg font-mono font-bold text-white">1.4M <span className="text-[10px] text-slate-800">TPS</span></span>
                    </div>
                    <div className="p-4 rounded-md bg-black/40 border border-white/[0.04] flex flex-col gap-1">
                      <span className="text-[8px] font-bold text-slate-700 uppercase">Latency</span>
                      <span className="text-lg font-mono font-bold text-emerald-400">12ms</span>
                    </div>
                  </div>
                </div>
                <div className="space-y-4">
                  <span className="text-[9px] font-bold text-slate-600 tracking-widest uppercase">SYNOPSIS</span>
                  <p className="text-[11px] text-slate-400 leading-relaxed italic opacity-80">"{selectedAgent.desc}"</p>
                </div>
              </div>

              <div className="flex-1 p-6 md:p-8 bg-black/20 flex flex-col gap-6">
                <div className="flex items-center justify-between">
                  <h3 className="text-[10px] font-bold text-slate-600 tracking-widest uppercase">Execution Buffer</h3>
                  <div className="flex items-center gap-2">
                    <div className="w-1 h-1 rounded-sm bg-emerald-500 animate-pulse" />
                    <span className="text-[8px] font-bold text-emerald-500/60 tracking-widest uppercase font-mono">Stream_Active</span>
                  </div>
                </div>

                <div className="flex-1 bg-black/40 rounded-md border border-white/[0.06] p-4 md:p-6 font-mono text-[10px] text-slate-600 overflow-y-auto no-scrollbar space-y-3 shadow-inner min-h-[200px]">
                  <div className="flex gap-4"><span className="text-indigo-500/40 shrink-0">[10:24:01]</span><span>Initializing quantum weights for {selectedAgent.name}...</span></div>
                  <div className="flex gap-4"><span className="text-indigo-500/40 shrink-0">[10:24:05]</span><span>Consolidating market triggers... [SUCCESS]</span></div>
                  <div className="flex gap-4"><span className="text-indigo-500/40 shrink-0">[10:24:12]</span><span>Synthesizing signal across nexus...</span></div>
                  <div className="flex gap-4 py-2 border-y border-white/[0.02] my-2"><span className="text-emerald-500/40 shrink-0">TERMINAL:</span><span className="text-emerald-500/80">Objective locked. Awaiting consensus from {selectedAgent.id === 'orchestrator' ? 'sub-nodes' : 'Orchestrator'}.</span></div>
                  <div className="flex gap-4"><span className="text-indigo-500/40 shrink-0">[10:24:45]</span><span>Trace hash verified: 0x8F5...2E9</span></div>
                </div>

                <button className="h-11 rounded-md bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-[10px] tracking-[0.2em] flex items-center justify-center gap-3 transition-all duration-120 uppercase">
                  <Zap size={14} fill="white" /> EXTRACT_NEURAL_LOGS
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
