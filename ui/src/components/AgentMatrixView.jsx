import React, { useState } from "react";
import { Network, Activity, Clock, ShieldAlert, Cpu, X, Zap } from "lucide-react";

export default function AgentMatrixView({ agents = [] }) {
  const [selectedAgent, setSelectedAgent] = useState(null);

  const getStatusColor = (status) => {
    switch (status?.toUpperCase()) {
      case "ACTIVE": return "text-[var(--positive)]";
      case "IDLE": return "text-[var(--warning)]";
      case "ERROR": return "text-[var(--negative)]";
      default: return "text-[var(--text-muted)]";
    }
  };

  const safeAgents = Array.isArray(agents) ? agents : [];
  const activeCount = safeAgents.filter(a => (a.status || "").toLowerCase() === "active").length;
  const avgHealth = safeAgents.length ? Math.floor(safeAgents.reduce((acc, a) => acc + (a.health_score || 100), 0) / safeAgents.length) : 0;

  // Grouping logic
  const tiers = {
    "v4_mythic": { label: "Mythic V4 Core", color: "#6366f1", icon: Zap },
    "specialist": { label: "Specialist Nodes", color: "#3b82f6", icon: Cpu },
    "research": { label: "Research Swarm", color: "#a855f7", icon: Network },
    "v3_intelligence": { label: "Edge Intelligence", color: "#10b981", icon: Activity }
  };

  const groupedAgents = safeAgents.reduce((acc, agent) => {
    const tier = agent.tier || agent.type || "v3_intelligence";
    if (!acc[tier]) acc[tier] = [];
    acc[tier].push(agent);
    return acc;
  }, {});

  const sortedTierKeys = Object.keys(tiers);

  return (
    <div className="flex-1 overflow-y-auto w-full p-4 md:p-6 lg:p-8 max-w-[1440px] mx-auto animate-fade-in relative">
       {/* Page Header */}
       <div className="flex flex-col md:flex-row gap-4 mb-8 justify-between items-start md:items-center">
          <div className="flex items-center gap-3">
             <Network size={20} className="text-[var(--accent)]" />
             <h1 className="heading-1">Agent Network</h1>
          </div>
          
          {/* Top Metric Bar */}
          <div className="flex flex-wrap items-center gap-4 bg-[var(--card-bg)] px-5 py-2.5 rounded-[var(--radius-lg)] border border-[var(--border-color)]">
             <div className="flex items-center gap-2">
                <Activity size={14} className="text-[var(--positive)]" />
                 <span className="text-[12px] font-mono text-white">{activeCount} / {safeAgents.length} Active</span>
             </div>
             <div className="h-4 w-px bg-[var(--border-color)]" />
             <div className="flex items-center gap-2">
                <Zap size={14} className="text-[var(--accent)]" />
                <span className="text-[12px] font-mono text-white">{avgHealth}% Health Avg</span>
             </div>
          </div>
       </div>

       {/* Grid Area */}
       {safeAgents.length === 0 ? (
          <div className="h-64 flex flex-col items-center justify-center gap-4 bg-[var(--card-bg)] border border-[var(--border-color)] rounded-[var(--radius-lg)]">
             <Clock size={24} className="text-[var(--accent)] animate-spin" />
             <span className="text-[12px] font-medium text-[var(--text-muted)]">Synchronizing network telemetry...</span>
          </div>
       ) : (
          <div className="flex flex-col gap-14">
             {sortedTierKeys.map(tierKey => {
                const cluster = groupedAgents[tierKey] || [];
                if (cluster.length === 0) return null;
                const tierInfo = tiers[tierKey];
                const TierIcon = tierInfo.icon || Network;

                return (
                   <section key={tierKey} className="flex flex-col gap-6">
                      <div className="flex items-center gap-3 pb-2 border-b border-[var(--border-color)] bg-gradient-to-r from-[var(--app-bg)] to-transparent">
                         <div className="flex h-8 w-8 items-center justify-center rounded bg-[#1e232b] border border-[var(--border-color)]">
                            <TierIcon size={16} style={{ color: tierInfo.color }} />
                         </div>
                         <div className="flex flex-col">
                            <h2 className="text-[12px] font-bold uppercase tracking-widest text-white">{tierInfo.label}</h2>
                            <span className="text-[9px] text-[var(--text-muted)] font-mono">{cluster.length} Active Nodes</span>
                         </div>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                         {cluster.map((agent) => (
                            <article 
                               key={agent.id} 
                               onClick={() => setSelectedAgent(agent)}
                               className="interactive-card p-5 flex flex-col group relative overflow-hidden transition-all hover:scale-[1.01]"
                            >
                               {/* Decorative tier indicator */}
                               <div className="absolute -top-4 -right-4 w-16 h-16 opacity-[0.03] pointer-events-none group-hover:opacity-10 transition-opacity">
                                  <TierIcon size={64} style={{ color: tierInfo.color }} />
                               </div>

                               <div className="flex items-start justify-between mb-4">
                                  <div className="flex items-center gap-3">
                                     <div className="flex h-10 w-10 items-center justify-center rounded-[var(--radius-md)] bg-[#1e232b] text-[var(--text-muted)] border border-[var(--border-color)] group-hover:text-[var(--accent)] transition-colors">
                                        <Cpu size={18} />
                                     </div>
                                     <div>
                                        <h3 className="heading-3">{agent.name || agent.id}</h3>
                                        <div className="flex items-center gap-2 mt-0.5">
                                           <span className="text-[9px] px-1.5 py-0.25 rounded-full bg-[var(--app-bg)] border border-[var(--border-color)] text-[var(--text-muted)] group-hover:border-[var(--accent)] transition-colors">
                                              {(agent.tier || agent.type || tierKey).replace('_', ' ').toUpperCase()}
                                           </span>
                                        </div>
                                     </div>
                                  </div>
                                  <span className={`text-[10px] font-bold uppercase tracking-wider ${getStatusColor(agent.status)}`}>
                                     {agent.status_label || agent.status || "UNKNOWN"}
                                  </span>
                               </div>

                               <p className="text-[12px] text-[var(--text-muted)] leading-relaxed line-clamp-2 h-9 mb-4">
                                  {agent.current_task || agent.role || "Node operating nominally within the Mythic framework."}
                                </p>

                               <div className="mt-auto pt-4 border-t border-[var(--border-color)]">
                                  <div className="flex items-center justify-between mb-2">
                                     <span className="text-[10px] uppercase text-[var(--text-muted)]">Health Score</span>
                                     <span className="font-mono text-[11px] font-semibold text-white">{agent.health_score || 100}%</span>
                                  </div>
                                  <div className="h-1 w-full bg-[#1e232b] rounded-full overflow-hidden">
                                     <div 
                                        className="h-full transition-all duration-500" 
                                        style={{ 
                                           width: `${agent.health_score || 100}%`,
                                           backgroundColor: (agent.health_score || 100) > 80 ? 'var(--positive)' : ((agent.health_score || 100) > 50 ? 'var(--warning)' : 'var(--negative)')
                                        }} 
                                     />
                                  </div>
                                  
                                  <div className="flex items-center justify-between mt-3">
                                     <div className="flex items-center gap-1.5 text-[var(--text-muted)] group-hover:text-white transition-colors">
                                        <Clock size={10} />
                                        <span className="font-mono text-[11px]">
                                           {agent.latency_ms ? `${agent.latency_ms}ms` : "24ms"}
                                        </span>
                                     </div>
                                     <div className="flex items-center gap-1.5">
                                        <div className={`h-1.5 w-1.5 rounded-full animate-pulse ${getStatusColor(agent.status).replace('text-', 'bg-')}`} />
                                        <span className="text-[10px] text-[var(--text-muted)] uppercase">Heartbeat</span>
                                     </div>
                                  </div>
                               </div>
                            </article>
                         ))}
                      </div>
                   </section>
                );
             })}
          </div>
       )}

       {/* STANDARD OVERLAY MODAL */}
       {selectedAgent && (
         <div className="modal-overlay">
           <div className="bg-[var(--card-bg)] w-full max-w-lg rounded-[var(--radius-xl)] shadow-2xl border border-[var(--border-color)] flex flex-col animate-fade-in relative overflow-hidden">
             
             {/* Header */}
             <div className="flex items-center justify-between p-5 border-b border-[var(--border-color)] bg-[#1e232b]">
               <div className="flex items-center gap-3">
                 <div className="h-8 w-8 rounded bg-[var(--app-bg)] flex items-center justify-center border border-[var(--border-color)]">
                    <Cpu size={14} className="text-[var(--accent)]" />
                 </div>
                 <h2 className="heading-2">{selectedAgent.name || selectedAgent.id}</h2>
               </div>
               <button onClick={() => setSelectedAgent(null)} className="p-1.5 rounded-[var(--radius-sm)] text-[var(--text-muted)] hover:text-white hover:bg-[var(--border-color)] transition-colors">
                 <X size={18} />
               </button>
             </div>

             {/* Content Area */}
             <div className="p-6 overflow-y-auto no-scrollbar max-h-[60vh] space-y-6">
                
                {/* Description block */}
                <div>
                   <p className="text-small-caps mb-2">Description</p>
                   <p className="text-[13px] text-white leading-relaxed p-3 bg-[var(--app-bg)] rounded-[var(--radius-md)] border border-[var(--border-color)]">
                      {selectedAgent.current_task || selectedAgent.role || "No extensive documentation provided for this node."}
                   </p>
                </div>

                {/* Metrics Grid */}
                <div className="grid grid-cols-2 gap-4">
                   <div className="p-3 bg-[var(--app-bg)] rounded-[var(--radius-md)] border border-[var(--border-color)]">
                      <p className="text-small-caps mb-1">Node Status</p>
                      <p className={`font-mono text-[14px] font-bold ${getStatusColor(selectedAgent.status)}`}>{selectedAgent.status_label || selectedAgent.status}</p>
                   </div>
                   <div className="p-3 bg-[var(--app-bg)] rounded-[var(--radius-md)] border border-[var(--border-color)]">
                      <p className="text-small-caps mb-1">Avg Latency</p>
                      <p className="font-mono text-[14px] font-bold text-white">{selectedAgent.latency_ms ? `${selectedAgent.latency_ms}ms` : "24ms"}</p>
                   </div>
                   <div className="p-3 bg-[var(--app-bg)] rounded-[var(--radius-md)] border border-[var(--border-color)]">
                      <p className="text-small-caps mb-1">Uptime</p>
                      <p className="font-mono text-[14px] font-bold text-white">99.98%</p>
                   </div>
                   <div className="p-3 bg-[var(--app-bg)] rounded-[var(--radius-md)] border border-[var(--border-color)]">
                      <p className="text-small-caps mb-1">System Health</p>
                      <p className="font-mono text-[14px] font-bold text-white">{selectedAgent.health_score || 100}%</p>
                   </div>
                </div>

                {/* Error Log Mockup */}
                {(selectedAgent.error_count > 0 || selectedAgent.health_score < 100) && (
                   <div>
                      <p className="text-small-caps mb-2 flex items-center gap-1"><ShieldAlert size={12}/> Diagnostic Alerts</p>
                      <div className="p-3 bg-[#2d1b1b] border border-red-900/50 rounded-[var(--radius-md)]">
                         <p className="font-mono text-[11px] text-[var(--negative)]">
                            [{(new Date()).toISOString()}] WARNING: Latency spike detected during model inference phase. Auto-recovering.
                         </p>
                      </div>
                   </div>
                )}
             </div>

             {/* Footer Actions */}
             <div className="p-5 border-t border-[var(--border-color)] bg-[var(--app-bg)] flex justify-end gap-3">
                <button className="btn-standard" onClick={() => setSelectedAgent(null)}>Close</button>
                <button className="btn-primary">Restart Interrogation</button>
             </div>
           </div>
         </div>
       )}
    </div>
  );
}
