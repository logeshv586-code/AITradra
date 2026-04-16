import React from 'react';
import { Activity, Zap, Server, ShieldCheck, AlertTriangle } from 'lucide-react';

export default function DiagnosticView({ agents }) {
  const issues = agents?.filter(a => a.health_score < 100 || a.status === "ERROR") || [];

  return (
    <div className="flex flex-col h-full bg-[var(--card-bg)]">
       {/* Diagnostic Summary */}
       <div className="p-5 grid grid-cols-2 lg:grid-cols-4 gap-4 border-b border-[var(--border-color)]">
          {[
             { l: "CPU Load", v: "42%", k: "Nominal" },
             { l: "Memory", v: "14GB", k: "Nominal" },
             { l: "API Requests", v: "1.2k/m", k: "Elevated" },
             { l: "DB Cache", v: "98%", k: "Optimal" },
          ].map((d, i) => (
             <div key={i} className="flex flex-col gap-1 p-3 bg-[#1e232b] rounded-[var(--radius-md)] border border-[var(--border-color)]">
                <span className="text-[11px] text-[var(--text-muted)] font-medium uppercase tracking-wider">{d.l}</span>
                <span className="font-mono text-[16px] text-white font-bold">{d.v}</span>
             </div>
          ))}
       </div>

       {/* Issue Feed */}
       <div className="flex-1 p-5 overflow-y-auto no-scrollbar">
          {issues.length > 0 ? (
             <div className="flex flex-col gap-3">
                {issues.map(iss => (
                   <div key={iss.id} className="flex items-start gap-3 p-3 bg-[#2d1b1b] border border-red-900/50 rounded-[var(--radius-md)]">
                      <AlertTriangle size={16} className="text-[var(--negative)] shrink-0 mt-0.5" />
                      <div className="flex flex-col gap-1">
                         <span className="text-[12px] font-semibold text-[var(--negative)]">
                            {iss.name} - Performance Suboptimal
                         </span>
                         <span className="text-[11px] text-[var(--text-muted)] font-mono">
                            Diagnostic ping returned {iss.latency || "timeout"}. Health is at {iss.health_score}%.
                         </span>
                      </div>
                   </div>
                ))}
             </div>
          ) : (
             <div className="flex flex-col items-center justify-center p-8 text-center bg-[#10b98110] border border-[#10b98130] rounded-[var(--radius-md)]">
                <ShieldCheck size={32} className="text-[var(--positive)] mb-3" />
                <span className="text-[13px] font-medium text-white mb-1">System Nominal</span>
                <span className="text-[11px] text-[var(--text-muted)]">All diagnostic checks pass across cluster nodes.</span>
             </div>
          )}
       </div>
    </div>
  );
}
