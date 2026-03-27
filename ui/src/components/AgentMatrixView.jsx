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
              <div className="p-3 rounded-2xl animate-cyber-pulse clay-organic" style={{
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
          <div className="hidden lg:flex gap-3">
             <div className="clay-badge py-2.5 px-5 shadow-xl bg-indigo-500/10 border-indigo-500/20 text-indigo-400">
               <Cpu size={14} /> CLAUDE_SONNET_3.5_CORE
             </div>
             <div className="clay-badge py-2.5 px-5 shadow-xl animate-soft-pulse" style={{ background: `${T.buy}15`, color: T.buy, borderColor: `${T.buy}30` }}>
               <Sparkles size={14} className="animate-spin-slow" /> AUTONOMOUS_MODE
             </div>
          </div>
        </div>

        <div className="grid-bento">
          {displayAgents.map((a) => {
            const Icon = a.icon;
            const isWarn = a.status === 'Retraining' || a.status === 'Learning' || a.status === 'Standby';
            const isActive = a.status === 'Active';
            const accentCol = isWarn ? T.warn : a.color;
            
            // Bento Area Assignment
            let bentoClass = "";
            if (a.id === 'think') bentoClass = "bento-main";
            else if (a.id === 'explain') bentoClass = "bento-wide";
            else if (a.id === 'batch') bentoClass = "bento-tall";

            return (
              <GlassCard key={a.id} interactive glowCol={accentCol} 
                className={`p-8 glass-holo flex flex-col ${bentoClass} ${isActive ? 'animate-cyber-pulse-subtle' : ''}`}>
                
                <div className="flex justify-between items-start mb-auto">
                  <div className="flex items-center gap-4">
                    <div className="p-4 rounded-2xl relative clay-organic" style={{ 
                      background: `linear-gradient(135deg, ${a.color}25, ${a.color}10)`,
                      border: `1px solid ${a.color}40`,
                      boxShadow: `0 8px 24px ${a.color}20`
                    }}>
                      <Icon size={a.id === 'think' ? 32 : 24} style={{ color: a.color, filter: `drop-shadow(0 0 12px ${a.color})` }} />
                      {isActive && <div className="absolute -top-1.5 -right-1.5 w-3.5 h-3.5 bg-green-500 rounded-full border-4 border-[#0a0e1a] animate-pulse"/>}
                    </div>
                    <div>
                      <div className={`font-black tracking-tight text-white uppercase ${a.id === 'think' ? 'text-2xl' : 'text-lg'}`}>{a.name}</div>
                      <div className="flex items-center gap-3 mt-1 text-[10px] text-slate-500 font-bold tracking-widest uppercase">
                        <span>NODE_v3.1</span>
                        <FrequencyVisualizer color={a.color} />
                      </div>
                    </div>
                  </div>
                  <span className={`clay-badge text-[10px] px-3.5 py-1.5 ${isWarn ? 'animate-soft-pulse' : ''}`}
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
                    <div className="clay-progress-track h-2 bg-black/50 shadow-inner">
                      <div className="clay-progress-fill relative overflow-hidden h-full" 
                        style={{ 
                          width: `${a.acc}%`, 
                          background: `linear-gradient(90deg, ${a.color}90, ${a.color})`,
                        }}>
                        <div className="absolute inset-0 animate-shimmer" style={{ background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent)' }}/>
                      </div>
                    </div>
                  </div>
  
                  <div className={`grid gap-4 ${a.id === 'think' ? 'grid-cols-3' : 'grid-cols-2'}`}>
                    <div className="clay-inset p-4 flex flex-col justify-center gap-1">
                      <span className="text-[9px] text-slate-500 font-black uppercase tracking-widest">Throughput</span>
                      <div className="flex items-end gap-2">
                        <span className="font-mono font-bold text-lg text-white leading-none">{a.tasks.toLocaleString()}</span>
                        <span className="text-[9px] text-slate-600 font-black">OPS</span>
                      </div>
                    </div>
                    <div className="clay-inset p-4 flex flex-col justify-center gap-1">
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
                       <div className="clay-inset p-4 flex flex-col justify-center gap-1">
                        <span className="text-[9px] text-slate-500 font-black uppercase tracking-widest">Neural Link</span>
                        <div className="text-xs text-indigo-400 font-black animate-pulse">ESTABLISHED</div>
                      </div>
                    )}
                  </div>
                </div>
              </GlassCard>
            );
          })}
        </div>
      </div>
    </div>
  );
}
