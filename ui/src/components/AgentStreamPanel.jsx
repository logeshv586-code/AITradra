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
    <div className="flex flex-col" style={{ 
      maxHeight:'45%', 
      borderBottom: '1px solid rgba(255,255,255,0.04)',
      background: 'rgba(10, 14, 26, 0.60)',
      backdropFilter: 'blur(20px)',
    }}>
      {/* Header */}
      <div className="px-4 py-3 flex items-center justify-between flex-shrink-0 border-b border-white/5 bg-gradient-to-b from-white/[0.03] to-transparent">
        <div className="flex items-center gap-2.5">
          <div className="p-1.5 bg-indigo-500/10 rounded-lg border border-indigo-500/20">
            <Terminal size={12} className="text-indigo-400" />
          </div>
          <div>
            <span className="text-[10px] font-black uppercase tracking-[0.15em] text-white block">Claude Flow Stream</span>
            <span className="text-[8px] font-mono text-slate-500 tracking-wider">
              {completedSteps} OPS // {activeAgents.length} NODES
            </span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {isAnalyzing && (
            <>
              <span className="text-[8px] font-black text-indigo-400 animate-pulse uppercase tracking-widest">STREAMING</span>
              <div className="w-2 h-2 rounded-full bg-indigo-500 animate-ping" />
            </>
          )}
          {!isAnalyzing && logs.length > 0 && (
            <span className="text-[8px] font-black text-emerald-400 uppercase tracking-widest">COMPLETE</span>
          )}
        </div>
      </div>

      {/* Flow Progress */}
      {logs.length > 0 && (
        <div className="px-4 py-2 flex items-center gap-1 border-b border-white/[0.03] bg-black/20">
          {FLOW_STEPS.map((step, i) => {
            const isActive = logs.some(l => l.action === step);
            const isCurrent = logs[logs.length - 1]?.action === step;
            return (
              <React.Fragment key={step}>
                <div className={`px-2 py-1 rounded-md text-[7px] font-black tracking-wider transition-all ${
                  isCurrent ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-500/30'
                  : isActive ? 'bg-white/5 text-slate-400'
                  : 'text-slate-600'
                }`}>
                  {step}
                </div>
                {i < FLOW_STEPS.length - 1 && <ChevronRight size={8} className="text-slate-700" />}
              </React.Fragment>
            );
          })}
        </div>
      )}

      {/* Log Stream */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3 no-scrollbar" style={{ minHeight: 0 }}>
        {logs.length === 0
          ? (
            <div className="flex flex-col items-center justify-center py-8 gap-3 opacity-40">
              <Cpu size={24} className="text-slate-600" />
              <p className="text-[10px] font-mono font-black text-slate-600 uppercase tracking-widest">Awaiting pipeline trigger...</p>
            </div>
          )
          : logs.map(log => {
              const a = AGENTS[log.agent];
              if (!a) return null;
              const Icon = a.icon;
              return (
                <div key={log.id} className="animate-slide-in group">
                  <div className="flex items-center gap-2 mb-1">
                    <div className="w-5 h-5 rounded-md flex items-center justify-center"
                      style={{ background: `${a.color}15`, border: `1px solid ${a.color}25` }}>
                      <Icon size={10} style={{ color: a.color }} />
                    </div>
                    <span className="font-black font-mono text-[10px] tracking-wider" style={{ color: a.color }}>{a.name}</span>
                    <span className="py-0.5 px-2 rounded text-[7px] font-black tracking-wider border"
                      style={{
                        background: `${T.ai}10`,
                        borderColor: `${T.ai}20`,
                        color: T.aiLight,
                      }}>
                      {log.action}
                    </span>
                    <div className="flex-1" />
                    <span className="text-[8px] font-mono text-slate-600">
                      {new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                    </span>
                  </div>
                  <div className="font-mono text-[10px] pl-7 border-l-2 leading-relaxed text-slate-400 group-hover:text-slate-300 transition-colors"
                    style={{ borderColor: `${a.color}25` }}>
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
