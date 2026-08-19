import React from "react";
import { Activity, BrainCircuit, CheckCircle2, Network, ShieldCheck } from "lucide-react";

function friendlyRole(agent) {
  const role = agent.role || "Supports market analysis and cross-checks other AI signals.";
  return role
    .replace(/OHLCV/gi, "price history")
    .replace(/VaR/gi, "loss-risk")
    .replace(/RAG/gi, "research memory")
    .replace(/orchestration/gi, "coordination")
    .replace(/semantic/gi, "context-aware");
}

export default function AgentMatrixView({ agents = [] }) {
  const safeAgents = Array.isArray(agents) ? agents : [];
  const ready = safeAgents.filter((agent) => ["active", "idle"].includes(String(agent.status || "").toLowerCase())).length;
  const working = safeAgents.filter((agent) => String(agent.status || "").toLowerCase() === "active").length;
  const issues = safeAgents.filter((agent) => ["error", "stale"].includes(String(agent.status || "").toLowerCase())).length;

  return (
    <div className="flex-1 overflow-y-auto w-full p-4 md:p-6 lg:p-8 max-w-[1440px] mx-auto animate-fade-in flex flex-col gap-6">
      <div>
        <div className="flex items-center gap-3"><Network size={22} className="text-[var(--accent)]" /><h1 className="heading-1">How AITradra checks an idea</h1></div>
        <p className="text-[13px] text-[var(--text-muted)] mt-2 max-w-3xl">AITradra does not rely on one AI opinion. Different services check price behavior, news, fundamentals, sentiment, market conditions and risk, then compare their conclusions before a customer-facing answer is produced.</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Summary icon={CheckCircle2} label="Ready" value={`${ready}/${safeAgents.length || 0}`} text="Services available for analysis" good />
        <Summary icon={Activity} label="Working now" value={String(working)} text="Services currently processing tasks" />
        <Summary icon={ShieldCheck} label="Needs attention" value={String(issues)} text="Stale or error states are excluded/discounted" good={issues === 0} />
      </div>

      <section className="surface-card p-5">
        <div className="flex items-start gap-3"><BrainCircuit size={17} className="text-[var(--accent)] mt-0.5" /><div><h2 className="heading-3">What happens when you ask about a stock</h2><p className="text-[11px] text-[var(--text-muted)] mt-2 leading-relaxed">The system collects current evidence, lets specialist agents form separate views, checks agreement and contradictions, runs a risk review, and then explains the result in plain language. You can see those individual views in Stock Terminal after running full AI research.</p></div></div>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mt-5">{["Collect evidence", "Analyze separately", "Compare signals", "Check risk", "Explain to customer"].map((step, index) => <div key={step} className="rounded-[var(--radius-md)] border border-[var(--border-color)] bg-[#171b22] p-3"><div className="text-[9px] text-[var(--accent)] font-bold">STEP {index + 1}</div><div className="text-[11px] text-white mt-1">{step}</div></div>)}</div>
      </section>

      <section className="surface-card overflow-hidden">
        <div className="p-5 border-b border-[var(--border-color)]"><h2 className="heading-3">Analysis services</h2><p className="text-[10px] text-[var(--text-muted)] mt-1">This is a health view, not a developer control panel. Service restarts and internal configuration stay outside the customer flow.</p></div>
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-px bg-[var(--border-color)]">
          {safeAgents.map((agent) => {
            const state = String(agent.status || "standby").toLowerCase();
            const healthy = state === "active" || state === "idle";
            return (
              <div key={agent.id || agent.name} className="bg-[var(--card-bg)] p-5">
                <div className="flex items-center justify-between gap-3"><div className="font-semibold text-white text-[12px]">{String(agent.name || "AI service").replace(/([a-z])([A-Z])/g, "$1 $2")}</div><span className={`surface-badge ${healthy ? "text-[var(--positive)]" : state === "stale" ? "text-amber-300" : "text-[var(--negative)]"}`}>{state === "active" ? "Working" : state === "idle" ? "Ready" : state === "stale" ? "Refreshing" : "Unavailable"}</span></div>
                <p className="text-[10px] text-[var(--text-muted)] leading-relaxed mt-3">{friendlyRole(agent)}</p>
                <div className="flex items-center justify-between mt-4 text-[9px] text-[var(--text-muted)]"><span>{agent.freshness_label || "Status current"}</span><span>{agent.latency_ms ? `${agent.latency_ms} ms` : ""}</span></div>
              </div>
            );
          })}
          {!safeAgents.length && <div className="col-span-full bg-[var(--card-bg)] p-10 text-center text-[11px] text-[var(--text-muted)]">Analysis services are connecting.</div>}
        </div>
      </section>
    </div>
  );
}

function Summary({ icon: Icon, label, value, text, good }) {
  return <div className="surface-card p-5 flex items-start gap-3"><Icon size={17} className={good ? "text-[var(--positive)]" : "text-[var(--accent)]"} /><div><div className="text-[9px] uppercase tracking-wider text-[var(--text-muted)]">{label}</div><div className="text-xl font-mono font-bold text-white mt-1">{value}</div><div className="text-[10px] text-[var(--text-muted)] mt-1">{text}</div></div></div>;
}
