import React from "react";
import { Layers, Sparkles, AlertTriangle } from "lucide-react";
import { T } from "../theme";
import { AGENTS } from "../data";
import { GlassCard } from "./Shared";

export default function AgentMatrixView() {
  return (
    <div className="flex-1 p-8 overflow-y-auto">
      <div className="max-w-6xl mx-auto space-y-8">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-bold flex items-center gap-3 text-white text-shadow-glow">
            <Layers size={24} style={{ color: T.ai }} /> Agent Matrix & Health
          </h2>
          <span className="text-xs px-3 py-1.5 rounded-lg flex items-center gap-2 font-bold"
            style={{ background:`${T.buy}15`, color:T.buy, border:`1px solid ${T.buy}40`, boxShadow:`0 0 15px ${T.buy}30` }}>
            <Sparkles size={14} /> Self-Improvement Engine Active
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {Object.entries(AGENTS).map(([key, a]) => {
            const Icon = a.icon;
            const isWarn = a.status === 'Retraining' || a.status === 'Learning';
            return (
              <GlassCard key={key} interactive glowCol={isWarn ? T.warn : a.color} className="p-6">
                <div className="absolute top-0 left-0 w-full h-1" style={{ background: isWarn ? T.warn : a.color, boxShadow: `0 0 10px ${isWarn ? T.warn : a.color}` }}/>
                <div className="flex justify-between items-start mb-5">
                  <div className="flex items-center gap-3">
                    <div className="p-2.5 rounded-xl" style={{ background: `${a.color}15`, border: `1px solid ${a.color}40` }}>
                      <Icon size={20} style={{ color: a.color, filter: `drop-shadow(0 0 5px ${a.color})` }} />
                    </div>
                    <div>
                      <div className="font-bold text-base text-white tracking-wide">{a.name}</div>
                      <div className="text-[10px] text-slate-400 uppercase tracking-widest mt-0.5">Claude Flow Node</div>
                    </div>
                  </div>
                  <span className={`text-[10px] px-2.5 py-1 rounded font-bold tracking-wide ${isWarn ? 'animate-pulse' : ''}`}
                    style={{ background:`${isWarn?T.warn:T.buy}15`, color:isWarn?T.warn:T.buy, border:`1px solid ${isWarn?T.warn:T.buy}40` }}>
                    {a.status}
                  </span>
                </div>
                <p className="text-xs mb-5 leading-relaxed text-slate-300">{a.desc}</p>
                <div className="flex justify-between text-xs mb-5 bg-black/30 p-3 rounded-lg border border-white/5">
                  <div>
                    <div className="text-[10px] text-slate-400 mb-1 uppercase tracking-wider">Accuracy</div>
                    <div className="font-mono font-bold text-base" style={{ color: a.acc >= 70 ? T.buy : T.warn, textShadow: `0 0 10px ${a.acc >= 70 ? T.buy : T.warn}60` }}>{a.acc}%</div>
                  </div>
                  <div>
                    <div className="text-[10px] text-slate-400 mb-1 uppercase tracking-wider">Tasks</div>
                    <div className="font-mono font-bold text-base text-white">{a.tasks.toLocaleString()}</div>
                  </div>
                  <div>
                    <div className="text-[10px] text-slate-400 mb-1 uppercase tracking-wider">Target</div>
                    <div className="font-mono font-bold text-base text-white">70%</div>
                  </div>
                </div>
                {isWarn && (
                  <div className="p-2.5 rounded-lg text-[10px] flex items-start gap-2" style={{ background:`${T.warn}10`, border:`1px solid ${T.warn}30`, color: T.warn }}>
                    <AlertTriangle size={14} className="flex-shrink-0" />
                    <span className="leading-snug">Accuracy threshold missed. Queuing prompt optimization & weight adjustment.</span>
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
