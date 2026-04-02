import React, { useMemo, useState } from "react";
import {
  Activity,
  AlertTriangle,
  ChevronRight,
  Cpu,
  Layers,
  Shield,
  Sparkles,
  X,
  Zap,
} from "lucide-react";
import { AGENTS } from "../data";

const STATUS_STYLES = {
  active: {
    label: "ACTIVE",
    chip: "border-emerald-400/20 bg-emerald-500/10 text-emerald-300",
  },
  idle: {
    label: "ONLINE",
    chip: "border-sky-400/20 bg-sky-500/10 text-sky-300",
  },
  stale: {
    label: "STALE",
    chip: "border-amber-400/20 bg-amber-500/10 text-amber-200",
  },
  error: {
    label: "ERROR",
    chip: "border-red-400/20 bg-red-500/10 text-red-300",
  },
  standby: {
    label: "NO DATA",
    chip: "border-white/10 bg-white/[0.03] text-slate-400",
  },
};

const TIER_LABELS = {
  v3_intelligence: "V3 Intelligence",
  v4_mythic: "V4 Mythic",
  specialist: "Specialist",
  research: "Research",
};

const FALLBACK_META = Object.fromEntries(
  Object.entries(AGENTS).map(([id, value]) => [
    id,
    {
      color: value.color,
      icon: value.icon,
      desc: value.desc,
      tierLabel: value.tier,
    },
  ]),
);

function metricTone(score = 0) {
  if (score >= 85) return "bg-emerald-500/80";
  if (score >= 65) return "bg-sky-500/80";
  if (score >= 45) return "bg-amber-400/80";
  return "bg-red-500/80";
}

