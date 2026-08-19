import React, { useEffect, useState } from "react";
import {
  Activity,
  BarChart3,
  BrainCircuit,
  CheckCircle2,
  Loader2,
  Lock,
  Network,
  RefreshCw,
  ShieldAlert,
  ShieldCheck,
} from "lucide-react";
import { API_BASE } from "../api_config";
import CustomerConnectionsPanel from "./CustomerConnectionsPanel";

function readable(value = "") {
  return String(value).replace(/([a-z])([A-Z])/g, "$1 $2").replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function StatCard({ icon: Icon, label, value, sub, positive }) {
  return (
    <div className="surface-card p-5 flex flex-col gap-4">
      <div className="flex items-center justify-between gap-3">
        <div className="h-10 w-10 rounded-[var(--radius-md)] bg-[#1e232b] border border-[var(--border-color)] flex items-center justify-center">
          <Icon size={18} className={positive === false ? "text-[var(--negative)]" : positive === true ? "text-[var(--positive)]" : "text-[var(--accent)]"} />
        </div>
        <span className="text-small-caps">{label}</span>
      </div>
      <div>
        <div className="text-xl font-mono font-bold text-white">{value}</div>
        <div className="text-[11px] text-[var(--text-muted)] mt-1 leading-relaxed">{sub}</div>
      </div>
    </div>
  );
}

export default function IntelligenceStatusView() {
  const [status, setStatus] = useState(null);
  const [autoTrading, setAutoTrading] = useState(null);
  const [customerTrading, setCustomerTrading] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  const load = async (refresh = false) => {
    refresh ? setRefreshing(true) : setLoading(true);
    setError("");
    try {
      const [statusRes, autoRes, manualRes] = await Promise.all([
        fetch(`${API_BASE}/api/intelligence/status`),
        fetch(`${API_BASE}/api/trading/status`),
        fetch(`${API_BASE}/api/customer/trading/status`),
      ]);
      if (!statusRes.ok) throw new Error("Market intelligence status is unavailable");
      setStatus(await statusRes.json());
      if (autoRes.ok) setAutoTrading(await autoRes.json());
      if (manualRes.ok) setCustomerTrading(await manualRes.json());
    } catch (e) {
      setError(e.message || "System status is temporarily unavailable");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    load();
    const timer = setInterval(() => load(true), 30000);
    return () => clearInterval(timer);
  }, []);

  const summary = status?.agent_mesh?.summary || {};
  const agents = status?.agent_mesh?.agents || [];
  const aggregate = status?.accuracy_aggregate || {};
  const accuracy = aggregate.global_avg_accuracy == null
    ? "Building history"
    : `${Math.round(Number(aggregate.global_avg_accuracy) * 100)}%`;
  const manualReady = Boolean(customerTrading?.real_money_ready);
  const autoEnabled = Boolean(customerTrading?.automation?.automation_enabled || autoTrading?.automation_enabled);
  const connections = customerTrading?.broker_connections || [];

  if (loading && !status) {
    return (
      <div className="h-full flex flex-col items-center justify-center gap-3 bg-[var(--app-bg)]">
        <Loader2 size={24} className="text-[var(--accent)] animate-spin" />
        <span className="text-[12px] text-[var(--text-muted)]">Checking market services…</span>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto w-full p-4 md:p-6 lg:p-8 max-w-[1440px] mx-auto animate-fade-in flex flex-col gap-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <BrainCircuit size={22} className="text-[var(--accent)]" />
            <h1 className="heading-1">AITradra readiness</h1>
          </div>
          <p className="text-[13px] text-[var(--text-muted)] mt-2 max-w-2xl">
            A simple view of the data, AI analysis, prediction history and trading safeguards behind the answers you see across the app.
          </p>
        </div>
        <button type="button" onClick={() => load(true)} disabled={refreshing} className="btn-standard h-9 px-4">
          <RefreshCw size={13} className={refreshing ? "animate-spin" : ""} /> Refresh
        </button>
      </div>

      {error && (
        <div className="surface-card p-4 flex items-center gap-3 text-[var(--negative)] border-red-500/20">
          <ShieldAlert size={16} /> <span className="text-[12px]">{error}</span>
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <StatCard icon={Activity} label="Market data" value={status ? "Connected" : "Checking"} sub="Live/cached prices, historical data, news and sentiment" positive={Boolean(status)} />
        <StatCard icon={Network} label="AI services" value={`${summary.online ?? agents.length} ready`} sub={`${summary.total || agents.length} analysis services monitored`} positive={(summary.error || 0) === 0} />
        <StatCard icon={BarChart3} label="Measured accuracy" value={accuracy} sub={`${aggregate.total_scored || 0} completed predictions have outcomes`} />
        <StatCard icon={Lock} label="Real trading" value={manualReady ? "Ready" : "Locked by default"} sub={`${connections.length} broker connection${connections.length === 1 ? "" : "s"}; automation ${autoEnabled ? "on" : "off"}`} positive={manualReady || !autoEnabled} />
      </div>

      <section className="surface-card overflow-hidden">
        <div className="p-5 border-b border-[var(--border-color)] flex items-start justify-between gap-4">
          <div className="flex items-start gap-3">
            <ShieldCheck size={18} className="text-[var(--positive)] mt-0.5" />
            <div>
              <h2 className="heading-3">Trading safeguards</h2>
              <p className="text-[11px] text-[var(--text-muted)] mt-1">Adding a broker key never turns on autonomous trading. Manual and automated real-money permissions are separate.</p>
            </div>
          </div>
          <span className={`surface-badge ${manualReady ? "text-[var(--positive)]" : "text-amber-300"}`}>
            {manualReady ? "Manual live ready" : "Real money locked"}
          </span>
        </div>
        <div className="p-5 grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3">
          <SafetyTile label="Practice mode" value={customerTrading?.manual?.paper_mode ? "On" : "Off"} good={customerTrading?.manual?.paper_mode} />
          <SafetyTile label="Manual real trading" value={manualReady ? "Enabled" : "Disabled"} good={manualReady} neutral={!manualReady} />
          <SafetyTile label="Autonomous trading" value={autoEnabled ? "Enabled" : "Disabled"} good={!autoEnabled} neutral={!autoEnabled} />
          <SafetyTile label="Stop & target protection" value={customerTrading?.manual?.protective_orders_required ? "Required" : "Not required"} good={customerTrading?.manual?.protective_orders_required} />
        </div>
        {!manualReady && customerTrading?.manual?.blockers?.length > 0 && (
          <div className="mx-5 mb-5 rounded-[var(--radius-md)] border border-amber-500/20 bg-amber-500/[0.05] p-4">
            <div className="text-[11px] font-semibold text-amber-200 mb-2">Why real trading is locked</div>
            <div className="flex flex-wrap gap-2">
              {customerTrading.manual.blockers.map((blocker) => <span key={blocker} className="surface-badge text-amber-200">{readable(blocker)}</span>)}
            </div>
          </div>
        )}
      </section>

      <CustomerConnectionsPanel />

      <section className="surface-card overflow-hidden">
        <div className="p-5 border-b border-[var(--border-color)]">
          <h2 className="heading-3">What is working behind your answers</h2>
          <p className="text-[11px] text-[var(--text-muted)] mt-1">You do not need to manage these agents. This section simply shows whether the analysis services are healthy.</p>
        </div>
        <div className="overflow-x-auto">
          <table className="table-standard min-w-[650px]">
            <thead><tr><th>Analysis service</th><th>Status</th><th className="text-right">Response</th><th>Purpose</th></tr></thead>
            <tbody>
              {agents.slice(0, 16).map((agent) => (
                <tr key={agent.id || agent.name}>
                  <td className="font-semibold text-white">{readable(agent.name)}</td>
                  <td><span className={`surface-badge ${agent.status === "error" ? "text-[var(--negative)]" : agent.status === "stale" ? "text-amber-300" : "text-[var(--positive)]"}`}>{agent.status === "active" ? "Working" : agent.status === "idle" ? "Ready" : readable(agent.status_label || agent.status)}</span></td>
                  <td className="text-right font-mono">{agent.latency_ms || 0} ms</td>
                  <td className="text-[11px] text-[var(--text-muted)]">{agent.role || "Market analysis"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <div className="surface-card p-5 flex gap-3 items-start">
        <CheckCircle2 size={16} className="text-[var(--positive)] mt-0.5 shrink-0" />
        <p className="text-[11px] text-[var(--text-muted)] leading-relaxed">
          AITradra combines available market data, news, historical behavior and multiple analysis agents. Prediction accuracy is measured only after outcomes are known; a prediction is not a guarantee of profit.
        </p>
      </div>
    </div>
  );
}

function SafetyTile({ label, value, good, neutral }) {
  return (
    <div className="rounded-[var(--radius-md)] border border-[var(--border-color)] bg-[#171b22] p-4">
      <div className="text-[10px] uppercase tracking-wider text-[var(--text-muted)]">{label}</div>
      <div className={`text-[13px] font-semibold mt-1 ${neutral ? "text-[var(--text-muted)]" : good ? "text-[var(--positive)]" : "text-amber-300"}`}>{value}</div>
    </div>
  );
}
