import React, { useRef, useEffect } from "react";
import { Terminal } from "lucide-react";
import { T } from "../theme";
import { AGENTS } from "../data";

export default function AgentStreamPanel({ logs, isAnalyzing }) {
  const endRef = useRef(null);
  useEffect(() => { endRef.current?.scrollIntoView({ behavior:'smooth' }); }, [logs]);

  return (
    <div className="flex flex-col border-b border-white/10 bg-black/40 backdrop-blur-md" style={{ maxHeight:'45%' }}>
      <div className="px-4 py-3 flex items-center justify-between flex-shrink-0 border-b border-white/5 bg-white/[0.02]">
        <div className="flex items-center gap-2">
          <Terminal size={14} style={{ color: T.ai }} />
          <span className="text-[10px] font-bold uppercase tracking-widest text-slate-300">Claude Flow Stream</span>
        </div>
        {isAnalyzing && <div className="w-2 h-2 rounded-full animate-pulse" style={{ background: T.buy, boxShadow: `0 0 10px ${T.buy}` }}/>}
      </div>
      <div className="flex-1 overflow-y-auto p-4 space-y-4" style={{ minHeight: 0 }}>
        {logs.length === 0
          ? <p className="text-xs italic text-slate-500">Awaiting pipeline trigger...</p>
          : logs.map(log => {
              const a = AGENTS[log.agent];
              const Icon = a.icon;
              return (
                <div key={log.id} className="text-xs animate-slide-in">
                  <div className="flex items-center gap-2 mb-1.5">
                    <Icon size={12} style={{ color: a.color }} />
                    <span className="font-bold font-mono tracking-wide" style={{ color: a.color, textShadow:`0 0 8px ${a.color}80` }}>{a.name}</span>
                    <span className="text-[9px] px-1.5 py-0.5 rounded-md font-bold tracking-wider" style={{ background:`${T.ai}20`, color:T.text, border:`1px solid ${T.ai}50` }}>{log.action}</span>
                  </div>
                  <div className="font-mono text-[11px] pl-5 border-l-2 leading-relaxed text-slate-300"
                    style={{ borderColor: `${a.color}40` }}>{log.text}</div>
                </div>
              );
            })
        }
        <div ref={endRef}/>
      </div>
    </div>
  );
}