export default function AgentMatrixView({ agentsStatus = [] }) {
  const [selectedAgent, setSelectedAgent] = useState(null);

  const displayAgents = useMemo(() => {
    if (!agentsStatus.length) {
      return Object.entries(AGENTS).map(([id, value]) => ({
        id,
        name: value.name,
        color: value.color,
        icon: value.icon,
        role: value.desc,
        type: value.tier,
        health_score: value.acc,
        status: value.status?.toLowerCase() === "active" ? "active" : "standby",
        status_label: value.status?.toUpperCase() || "STANDBY",
        freshness_label: "Awaiting heartbeat",
        latency_ms: 0,
        error_count: 0,
        cadence_hours: 24,
      }));
    }

    return agentsStatus.map((agent) => {
      const meta = FALLBACK_META[agent.id] || {};
      return {
        ...agent,
        color: meta.color || "#818cf8",
        icon: meta.icon || Cpu,
        role: agent.role || meta.desc || "Agent heartbeat available.",
        type_label: TIER_LABELS[agent.type] || "Agent",
      };
    });
  }, [agentsStatus]);

  const totals = useMemo(() => {
    const active = displayAgents.filter((agent) => agent.status === "active").length;
    const stale = displayAgents.filter((agent) => agent.status === "stale").length;
    const errors = displayAgents.filter((agent) => agent.status === "error").length;
    const avgHealth =
      displayAgents.length > 0
        ? Math.round(displayAgents.reduce((sum, agent) => sum + (agent.health_score || 0), 0) / displayAgents.length)
        : 0;

    return { active, stale, errors, avgHealth };
  }, [displayAgents]);

  const orderedAgents = useMemo(() => {
    const priority = { error: 0, stale: 1, active: 2, idle: 3, standby: 4 };
    return [...displayAgents].sort((a, b) => {
      const statusDelta = (priority[a.status] ?? 9) - (priority[b.status] ?? 9);
      if (statusDelta !== 0) return statusDelta;
      return (b.health_score || 0) - (a.health_score || 0);
    });
  }, [displayAgents]);

  return (
    <div className="flex-1 overflow-y-auto no-scrollbar page-padding">
      <div className="content-max-w space-y-6 md:space-y-10 animate-fade-in">
        <div className="flex flex-col gap-6 border-b border-white/[0.08] pb-6 md:flex-row md:items-end md:justify-between">
          <div className="space-y-4">
            <div className="flex items-center gap-4 md:gap-6">
              <div className="flex h-11 w-11 items-center justify-center rounded-lg border border-indigo-500/20 bg-indigo-500/10 shadow-sm">
                <Layers size={22} className="text-indigo-400" />
              </div>
              <div>
                <h1 className="text-xl font-bold uppercase tracking-tight text-white md:text-2xl">
                  Agent Matrix
                </h1>
                <p className="mt-1 text-[10px] font-mono uppercase tracking-[0.22em] text-slate-500">
                  Live heartbeats, daily freshness, and error visibility
                </p>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-3 text-[9px] font-bold uppercase tracking-[0.2em] text-slate-500">
              <span className="flex items-center gap-2">
                <Activity size={10} className="text-emerald-400/70" /> {totals.active} active
              </span>
              <span className="flex items-center gap-2">
                <Zap size={10} className="text-indigo-400/70" /> {totals.avgHealth}% avg health
              </span>
              <span className="flex items-center gap-2">
                <AlertTriangle size={10} className="text-amber-300/70" /> {totals.stale} stale
              </span>
              <span className="flex items-center gap-2">
                <Shield size={10} className="text-red-300/70" /> {totals.errors} errors
              </span>
            </div>
          </div>

          <div className="flex gap-3">
            <div className="flex items-center gap-2 rounded-md border border-white/[0.08] bg-white/[0.02] px-4 py-2 text-[9px] font-mono tracking-widest text-slate-400">
              <Cpu size={12} /> LIVE_HEARTBEATS
            </div>
            <button className="skeuo-button px-5 py-2 text-[9px] gap-2">
              <Sparkles size={12} className="text-indigo-400" /> DAILY_REFRESH
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3 md:gap-6">
          {orderedAgents.map((agent) => {
            const Icon = agent.icon || Cpu;
            const statusStyle = STATUS_STYLES[agent.status] || STATUS_STYLES.standby;
            const healthScore = Math.round(agent.health_score || 0);

            return (
              <button
                key={agent.id}
                type="button"
                onClick={() => setSelectedAgent(agent)}
                className="group glass-card interactive flex flex-col gap-6 p-5 text-left md:p-6"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-center gap-4">
                    <div
                      className="flex h-11 w-11 items-center justify-center rounded-lg border transition-all duration-150 group-hover:scale-[1.03]"
                      style={{
                        background: `${agent.color}10`,
                        borderColor: `${agent.color}22`,
                        color: agent.color,
                      }}
                    >
                      <Icon size={20} />
                    </div>
                    <div className="space-y-1">
                      <div className="text-[14px] font-bold uppercase tracking-tight text-white">{agent.name}</div>
                      <div className="text-[8px] font-bold uppercase tracking-[0.16em] text-slate-500">
                        {agent.type_label || TIER_LABELS[agent.type] || "Agent"}
                      </div>
                    </div>
                  </div>

                  <span className={`rounded-full border px-2.5 py-1 text-[8px] font-black uppercase tracking-[0.18em] ${statusStyle.chip}`}>
                    {agent.status_label || statusStyle.label}
                  </span>
                </div>

                <p className="min-h-[48px] text-[11px] leading-relaxed text-slate-400">
                  {agent.role}
                </p>

                <div className="space-y-4">
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between text-[8px] font-bold uppercase tracking-[0.16em] text-slate-500">
                      <span>Health</span>
                      <span className="font-mono text-white">{healthScore}%</span>
                    </div>
                    <div className="h-1 overflow-hidden rounded-sm border border-white/[0.04] bg-black/40">
                      <div className={`h-full ${metricTone(healthScore)}`} style={{ width: `${healthScore}%` }} />
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div className="rounded-md border border-white/[0.03] bg-white/[0.01] p-3">
                      <div className="text-[8px] font-black uppercase tracking-[0.16em] text-slate-600">
                        Freshness
                      </div>
                      <div className="mt-1 text-[12px] font-semibold text-white">{agent.freshness_label || "Unknown"}</div>
                    </div>
                    <div className="rounded-md border border-white/[0.03] bg-white/[0.01] p-3">
                      <div className="text-[8px] font-black uppercase tracking-[0.16em] text-slate-600">
                        Latency
                      </div>
                      <div className="mt-1 text-[12px] font-semibold text-white">
                        {agent.latency_ms ? `${agent.latency_ms}ms` : "n/a"}
                      </div>
                    </div>
                  </div>
                </div>

                <div className="flex items-center justify-between border-t border-white/[0.05] pt-4">
                  <div className="text-[8px] font-bold uppercase tracking-[0.18em] text-slate-600">
                    {agent.error_count ? `${agent.error_count} errors logged` : `Daily cadence ${agent.cadence_hours || 24}h`}
                  </div>
                  <ChevronRight size={14} className="text-slate-600 transition-colors group-hover:text-indigo-300" />
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {selectedAgent ? (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/90 p-4 backdrop-blur-md animate-fade-in md:p-8">
          <div className="absolute inset-0" onClick={() => setSelectedAgent(null)} />

          <div className="relative flex h-full w-full max-w-4xl flex-col overflow-hidden rounded-lg border border-white/[0.08] bg-[#0B0F14] shadow-2xl lg:h-[82vh]">
            <div className="flex h-14 items-center justify-between border-b border-white/[0.08] px-6 shrink-0">
              <div className="flex items-center gap-3">
                <div
                  className="flex h-8 w-8 items-center justify-center rounded-md border"
                  style={{
                    background: `${selectedAgent.color}10`,
                    borderColor: `${selectedAgent.color}22`,
                    color: selectedAgent.color,
                  }}
                >
                  {React.createElement(selectedAgent.icon || Cpu, { size: 16 })}
                </div>
                <h2 className="text-[12px] font-bold uppercase tracking-[0.18em] text-white">
                  {selectedAgent.name}
                </h2>
              </div>

              <button
                onClick={() => setSelectedAgent(null)}
                className="flex h-8 w-8 items-center justify-center text-slate-600 transition-colors hover:text-white"
              >
                <X size={18} />
              </button>
            </div>

            <div className="flex flex-1 flex-col overflow-y-auto lg:flex-row lg:overflow-hidden">
              <div className="w-full border-b border-white/[0.08] p-6 lg:w-[320px] lg:border-b-0 lg:border-r">
                <div className="space-y-6">
                  <div>
                    <p className="text-[9px] font-black uppercase tracking-[0.18em] text-slate-500">Role</p>
                    <p className="mt-2 text-sm leading-relaxed text-slate-300">{selectedAgent.role}</p>
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <InfoTile label="Status" value={selectedAgent.status_label || "UNKNOWN"} />
                    <InfoTile label="Health" value={`${Math.round(selectedAgent.health_score || 0)}%`} />
                    <InfoTile label="Latency" value={selectedAgent.latency_ms ? `${selectedAgent.latency_ms}ms` : "n/a"} />
                    <InfoTile label="Cadence" value={`${selectedAgent.cadence_hours || 24}h`} />
                  </div>

                  <div className="rounded-md border border-white/[0.05] bg-black/30 p-4">
                    <p className="text-[8px] font-black uppercase tracking-[0.16em] text-slate-600">Heartbeat</p>
                    <p className="mt-2 text-[13px] text-white">{selectedAgent.freshness_label || "No heartbeat yet"}</p>
                    <p className="mt-1 text-[10px] leading-relaxed text-slate-500">
                      {selectedAgent.last_seen
                        ? `Last seen at ${new Date(selectedAgent.last_seen).toLocaleString()}`
                        : "This agent has not written telemetry to the knowledge store yet."}
                    </p>
                  </div>
                </div>
              </div>

              <div className="flex flex-1 flex-col gap-6 bg-black/20 p-6">
                <div className="flex items-center justify-between">
                  <h3 className="text-[10px] font-bold uppercase tracking-[0.18em] text-slate-500">
                    Telemetry
                  </h3>
                  <span className="rounded-full border border-white/[0.08] bg-white/[0.03] px-3 py-1 text-[8px] font-black uppercase tracking-[0.16em] text-slate-400">
                    {selectedAgent.type_label || TIER_LABELS[selectedAgent.type] || "Agent"}
                  </span>
                </div>

                <div className="min-h-[240px] flex-1 rounded-md border border-white/[0.06] bg-black/40 p-4 font-mono text-[10px] text-slate-500 shadow-inner">
                  <TelemetryLine label="status" value={selectedAgent.status_label || "UNKNOWN"} />
                  <TelemetryLine label="freshness" value={selectedAgent.freshness_label || "No heartbeat"} />
                  <TelemetryLine label="latency" value={selectedAgent.latency_ms ? `${selectedAgent.latency_ms}ms` : "n/a"} />
                  <TelemetryLine label="errors" value={`${selectedAgent.error_count || 0}`} />
                  <TelemetryLine label="task" value={selectedAgent.current_task || "Idle / awaiting next route"} />
                  <TelemetryLine
                    label="refresh_window"
                    value={`Expected heartbeat within ${selectedAgent.cadence_hours || 24}h cadence.`}
                  />
                </div>

                <div className="rounded-md border border-indigo-500/20 bg-indigo-500/5 p-4">
                  <p className="text-[9px] font-black uppercase tracking-[0.18em] text-indigo-300/80">
                    Operator Note
                  </p>
                  <p className="mt-2 text-[12px] leading-relaxed text-slate-300">
                    Use this panel to spot stale daily agents, slow responses, or specialist nodes that are drifting into
                    error states before they affect the prediction pipeline.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}

function InfoTile({ label, value }) {
  return (
    <div className="rounded-md border border-white/[0.05] bg-black/30 p-3">
      <p className="text-[8px] font-black uppercase tracking-[0.16em] text-slate-600">{label}</p>
      <p className="mt-1.5 text-[13px] font-semibold text-white">{value}</p>
    </div>
  );
}

function TelemetryLine({ label, value }) {
  return (
    <div className="flex gap-4 border-b border-white/[0.03] py-3 last:border-b-0">
      <span className="w-[120px] shrink-0 text-indigo-400/55">{label}</span>
      <span className="text-slate-300">{value}</span>
    </div>
  );
}
