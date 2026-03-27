import React from "react";
import { Layers, Sparkles, AlertTriangle, Activity, Zap, Cpu } from "lucide-react";
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
    <div className="flex-1 p-8 overflow-y-auto no-scrollbar">
      <div className="max-w-6xl mx-auto space-y-8 animate-fade-in">
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <h2 className="text-2xl font-black flex items-center gap-3 text-white text-shadow-glow tracking-tight">
              <div className="p-2 rounded-xl animate-cyber-pulse" style={{
                background: 'linear-gradient(135deg, rgba(99,102,241,0.25), rgba(99,102,241,0.10))',
                border: '1px solid rgba(99,102,241,0.35)'
              }}>
                <Layers size={22} style={{ color: T.ai }} />
              </div>
              AGENT MATRIX <span className="text-indigo-500/50">&</span> HEALTH
            </h2>
            <div className="flex items-center gap-4 text-[10px] text-slate-500 font-bold tracking-[0.2em] px-1">
              <span className="flex items-center gap-1.5"><Activity size={10} className="text-indigo-400"/> AVG_ACCURACY: {avgAcc}%</span>
              <span className="w-1 h-1 rounded-full bg-slate-700"/>
              <span className="flex items-center gap-1.5"><Zap size={10} className="text-yellow-400"/> TOTAL_THROUGHPUT: {totalOps.toLocaleString()} OPS/S</span>
            </div>
          </div>
          <span className="clay-badge py-2 px-4 shadow-lg animate-soft-pulse" style={{
            background: `linear-gradient(135deg, ${T.buy}15, ${T.buy}05)`,
            color: T.buy,
            borderColor: `${T.buy}30`,
            borderRadius: '12px'
          }}>
            <Sparkles size={14} className="animate-spin-slow" /> SELF-IMPROVEMENT ENGINE ACTIVE
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {displayAgents.map((a) => {
            const Icon = a.icon;
            const isWarn = a.status === 'Retraining' || a.status === 'Learning' || a.status === 'Standby';
            const isActive = a.status === 'Active';
            const accentCol = isWarn ? T.warn : a.color;
            
            return (
              <GlassCard key={a.id} interactive glowCol={accentCol} className={`p-6 ${isActive ? 'animate-cyber-pulse' : ''}`}>
                {/* Accent bar with scanning effect */}
                <div className="absolute top-0 left-0 w-full h-1 overflow-hidden rounded-t-[20px]">
                  <div className="w-full h-full" style={{ background: `linear-gradient(90deg, transparent, ${accentCol}, transparent)` }}/>
                  <div className="absolute inset-0 w-1/3 h-full animate-shimmer" style={{ background: `linear-gradient(90deg, transparent, white, transparent)` }}/>
                </div>
                
                <div className="flex justify-between items-start mb-6">
                  <div className="flex items-center gap-3">
                    <div className="p-2.5 rounded-2xl relative" style={{ 
                      background: `linear-gradient(135deg, ${a.color}20, ${a.color}10)`,
                      border: `1px solid ${a.color}35`,
                      boxShadow: `0 0 15px ${a.color}15`
                    }}>
                      <Icon size={22} style={{ color: a.color, filter: `drop-shadow(0 0 8px ${a.color})` }} />
                      {isActive && <div className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-green-500 rounded-full border-2 border-[#0a0e1a] animate-pulse"/>}
                    </div>
                    <div>
                      <div className="font-black text-base text-white tracking-wide uppercase">{a.name}</div>
                      <div className="flex items-center gap-2">
                        <div className="text-[9px] text-slate-500 font-bold uppercase tracking-widest">CLAUDE_FLOW_NODE</div>
                        <FrequencyVisualizer color={a.color} />
                      </div>
                    </div>
                  </div>
                  <span className={`clay-badge text-[9px] px-2.5 py-1 ${isWarn ? 'animate-soft-pulse' : ''}`}
                    style={{ 
                      background: isWarn ? `${T.warn}15` : `${T.buy}10`,
                      color: isWarn ? T.warn : T.buy,
                      borderColor: isWarn ? `${T.warn}30` : `${T.buy}25`,
                      letterSpacing: '0.1em'
                    }}>
                    {a.status.toUpperCase()}
                  </span>
                </div>
                
                <div className="relative mb-5">
                  <p className="text-[11px] leading-relaxed text-slate-400 font-medium px-1 border-l-2" style={{ borderColor: `${a.color}30` }}>
                    {a.desc}
                  </p>
                </div>
                
                {/* Visual Math / Data health */}
                <div className="space-y-4 mb-6">
                  <div className="space-y-1.5">
                    <div className="flex justify-between items-end px-1">
                      <span className="text-[9px] font-black text-slate-500 tracking-tighter uppercase">Confidence Matrix</span>
                      <span className="font-mono font-black text-xs" style={{ color: a.acc >= 70 ? T.buy : T.warn }}>{a.acc}%</span>
                    </div>
                    <div className="clay-progress-track h-1.5 bg-black/40 shadow-inner">
                      <div className="clay-progress-fill relative overflow-hidden h-full" 
                        style={{ 
                          width: `${a.acc}%`, 
                          background: `linear-gradient(90deg, ${a.color}80, ${a.color})`,
                          boxShadow: `0 0 10px ${a.color}40`
                        }}>
                        <div className="absolute inset-0 animate-shimmer" style={{ background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent)' }}/>
                      </div>
                    </div>
                  </div>
 
                  <div className="grid grid-cols-2 gap-3">
                    <div className="clay-inset p-3 bg-black/20 flex flex-col justify-center">
                      <span className="text-[8px] text-slate-500 font-black uppercase tracking-widest mb-1">Throughput</span>
                      <div className="flex items-end gap-1.5">
                        <span className="font-mono font-bold text-sm text-white">{a.tasks.toLocaleString()}</span>
                        <span className="text-[8px] text-slate-600 mb-0.5 font-bold">OPS/S</span>
                      </div>
                    </div>
                    <div className="clay-inset p-3 bg-black/20 flex flex-col justify-center">
                      <span className="text-[8px] text-slate-500 font-black uppercase tracking-widest mb-1">Critique Pass</span>
                      <div className="flex items-center gap-2">
                        <div className="flex gap-0.5">
                          {[1,2,3,4].map(i => (
                            <div key={i} className={`w-1.5 h-1.5 rounded-full ${i <= 3 ? (isWarn ? 'bg-amber-500' : 'bg-indigo-500') : 'bg-slate-800'}`}/>
                          ))}
                        </div>
                        <span className="text-[9px] text-slate-400 font-bold">75%</span>
                      </div>
                    </div>
                  </div>
                </div>
                
                {isWarn && (
                    <div className="clay-badge p-3 w-full border-dashed flex items-center gap-3 mt-auto" style={{ 
                      background: `rgba(251, 191, 36, 0.05)`,
                      borderColor: `${T.warn}40`,
                      color: T.warn,
                      borderRadius: '12px'
                    }}>
                      <div className="p-1.5 bg-amber-500/20 rounded-lg animate-pulse">
                        <AlertTriangle size={14} />
                      </div>
                      <span className="text-[9px] leading-tight font-bold tracking-tight uppercase">Accuracy threshold parity missed. Refactoring synaptic weights.</span>
                    </div>
                  )}
              </GlassCard>
            );
          })}
        </div>
      </div>
    </div>
  );
}
