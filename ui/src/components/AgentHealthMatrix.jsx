import React, { useState, useEffect } from "react";
import { Activity, Shield, AlertTriangle, CheckCircle, Zap } from "lucide-react";
import { API_BASE } from "../constants/config";

const AgentCard = ({ agent }) => {
  const isStuck = agent.status === "active" && (new Date() - new Date(agent.last_seen)) > 300000;
  const isError = agent.status === "error";
  
  const statusColor = isError ? "text-red-400" : (isStuck ? "text-amber-400" : (agent.status === "active" ? "text-emerald-400" : "text-slate-400"));
  const StatusIcon = isError ? AlertTriangle : (isStuck ? Activity : (agent.status === "active" ? Zap : CheckCircle));

  return (
    <div className="clay-card p-4 flex flex-col gap-3 min-w-[200px] flex-1">
      <div className="flex items-center justify-between">
        <span className="text-[10px] font-bold tracking-widest text-slate-400 uppercase font-mono">{agent.agent_name}</span>
        <StatusIcon size={14} className={statusColor + (agent.status === "active" ? " animate-pulse" : "")} />
      </div>
      
      <div className="text-sm font-mono font-bold text-white tracking-tight flex items-center justify-between">
        <span>STATUS:</span>
        <span className={statusColor}>{agent.status.toUpperCase()}</span>
      </div>
      
      <div className="flex flex-col gap-1">
        <div className="flex justify-between text-[8px] font-bold tracking-widest text-slate-500 uppercase">
          <span>LATENCY:</span>
          <span>{agent.latency_ms}ms</span>
        </div>
        <div className="w-full bg-white/5 h-1 rounded-full overflow-hidden">
          <div 
            className="h-full bg-indigo-500 transition-all duration-500" 
            style={{ width: `${Math.min(agent.latency_ms / 100, 100)}%` }}
          />
        </div>
      </div>
      
      <div className="mt-2 pt-2 border-t border-white/5 flex flex-col gap-1">
         <span className="text-[8px] text-slate-500 uppercase font-bold tracking-tighter">Current Task:</span>
         <span className="text-[9px] text-white font-mono truncate">{agent.current_task || "Standby..."}</span>
      </div>
    </div>
  );
};

export default function AgentHealthMatrix() {
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchStatus = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/mission/status`);
      const data = await res.json();
      setAgents(data.agents || []);
      setLoading(false);
    } catch (err) {
      console.error("Failed to fetch agent status:", err);
    }
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  if (loading && agents.length === 0) return <div className="animate-pulse text-indigo-400 font-mono text-[10px]">OBTAINING TELEMETRY...</div>;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-bold tracking-[0.2em] text-white uppercase font-mono flex items-center gap-2">
          <Shield size={14} className="text-indigo-400" />
          Agent Intelligence Matrix (14 Fleet)
        </h3>
        <span className="text-[10px] font-mono text-emerald-400 animate-pulse uppercase">Live Telemetry Link Active</span>
      </div>
      
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-7 gap-4">
        {agents.map((agent) => (
          <AgentCard key={agent.agent_name} agent={agent} />
        ))}
        {agents.length === 0 && (
           <div className="col-span-full py-12 text-center text-slate-500 font-mono text-[10px] uppercase tracking-widest border border-dashed border-white/10 rounded-2xl">
              Waiting for analysis pulse...
           </div>
        )}
      </div>
    </div>
  );
}
