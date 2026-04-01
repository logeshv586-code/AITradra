import React, { useRef, useEffect } from "react";
import { Terminal, ChevronRight, Activity, Cpu, Loader2 } from "lucide-react";
import { AGENTS, FLOW_STEPS } from "../data";

export default function AgentStreamPanel({ logs, isAnalyzing }) {
  const endRef = useRef(null);
  useEffect(() => { endRef.current?.scrollIntoView({ behavior:'smooth' }); }, [logs]);

  const activeAgents = [...new Set(logs.map(l => l.agent))];
  const completedSteps = logs.length;

  return (
    <div className="flex flex-col h-full relative overflow-hidden bg-black/20 backdrop-blur-3xl animate-fade-in group">
      {/* Precision Header */}
      <div className="px-5 py-4 flex items-center justify-between flex-shrink-0 border-b border-white/[0.08] bg-white/[0.02]">
        <div className="flex items-center gap-4">
          <div className="w-8 h-8 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center transition-all duration-120 group-hover:bg-indigo-500/20">
            <Terminal size={14} className="text-indigo-400" />
          </div>
          <div className="flex flex-col">
            <span className="text-[11px] font-bold uppercase tracking-widest text-white leading-none">Reasoning Stream</span>
            <span className="text-[9px] font-mono text-slate-500 tracking-[0.2em] uppercase mt-1.5 tabular-nums">
              {completedSteps} OPS // {activeAgents.length} NODES
            </span>
          </div>
        </div>
        <div>
          {isAnalyzing && (
            <div className="flex items-center gap-2 px-2 py-0.5 bg-indigo-500/5 border border-indigo-500/20 rounded-md">
              <Loader2 size={10} className="text-indigo-400 animate-spin" />
              <span className="text-[8px] font-bold text-indigo-400 uppercase tracking-widest leading-none">PULSE</span>
            </div>
          )}
        </div>
      </div>

      {/* Logic Sequence - Institutional Toggles */}
      {logs.length > 0 && (
        <div className="px-4 py-2.5 flex items-center gap-2 border-b border-white/[0.06] bg-black/20 overflow-x-auto no-scrollbar">
          {FLOW_STEPS.map((step, i) => {
            const isActive = logs.some(l => l.action === step);
            const isCurrent = logs[logs.length - 1]?.action === step;
            return (
              <React.Fragment key={step}>
                <div className={`px-2 py-1 rounded-md text-[8px] font-bold tracking-widest transition-all duration-120 whitespace-nowrap border ${
                  isCurrent ? 'bg-indigo-600 text-white border-indigo-500 shadow-lg shadow-indigo-900/20'
                  : isActive ? 'bg-indigo-500/5 text-indigo-400 border-indigo-500/20'
                  : 'text-slate-600 border-transparent'
                }`}>
                  {step}
                </div>
                {i < FLOW_STEPS.length - 1 && <div className="w-1 h-[1px] bg-white/10 shrink-0" />}
              </React.Fragment>
            );
          })}
        </div>
      )}

      {/* Trace Buffer */}
      <div className="flex-1 overflow-y-auto p-5 space-y-4 no-scrollbar relative z-10 scroll-smooth" style={{ minHeight: 0 }}>
        {logs.length === 0
          ? (
            <div className="flex flex-col items-center justify-center py-20 gap-4 opacity-40 h-full">
              <Cpu size={24} className="text-slate-700 animate-float" />
              <p className="text-[9px] font-mono font-bold text-slate-800 uppercase tracking-widest">Awaiting Command Input...</p>
            </div>
          )
          : logs.map((log, li) => {
              const a = AGENTS[log.agent];
              if (!a) return null;
              const Icon = a.icon;
              return (
                <div key={log.id || li} className="animate-slide-up group/item border-l border-white/[0.06] hover:border-indigo-500/40 pl-4 py-1 transition-all duration-120">
                  <div className="flex items-center gap-3 mb-1.5">
                    <div className="w-5 h-5 rounded flex items-center justify-center bg-white/[0.03] border border-white/[0.06]">
                      <Icon size={10} style={{ color: a.color }} />
                    </div>
                    <span className="font-bold font-mono text-[10px] tracking-widest uppercase" style={{ color: a.color }}>{a.name}</span>
                    <span className="text-[8px] font-mono text-slate-700 ml-auto tabular-nums">
                      {new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                    </span>
                  </div>
                  <div className="font-mono text-[10px] leading-relaxed text-slate-500 group-hover/item:text-slate-300 transition-colors">
                    <span className="text-indigo-500/30 mr-2">/</span>
                    {log.text}
                  </div>
                </div>
              );
            })
        }
        <div ref={endRef} className="h-4" />
      </div>
    </div>
  );
}
