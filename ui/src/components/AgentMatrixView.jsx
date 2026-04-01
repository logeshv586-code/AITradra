import React, { useState } from "react";
import { Layers, Sparkles, AlertTriangle, Activity, Zap, Cpu, X, TrendingUp, BarChart2, Shield } from "lucide-react";
import { T } from "../theme";
import { AGENTS } from "../data";
import { GlassCard } from "./Shared";

const FrequencyVisualizer = ({ color }) => (
  <div className="flex items-end gap-[2px] h-3 px-2">
    {[0.4, 0.7, 0.5, 0.9, 0.6, 0.8, 0.3].map((h, i) => (
      <div key={i} className="w-[1.5px] frequency-bar" 
        style={{ 
          height: `${h * 100}%`, 
          background: color,
          animationDelay: `${i * 0.1}s`,
          boxShadow: `0 0 4px ${color}`
        }} 
      />
    ))}
  </div>
);

export default function AgentMatrixView({ agentsStatus = [] }) {
  const [selectedAgent, setSelectedAgent] = useState(null);

  // Merge live status with static metadata
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
    <div className="flex-1 p-8 overflow-y-auto no-scrollbar relative">
      {/* Background Neural Flow (Decorative) */}
      <svg className="absolute inset-0 w-full h-full pointer-events-none opacity-20">
        <path d="M100,100 Q400,300 800,100" fill="none" stroke="currentColor" strokeWidth="0.5" className="text-indigo-500 animate-flow-line" />
        <path d="M200,600 Q500,400 900,600" fill="none" stroke="currentColor" strokeWidth="0.5" className="text-indigo-500 animate-flow-line" style={{ animationDelay: '-2s' }} />
      </svg>

      <div className="max-w-7xl mx-auto space-y-10 animate-fade-in relative z-10">
        <div className="flex items-end justify-between border-b border-white/5 pb-6">
          <div className="space-y-2">
            <h2 className="text-4xl font-black flex items-center gap-4 text-white text-shadow-glow tracking-tighter">
                <div className="p-3 rounded-2xl animate-cyber-pulse glass-card" style={{
                background: 'linear-gradient(135deg, rgba(99,102,241,0.25), rgba(99,102,241,0.10))',
                border: '1px solid rgba(99,102,241,0.35)'
              }}>
                <Layers size={28} style={{ color: T.ai }} />
              </div>

              AGENT <span className="text-indigo-500">MATRIX</span>
            </h2>
            <div className="flex items-center gap-6 text-[11px] text-slate-500 font-bold tracking-[0.25em] px-1">
              <span className="flex items-center gap-2"><Activity size={12} className="text-indigo-400"/> ACCURACY: {avgAcc}%</span>
              <span className="w-1.5 h-1.5 rounded-full bg-slate-800"/>
              <span className="flex items-center gap-2"><Zap size={12} className="text-yellow-400"/> THROUGHPUT: {totalOps.toLocaleString()} OPS/S</span>
            </div>
          </div>
          <div className="hidden lg:flex gap-4">
             <div className="glass-card py-2.5 px-6 shadow-xl bg-purple-500/10 border-purple-500/20 text-purple-400 font-mono text-[10px] tracking-widest flex items-center gap-2">
               <Cpu size={14} /> NEMOTRON_LOCAL_GGUF
             </div>
             <div className="skeuo-button py-2.5 px-6 gap-2 text-[10px] tracking-widest">
               <Sparkles size={14} className="animate-spin-slow text-indigo-400" /> MYTHIC_ORCHESTRATION
             </div>
          </div>

        </div>

        <div className="grid-bento">
          {displayAgents.map((a) => {
            const Icon = a.icon;
            const isWarn = a.status === 'Retraining' || a.status === 'Learning' || a.status === 'Standby';
            const isActive = a.status === 'Active';
            const isMythic = a.tier === 'v4_mythic';
            const accentCol = isWarn ? T.warn : a.color;
            
            // Bento Area Assignment
            let bentoClass = "";
            if (a.id === 'think') bentoClass = "bento-main";
            else if (a.id === 'explanation') bentoClass = "bento-wide";
            else if (a.id === 'batch') bentoClass = "bento-tall";
            else if (a.id === 'orchestrator') bentoClass = "bento-main";

            return (
              <div key={a.id} onClick={() => setSelectedAgent(a)} className="cursor-pointer">
              <GlassCard interactive glowCol={accentCol} 
                className={`p-8 glass-holo flex flex-col h-full ${bentoClass} ${isActive ? 'animate-cyber-pulse-subtle' : ''}`}
                style={isMythic ? { border: `1px solid ${a.color}30`, boxShadow: `inset 0 0 30px ${a.color}08, 0 0 20px ${a.color}10` } : {}}
              >
                
                <div className="flex justify-between items-start mb-auto">
                  <div className="flex items-center gap-4">
                    <div className="p-4 rounded-2xl relative glass-card" style={{ 
                      background: `linear-gradient(135deg, ${a.color}25, ${a.color}10)`,
                      border: `1px solid ${a.color}40`,
                      boxShadow: `0 8px 24px ${a.color}20`
                    }}>
                      <Icon size={a.id === 'think' ? 32 : 24} style={{ color: a.color, filter: `drop-shadow(0 0 12px ${a.color})` }} />
                      {isActive && <div className="absolute -top-1.5 -right-1.5 w-3.5 h-3.5 bg-green-500 rounded-full border-4 border-[#0a0e1a] animate-pulse"/>}
                    </div>

                    <div>
                      <div className={`font-black tracking-tight text-white uppercase ${a.id === 'think' || a.id === 'orchestrator' ? 'text-2xl' : 'text-lg'}`}>{a.name}</div>
                      <div className="flex items-center gap-3 mt-1 text-[10px] text-slate-500 font-bold tracking-widest uppercase">
                        <span>{isMythic ? 'NODE_v4.0' : 'NODE_v3.1'}</span>
                        {isMythic && <span className="text-[8px] px-1.5 py-0.5 rounded bg-purple-500/15 text-purple-400 border border-purple-500/25">MYTHIC</span>}
                        <FrequencyVisualizer color={a.color} />
                      </div>
                    </div>
                  </div>
                  <span className={`glass-card text-[10px] font-black tracking-widest px-4 py-1.5 ${isWarn ? 'animate-soft-pulse' : ''}`}
                    style={{ 
                      background: isWarn ? `${T.warn}20` : `${T.buy}15`,
                      color: isWarn ? T.warn : T.buy,
                      borderColor: isWarn ? `${T.warn}40` : `${T.buy}35`,
                    }}>
                    {a.status.toUpperCase()}
                  </span>

                </div>
                
                <div className="my-8">
                  <p className={`leading-relaxed text-slate-400 font-medium border-l-4 pl-4 ${a.id === 'think' ? 'text-sm' : 'text-[11px]'}`} style={{ borderColor: `${a.color}40` }}>
                    {a.desc}
                  </p>
                </div>
                
                <div className="space-y-6 mt-auto">
                  <div className="space-y-2">
                    <div className="flex justify-between items-end px-1">
                      <span className="text-[10px] font-black text-slate-500 tracking-[0.1em] uppercase">Intelligence Matrix</span>
                      <span className="font-mono font-black text-sm" style={{ color: a.acc >= 70 ? T.buy : T.warn }}>{a.acc}%</span>
                    </div>
                    <div className="glass-card h-2 bg-black/50 shadow-inner rounded-full">
                      <div className="relative overflow-hidden h-full rounded-full transition-all duration-1000" 
                        style={{ 
                          width: `${a.acc}%`, 
                          background: `linear-gradient(90deg, ${a.color}90, ${a.color})`,
                        }}>
                        <div className="absolute inset-0 animate-shimmer" style={{ background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent)' }}/>
                      </div>
                    </div>

                  </div>
  
                  <div className={`grid gap-4 ${a.id === 'think' ? 'grid-cols-3' : 'grid-cols-2'}`}>
                    <div className="glass-panel p-4 flex flex-col justify-center gap-1 rounded-2xl">
                      <span className="text-[9px] text-slate-500 font-black uppercase tracking-widest">Throughput</span>
                      <div className="flex items-end gap-2">
                        <span className="font-mono font-bold text-lg text-white leading-none">{a.tasks.toLocaleString()}</span>
                        <span className="text-[9px] text-slate-600 font-black">OPS</span>
                      </div>
                    </div>
                    <div className="glass-panel p-4 flex flex-col justify-center gap-1 rounded-2xl">
                      <span className="text-[9px] text-slate-500 font-black uppercase tracking-widest">Critique</span>
                      <div className="flex items-center gap-3">
                        <div className="flex gap-1">
                          {[1,2,3,4].map(i => (
                            <div key={i} className={`w-2 h-2 rounded-full ${i <= 3 ? (isWarn ? 'bg-amber-500 shadow-[0_0_8px_#f59e0b]' : 'bg-indigo-500 shadow-[0_0_8px_#6366f1]') : 'bg-slate-800'}`}/>
                          ))}
                        </div>
                        <span className="text-xs text-slate-400 font-black">75%</span>
                      </div>
                    </div>
                    {a.id === 'think' && (
                       <div className="glass-panel p-4 flex flex-col justify-center gap-1 rounded-2xl">
                        <span className="text-[9px] text-slate-500 font-black uppercase tracking-widest">Neural Link</span>
                        <div className="text-xs text-indigo-400 font-black animate-pulse">ESTABLISHED</div>
                      </div>
                    )}
                  </div>

                </div>
              </GlassCard>
              </div>
            );
          })}
        </div>
      </div>

      {/* DETAILED AGENT DASHBOARD OVERLAY */}
      {selectedAgent && (
        <div className="absolute inset-0 z-50 flex items-center justify-center p-8 bg-black/60 backdrop-blur-md animate-fade-in">
          <div className="absolute inset-0 cursor-pointer" onClick={() => setSelectedAgent(null)} />
          <GlassCard className="relative w-full max-w-5xl h-[85vh] overflow-hidden flex flex-col glass-holo shadow-[0_20px_60px_rgba(0,0,0,0.8)] border border-white/10 p-0" glowCol={selectedAgent.color}>
            
            {/* Overlay Header */}
            <div className="p-8 border-b border-white/10 flex items-start justify-between bg-black/40">
              <div className="flex items-center gap-6">
                <div className="p-5 rounded-3xl" style={{ background: `linear-gradient(135deg, ${selectedAgent.color}30, ${selectedAgent.color}10)`, border: `1px solid ${selectedAgent.color}50` }}>
                  {React.createElement(selectedAgent.icon, { size: 36, color: selectedAgent.color })}
                </div>
                <div>
                  <h2 className="text-3xl font-black text-white uppercase tracking-tighter">{selectedAgent.name} // DASHBOARD</h2>
                  <div className="flex items-center gap-4 mt-2">
                    <span className="text-xs font-mono font-bold text-slate-400">ID: AXIOM-{selectedAgent.id.toUpperCase()}</span>
                    <span className={`glass-card text-[10px] font-black tracking-widest px-3 py-1 bg-${selectedAgent.status === 'Active' ? 'green' : 'amber'}-500/20 text-${selectedAgent.status === 'Active' ? 'green' : 'amber'}-400 border-${selectedAgent.status === 'Active' ? 'green' : 'amber'}-500/30`}>
                      {selectedAgent.status.toUpperCase()}
                    </span>

                  </div>
                </div>
              </div>
              <button className="p-2 rounded-full bg-white/5 hover:bg-white/10 transition-colors text-slate-400 hover:text-white" onClick={() => setSelectedAgent(null)}>
                <X size={24} />
              </button>
            </div>

            {/* Overlay Body */}
            <div className="flex-1 overflow-y-auto p-8 flex flex-col gap-8 no-scrollbar bg-gradient-to-b from-transparent to-[#0a0e1a]/80">
              <div className="grid grid-cols-3 gap-6">
                {/* Metric 1 */}
                <div className="glass-panel p-6 rounded-[2rem] flex flex-col gap-2">
                  <div className="flex items-center gap-2 mb-2 text-slate-400">
                    <TrendingUp size={16} /><span className="text-xs font-black uppercase tracking-[0.2em]">Input Volume</span>
                  </div>
                  <div className="text-3xl font-mono font-black text-white">{(selectedAgent.tasks * 1.4).toLocaleString()}</div>
                  <div className="text-[10px] uppercase font-black text-green-400 tracking-widest">▲ +12.4% TODAY</div>
                  <p className="text-[11px] text-slate-500 mt-3 font-medium leading-relaxed">Intelligence nodes harvested and ingested into nexus in the last 24h cycle.</p>
                </div>
                {/* Metric 2 */}
                <div className="glass-panel p-6 rounded-[2rem] flex flex-col gap-2">
                  <div className="flex items-center gap-2 mb-2 text-slate-400">
                    <Activity size={16} /><span className="text-xs font-black uppercase tracking-[0.2em]">Self-Improvement</span>
                  </div>
                  <div className="text-3xl font-mono font-black text-white">{selectedAgent.acc}% <span className="text-lg text-slate-500">ACC</span></div>
                  <div className="text-[10px] uppercase font-black text-indigo-400 tracking-widest">REINFORCEMENT ACTIVE</div>
                  <p className="text-[11px] text-slate-500 mt-3 font-medium leading-relaxed">Error gradients applied. Accuracy delta: +0.4% post-correction.</p>
                </div>
                {/* Metric 3 */}
                <div className="glass-panel p-6 rounded-[2rem] flex flex-col gap-2 border-indigo-500/20 shadow-inner">
                  <div className="flex items-center gap-2 mb-2 text-slate-400">
                    <Shield size={16} /><span className="text-xs font-black uppercase tracking-[0.2em]">Synapse State</span>
                  </div>
                  <div className="text-3xl font-mono font-black text-white" style={{ color: selectedAgent.color }}>NOMINAL</div>
                  <div className="text-[10px] uppercase font-black text-slate-400 tracking-widest">INTEGRITY_INDEX: 1.0</div>
                  <p className="text-[11px] text-slate-500 mt-3 font-medium leading-relaxed">Output signals verified by the Mythic Oversight layer.</p>
                </div>

              </div>

              {/* Data & Logs Block */}
              <div className="flex-1 grid grid-cols-2 gap-6">
                <div className="glass-panel p-8 rounded-[2rem] flex flex-col bg-black/20">
                  <h4 className="text-sm font-black text-slate-300 uppercase tracking-widest mb-6 flex items-center gap-3">
                    <div className="w-1.5 h-6 bg-indigo-500 rounded-full" />
                    Action_Register
                  </h4>
                  <div className="flex-1 space-y-3 font-mono text-[11px] text-slate-400 overflow-y-auto pr-2 custom-scroll">
                    {[1,2,3,4,5,6].map(i => (
                      <div key={i} className="flex gap-4 p-4 rounded-2xl bg-white/[0.02] border border-white/5 hover:border-indigo-500/20 transition-all">
                        <span className="text-indigo-400 font-black shrink-0">[{new Date(Date.now() - i*900000).toLocaleTimeString()}]</span>
                        <span className="text-slate-300">Synchronizing nexus heuristic weights... [OK]</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="glass-panel p-8 rounded-[2rem] flex flex-col bg-indigo-950/10 border-indigo-500/20">
                   <h4 className="text-sm font-black text-slate-300 uppercase tracking-widest mb-6 flex items-center gap-3">
                     <Zap size={18} className="text-indigo-400 fill-indigo-400/20"/>
                     Neural_Stream
                   </h4>
                   <div className="flex-1 border border-indigo-500/10 rounded-[1.5rem] bg-black/60 p-6 font-mono text-[11px] leading-relaxed text-indigo-200/80 overflow-y-auto shadow-inner">

                     {'>'} INITIALIZING KNOWLEDGE SYNC...<br/>
                     {'>'} ESTABLISHING OMNI-DATA CONNECTION... [OK]<br/>
                     {'>'} INGESTING 14,082 MARKET NODES...<br/>
                     {'>'} APPLYING SELF-ATTENTION TRANSFORMERS...<br/>
                     <br/>
                     <span className="text-indigo-400">AGENT OBJECTIVE:</span><br/>
                     {selectedAgent.desc}<br/>
                     <br/>
                     <span className="text-cyan-400">LATEST FINDING:</span><br/>
                     Successfully identified correlation anomaly in macro index. Retraining matrix active. Next update scheduled at 00:00 UTC.
                   </div>
                </div>
              </div>
            </div>
          </GlassCard>
        </div>
      )}
    </div>
  );
}
