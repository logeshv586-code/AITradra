import React, { useRef, useEffect } from "react";
import { Terminal, ChevronRight, Activity, Cpu } from "lucide-react";
import { T } from "../theme";
import { AGENTS, FLOW_STEPS } from "../data";

export default function AgentStreamPanel({ logs, isAnalyzing }) {
  const endRef = useRef(null);
  useEffect(() => { endRef.current?.scrollIntoView({ behavior:'smooth' }); }, [logs]);

  const activeAgents = [...new Set(logs.map(l => l.agent))];
  const completedSteps = logs.length;

  return (
    <div className="flex flex-col border-l border-white/5 h-[45%] relative overflow-hidden" style={{ 
      background: 'rgba(10, 14, 26, 0.45)',
      backdropFilter: 'blur(32px)',
    }}>

      {/* Header */}
      <div className="px-6 py-4 flex items-center justify-between flex-shrink-0 border-b border-white/5 relative z-10 bg-black/20">
        <div className="flex items-center gap-4">
          <div className="w-8 h-8 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center">
            <Terminal size={14} className="text-indigo-400" />
          </div>
          <div>
            <span className="text-[11px] font-black uppercase tracking-[0.2em] text-white block">Reasoning Trace</span>
            <span className="text-[9px] font-mono text-slate-500 tracking-widest uppercase mt-0.5">
              {completedSteps} OPS_TOTAL // {activeAgents.length} NODES_ACTIVE
            </span>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {isAnalyzing && (
            <div className="flex items-center gap-2 px-3 py-1 bg-indigo-500/10 border border-indigo-500/30 rounded-full">
              <span className="text-[9px] font-black text-indigo-400 animate-pulse uppercase tracking-[0.1em]">STREAMING</span>
              <div className="w-1.5 h-1.5 rounded-full bg-indigo-500 animate-ping" />
            </div>
          )}
        </div>
      </div>

      {/* Flow Progress */}
      {logs.length > 0 && (
        <div className="px-5 py-3 flex items-center gap-2 border-b border-white/[0.05] bg-black/40 overflow-x-auto no-scrollbar relative z-10">
          {FLOW_STEPS.map((step, i) => {
            const isActive = logs.some(l => l.action === step);
            const isCurrent = logs[logs.length - 1]?.action === step;
            return (
              <React.Fragment key={step}>
                <div className={`px-3 py-1.5 rounded-lg text-[8px] font-black tracking-[0.15em] transition-all whitespace-nowrap ${
                  isCurrent ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-500/40 scale-105'
                  : isActive ? 'bg-indigo-500/10 text-indigo-300 border border-indigo-500/20'
                  : 'text-slate-600 border border-transparent'
                }`}>
                  {step}
                </div>
                {i < FLOW_STEPS.length - 1 && <ChevronRight size={10} className="text-slate-800 flex-shrink-0" />}
              </React.Fragment>
            );
          })}
        </div>
      )}

      {/* Log Stream */}
      <div className="flex-1 overflow-y-auto p-5 space-y-4 no-scrollbar relative z-10" style={{ minHeight: 0 }}>
        {logs.length === 0
          ? (
            <div className="flex flex-col items-center justify-center py-12 gap-4 opacity-50 h-full">
              <Cpu size={32} className="text-slate-800 animate-float" />
              <p className="text-[10px] font-mono font-black text-slate-600 uppercase tracking-[0.3em]">Awaiting synaptic trigger...</p>
            </div>
          )
          : logs.map(log => {
              const a = AGENTS[log.agent];
              if (!a) return null;
              const Icon = a.icon;
              return (
                <div key={log.id} className="animate-slide-in group border-l-2 pl-5 py-2 transition-all hover:bg-white/[0.03] rounded-r-xl border-white/10 hover:border-indigo-500/50">
                  <div className="flex items-center gap-3 mb-2">
                    <div className="w-6 h-6 rounded-lg flex items-center justify-center bg-white/5 border border-white/10">
                      <Icon size={12} style={{ color: a.color }} />
                    </div>
                    <span className="font-bold font-mono text-[11px] tracking-widest uppercase opacity-80" style={{ color: a.color }}>{a.name}</span>
                    <span className="text-[9px] font-mono text-slate-600 ml-auto tabular-nums">
                      {new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                    </span>
                  </div>
                  <div className="font-mono text-[11px] leading-relaxed text-slate-400 group-hover:text-slate-200 transition-colors">
                    <span className="text-indigo-500/50 mr-2">»</span>
                    {log.text}
                  </div>
                </div>
              );
            })
        }
        <div ref={endRef}/>
      </div>
    </div>
  );
}
