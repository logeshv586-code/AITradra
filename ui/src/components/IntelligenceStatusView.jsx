import React, { useEffect, useMemo, useState } from "react";
import {
  Activity,
  BrainCircuit,
  CheckCircle2,
  Clock3,
  Database,
  Loader2,
  Network,
  RefreshCw,
  ShieldAlert,
  Sparkles,
  Zap,
  Trophy,
  BarChart3,
} from "lucide-react";
import { API_BASE } from "../api_config";

function formatTime(value) {
  if (!value) return "n/a";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "recent";
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function routeTone(enabled) {
  return enabled ? "text-emerald-300 border-emerald-500/20 bg-emerald-500/10" : "text-slate-500 border-white/[0.08] bg-white/[0.03]";
}

function StatCard({ icon, label, value, sub, color = "var(--accent)" }) {
  const CardIcon = icon;
  return (
    <div className="surface-card p-5 flex flex-col gap-4">
      <div className="flex items-center justify-between gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-[var(--radius-md)] bg-[#1e232b] border border-[var(--border-color)]">
          <CardIcon size={18} style={{ color }} />
        </div>
        <span className="text-small-caps">{label}</span>
      </div>
      <div>
        <div className="text-2xl font-mono font-bold text-white">{value}</div>
        {sub && <div className="mt-1 text-[11px] text-[var(--text-muted)]">{sub}</div>}
      </div>
    </div>
  );
}

export default function IntelligenceStatusView() {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [scoring, setScoring] = useState(false);
  const [scoreResult, setScoreResult] = useState(null);
  const [leaderboard, setLeaderboard] = useState(null);
  const [lbGroupBy, setLbGroupBy] = useState("ticker");

  const load = async (isRefresh = false) => {
    try {
      setError("");
      if (isRefresh) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }
      const response = await fetch(`${API_BASE}/api/intelligence/status`);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      setStatus(await response.json());
    } catch (fetchError) {
      setError(fetchError.message || "Status unavailable");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const loadLeaderboard = async (group) => {
    try {
      const res = await fetch(`${API_BASE}/api/admin/accuracy-leaderboard?group_by=${group}&limit=15`);
      if (res.ok) setLeaderboard(await res.json());
    } catch { /* fail silently */ }
  };

  const handleForceScore = async () => {
    setScoring(true);
    setScoreResult(null);
    try {
      const res = await fetch(`${API_BASE}/api/admin/force-score-predictions`, { method: "POST" });
      const data = await res.json();
      setScoreResult(data);
      await load(true);
      await loadLeaderboard(lbGroupBy);
    } catch (err) {
      setScoreResult({ error: err.message });
    } finally {
      setScoring(false);
    }
  };

  useEffect(() => {
    load();
    loadLeaderboard(lbGroupBy);
    const id = setInterval(() => load(true), 30000);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    loadLeaderboard(lbGroupBy);
  }, [lbGroupBy]);

  const modelRouter = status?.model_router || {};
  const routes = useMemo(() => modelRouter.available_routes || {}, [modelRouter.available_routes]);
  const agents = status?.agent_mesh?.agents || [];
  const summary = status?.agent_mesh?.summary || {};
  const improvement = status?.self_improvement || {};
  const scoring_ = improvement.prediction_scoring || {};
  const accAgg = status?.accuracy_aggregate || {};

  const routeEntries = useMemo(() => Object.entries(routes), [routes]);
  const agentRows = agents.slice(0, 12);
  const avgAccuracy =
    scoring_.average_accuracy === null || scoring_.average_accuracy === undefined
      ? "n/a"
      : `${Math.round(Number(scoring_.average_accuracy) * 100)}%`;

  const globalAvg = accAgg.global_avg_accuracy != null
    ? `${Math.round(accAgg.global_avg_accuracy * 100)}%`
    : "n/a";

  if (loading && !status) {
    return (
      <div className="h-full flex flex-col items-center justify-center gap-4 bg-[var(--app-bg)] w-full">
        <Loader2 size={24} className="text-[var(--accent)] animate-spin" />
        <span className="text-[12px] font-medium text-[var(--text-muted)]">Loading intelligence status...</span>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto w-full p-4 md:p-6 lg:p-8 max-w-[1440px] mx-auto animate-fade-in flex flex-col gap-6 lg:gap-8">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex flex-col gap-2">
          <div className="flex items-center gap-3">
            <BrainCircuit size={22} className="text-[var(--accent)]" />
            <h1 className="heading-1">Intelligence Status</h1>
          </div>
          <p className="text-[13px] text-[var(--text-muted)]">
            {modelRouter.active_provider || "adaptive"} router, {summary.total || 0} agents, learning loop {improvement.loop_running ? "active" : "standby"}.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button type="button" onClick={handleForceScore} disabled={scoring} className="btn-standard h-9 px-4">
            <Zap size={13} className={scoring ? "animate-spin" : ""} />
            {scoring ? "Scoring..." : "Force Score"}
          </button>
          <button type="button" onClick={() => load(true)} disabled={refreshing} className="btn-standard h-9 px-4">
            <RefreshCw size={13} className={refreshing ? "animate-spin" : ""} />
            Refresh
          </button>
        </div>
      </div>

      {error && (
        <div className="surface-card p-4 flex items-center gap-3 border-red-500/20 bg-red-500/[0.04] text-red-200">
          <ShieldAlert size={16} />
          <span className="text-[12px]">{error}</span>
        </div>
      )}

      {scoreResult && (
        <div className={`surface-card p-4 flex items-center gap-3 ${scoreResult.error ? "border-red-500/20 bg-red-500/[0.04] text-red-200" : "border-emerald-500/20 bg-emerald-500/[0.04] text-emerald-200"}`}>
          <CheckCircle2 size={16} />
          <span className="text-[12px] font-mono">
            {scoreResult.error
              ? `Error: ${scoreResult.error}`
              : `Scored ${scoreResult.evaluated || 0} predictions | Skipped ${scoreResult.skipped || 0} | Failed ${scoreResult.failed || 0} | Avg: ${scoreResult.average_accuracy != null ? (scoreResult.average_accuracy * 100).toFixed(1) + "%" : "n/a"}`}
          </span>
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <StatCard
          icon={Sparkles}
          label="Active Provider"
          value={modelRouter.last_provider_used || modelRouter.active_provider || "adaptive"}
          sub={modelRouter.configured_provider || "auto"}
        />
        <StatCard
          icon={Network}
          label="Agent Mesh"
          value={summary.online ?? agentRows.length}
          sub={`${summary.total || agentRows.length} registered`}
          color="var(--positive)"
        />
        <StatCard
          icon={Activity}
          label="Outcome Accuracy"
          value={avgAccuracy}
          sub={`${scoring_.evaluated || 0} newly scored`}
          color="var(--warning)"
        />
        <StatCard
          icon={Trophy}
          label="Global Accuracy"
          value={globalAvg}
          sub={`${accAgg.total_scored || 0} total scored across ${accAgg.tickers || 0} tickers`}
          color="#e9b308"
        />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-[0.95fr_1.05fr] gap-6 lg:gap-8">
        <section className="surface-card flex flex-col overflow-hidden">
          <div className="p-5 border-b border-[var(--border-color)] bg-[#1b1f27] flex items-center gap-2">
            <Sparkles size={16} className="text-[var(--accent)]" />
            <h2 className="heading-3">Model Routes</h2>
          </div>
          <div className="p-5 flex flex-col gap-3">
            {routeEntries.map(([name, enabled]) => (
              <div key={name} className="flex items-center justify-between gap-4 rounded-[var(--radius-md)] border border-[var(--border-color)] bg-[#1e232b] px-4 py-3">
                <div className="flex flex-col gap-1 min-w-0">
                  <span className="text-[12px] font-semibold text-white uppercase tracking-wide">{name.replace(/_/g, " ")}</span>
                  <span className="text-[10px] text-[var(--text-muted)] font-mono truncate">
                    {modelRouter.models?.[name] || (enabled ? "configured" : "fallback")}
                  </span>
                </div>
                <span className={`surface-badge ${routeTone(enabled)}`}>
                  {enabled ? "ready" : "standby"}
                </span>
              </div>
            ))}
          </div>
        </section>

        <section className="surface-card flex flex-col overflow-hidden">
          <div className="p-5 border-b border-[var(--border-color)] bg-[#1b1f27] flex items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <Network size={16} className="text-[var(--accent)]" />
              <h2 className="heading-3">Agent Telemetry</h2>
            </div>
            <span className="surface-badge">{summary.median_latency_ms || 0}ms median</span>
          </div>
          <div className="overflow-x-auto">
            <table className="table-standard min-w-[620px]">
              <thead>
                <tr>
                  <th>Agent</th>
                  <th>Status</th>
                  <th className="text-right">Latency</th>
                  <th>Task</th>
                </tr>
              </thead>
              <tbody>
                {agentRows.map((agent) => (
                  <tr key={agent.id || agent.name}>
                    <td className="font-semibold text-white">{agent.name}</td>
                    <td>
                      <span className="surface-badge">{agent.status_label || agent.status}</span>
                    </td>
                    <td className="text-right font-mono">{agent.latency_ms || 0}ms</td>
                    <td className="text-[11px] text-[var(--text-muted)] truncate max-w-[240px]">{agent.current_task || agent.role || "idle"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>

      {/* Learning Loop */}
      <section className="surface-card flex flex-col overflow-hidden">
        <div className="p-5 border-b border-[var(--border-color)] bg-[#1b1f27] flex items-center gap-2">
          <Database size={16} className="text-[var(--accent)]" />
          <h2 className="heading-3">Learning Loop</h2>
        </div>
        <div className="p-5 grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="rounded-[var(--radius-md)] border border-[var(--border-color)] bg-[#1e232b] p-4">
            <div className="flex items-center gap-2 mb-2">
              <CheckCircle2 size={14} className="text-emerald-300" />
              <span className="text-small-caps">Outcome Scoring</span>
            </div>
            <div className="text-xl font-mono font-bold text-white">{scoring_.evaluated || 0}</div>
            <div className="text-[11px] text-[var(--text-muted)] mt-1">{scoring_.skipped || 0} skipped, {scoring_.failed || 0} failed</div>
          </div>
          <div className="rounded-[var(--radius-md)] border border-[var(--border-color)] bg-[#1e232b] p-4">
            <div className="text-small-caps mb-2">Average Accuracy</div>
            <div className="text-xl font-mono font-bold text-white">{avgAccuracy}</div>
            <div className="text-[11px] text-[var(--text-muted)] mt-1">{formatTime(scoring_.updated_at)}</div>
          </div>
          <div className="rounded-[var(--radius-md)] border border-[var(--border-color)] bg-[#1e232b] p-4">
            <div className="text-small-caps mb-2">Feedback Loops</div>
            <div className="flex flex-wrap gap-2">
              {(improvement.feedback_loops || []).map((loop) => (
                <span key={loop} className="surface-badge">{loop.replace(/_/g, " ")}</span>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Accuracy Leaderboard */}
      <section className="surface-card flex flex-col overflow-hidden">
        <div className="p-5 border-b border-[var(--border-color)] bg-[#1b1f27] flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <BarChart3 size={16} className="text-[#e9b308]" />
            <h2 className="heading-3">Accuracy Leaderboard</h2>
          </div>
          <div className="flex items-center gap-2">
            {["ticker", "model", "provider", "direction"].map((g) => (
              <button
                key={g}
                onClick={() => setLbGroupBy(g)}
                className={`px-3 py-1 rounded-[var(--radius-sm)] text-[11px] font-medium transition-colors ${
                  lbGroupBy === g
                    ? "bg-[var(--accent)] text-white"
                    : "bg-[#1e232b] text-[var(--text-muted)] hover:text-white border border-[var(--border-color)]"
                }`}
              >
                {g}
              </button>
            ))}
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="table-standard min-w-[540px]">
            <thead>
              <tr>
                <th>{lbGroupBy}</th>
                <th className="text-right">Avg Accuracy</th>
                <th className="text-right">Total Scored</th>
                <th className="text-right">Best</th>
                <th className="text-right">Worst</th>
              </tr>
            </thead>
            <tbody>
              {(leaderboard?.leaderboard || []).length === 0 ? (
                <tr>
                  <td colSpan={5} className="text-center text-[var(--text-muted)] py-8">No data yet. Score predictions to populate.</td>
                </tr>
              ) : (
                (leaderboard?.leaderboard || []).map((row, idx) => (
                  <tr key={idx}>
                    <td className="font-semibold text-white">{row[lbGroupBy] || "—"}</td>
                    <td className="text-right font-mono">{row.avg_accuracy != null ? (row.avg_accuracy * 100).toFixed(1) + "%" : "—"}</td>
                    <td className="text-right font-mono">{row.total_scored || 0}</td>
                    <td className="text-right font-mono text-emerald-300">{row.best_score != null ? (row.best_score * 100).toFixed(0) + "%" : "—"}</td>
                    <td className="text-right font-mono text-red-300">{row.worst_score != null ? (row.worst_score * 100).toFixed(0) + "%" : "—"}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
