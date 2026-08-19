import React, { useEffect, useMemo, useState } from "react";
import {
  Activity,
  BrainCircuit,
  CheckCircle2,
  Loader2,
  Network,
  RefreshCw,
  ShieldAlert,
  ShieldCheck,
  BarChart3,
  Lock,
  PlayCircle,
} from "lucide-react";
import { API_BASE } from "../api_config";

function readableName(value = "") {
  return String(value)
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatTime(value) {
  if (!value) return "Not yet";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Recently";
  return date.toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function StatCard({ icon, label, value, sub, positive }) {
  const Icon = icon;
  return (
    <div className="surface-card p-5 flex flex-col gap-4">
      <div className="flex items-center justify-between gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-[var(--radius-md)] bg-[#1e232b] border border-[var(--border-color)]">
          <Icon size={18} className={positive === false ? "text-[var(--negative)]" : positive === true ? "text-[var(--positive)]" : "text-[var(--accent)]"} />
        </div>
        <span className="text-small-caps">{label}</span>
      </div>
      <div>
        <div className="text-xl font-mono font-bold text-white">{value}</div>
        {sub && <div className="mt-1 text-[11px] text-[var(--text-muted)] leading-relaxed">{sub}</div>}
      </div>
    </div>
  );
}

export default function IntelligenceStatusView() {
  const [status, setStatus] = useState(null);
  const [trading, setTrading] = useState(null);
  const [leaderboard, setLeaderboard] = useState(null);
  const [groupBy, setGroupBy] = useState("ticker");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [scoring, setScoring] = useState(false);
  const [scoreMessage, setScoreMessage] = useState("");

  const load = async (refresh = false) => {
    refresh ? setRefreshing(true) : setLoading(true);
    setError("");
    try {
      const [statusResponse, tradingResponse] = await Promise.all([
        fetch(`${API_BASE}/api/intelligence/status`),
        fetch(`${API_BASE}/api/trading/status`),
      ]);
      if (!statusResponse.ok) throw new Error("Market intelligence status is unavailable");
      setStatus(await statusResponse.json());
      if (tradingResponse.ok) setTrading(await tradingResponse.json());
    } catch (loadError) {
      setError(loadError.message || "System status is temporarily unavailable");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const loadLeaderboard = async (group) => {
    try {
      const response = await fetch(`${API_BASE}/api/admin/accuracy-leaderboard?group_by=${group}&limit=12`);
      if (response.ok) setLeaderboard(await response.json());
    } catch {
      // Track record is supplementary. Keep the rest of the page usable.
    }
  };

  const updateResults = async () => {
    setScoring(true);
    setScoreMessage("");
    try {
      const response = await fetch(`${API_BASE}/api/admin/force-score-predictions`, { method: "POST" });
      const result = await response.json();
      if (!response.ok || result.error) throw new Error(result.error || "Could not update prediction results");
      setScoreMessage(`Reviewed ${result.evaluated || 0} prediction outcomes.`);
      await Promise.all([load(true), loadLeaderboard(groupBy)]);
    } catch (updateError) {
      setScoreMessage(updateError.message || "Prediction results could not be updated");
    } finally {
      setScoring(false);
    }
  };

  useEffect(() => {
    load();
    loadLeaderboard(groupBy);
    const timer = setInterval(() => load(true), 30000);
    return () => clearInterval(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    loadLeaderboard(groupBy);
  }, [groupBy]);

  const agents = status?.agent_mesh?.agents || [];
  const summary = status?.agent_mesh?.summary || {};
  const aggregate = status?.accuracy_aggregate || {};
  const displayedAgents = agents.slice(0, 14);
  const predictionAccuracy =
    aggregate.global_avg_accuracy == null
      ? "Not enough data"
      : `${Math.round(Number(aggregate.global_avg_accuracy) * 100)}%`;
  const tradingMode = trading?.uses_real_money ? "Real money" : "Practice only";
  const liveReady = Boolean(trading?.live_ready);

  const leaderboardRows = useMemo(
    () => leaderboard?.rows || leaderboard?.leaderboard || leaderboard?.data || [],
    [leaderboard]
  );

  if (loading && !status) {
    return (
      <div className="h-full flex flex-col items-center justify-center gap-4 bg-[var(--app-bg)] w-full">
        <Loader2 size={24} className="text-[var(--accent)] animate-spin" />
        <span className="text-[12px] text-[var(--text-muted)]">Checking AITradra services…</span>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto w-full p-4 md:p-6 lg:p-8 max-w-[1440px] mx-auto animate-fade-in flex flex-col gap-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <BrainCircuit size={22} className="text-[var(--accent)]" />
            <h1 className="heading-1">Intelligence Status</h1>
          </div>
          <p className="text-[13px] text-[var(--text-muted)] mt-2 max-w-2xl">
            See whether market data, AI analysis, prediction tracking, and trading safety checks are ready before you rely on a result.
          </p>
        </div>
        <div className="flex gap-2">
          <button type="button" onClick={updateResults} disabled={scoring} className="btn-standard h-9 px-4">
            {scoring ? <Loader2 size={13} className="animate-spin" /> : <CheckCircle2 size={13} />}
            {scoring ? "Updating…" : "Update prediction results"}
          </button>
          <button type="button" onClick={() => load(true)} disabled={refreshing} className="btn-standard h-9 px-4">
            <RefreshCw size={13} className={refreshing ? "animate-spin" : ""} /> Refresh
          </button>
        </div>
      </div>

      {error && (
        <div className="surface-card p-4 flex items-center gap-3 border-red-500/20 bg-red-500/[0.04] text-red-200">
          <ShieldAlert size={16} /> <span className="text-[12px]">{error}</span>
        </div>
      )}
      {scoreMessage && (
        <div className="surface-card p-4 flex items-center gap-3 text-[12px] text-[var(--text-muted)]">
          <CheckCircle2 size={15} className="text-[var(--positive)]" /> {scoreMessage}
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <StatCard
          icon={Activity}
          label="Market intelligence"
          value={status ? "Connected" : "Checking"}
          sub="Current data and AI analysis services"
          positive={Boolean(status)}
        />
        <StatCard
          icon={Network}
          label="Data services"
          value={`${summary.online ?? displayedAgents.length} online`}
          sub={`${summary.total || displayedAgents.length} services tracked`}
          positive={(summary.error || 0) === 0}
        />
        <StatCard
          icon={BarChart3}
          label="Prediction accuracy"
          value={predictionAccuracy}
          sub={`${aggregate.total_scored || 0} resolved predictions measured`}
        />
        <StatCard
          icon={trading?.uses_real_money ? PlayCircle : Lock}
          label="Trading mode"
          value={tradingMode}
          sub={trading?.automation_enabled ? "Automated cycles enabled" : "Automated cycles off"}
          positive={!trading?.uses_real_money || liveReady}
        />
      </div>

      <section className="surface-card overflow-hidden">
        <div className="p-5 border-b border-[var(--border-color)] flex items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <ShieldCheck size={17} className="text-[var(--positive)]" />
            <div>
              <h2 className="heading-3">Trading safety</h2>
              <p className="text-[11px] text-[var(--text-muted)] mt-1">Real-money execution stays locked until all required checks pass.</p>
            </div>
          </div>
          <span className={`surface-badge ${liveReady ? "text-[var(--positive)]" : "text-amber-300"}`}>
            {liveReady ? "Live checks passed" : "Live locked"}
          </span>
        </div>
        <div className="p-5 grid grid-cols-1 lg:grid-cols-[0.9fr_1.1fr] gap-5">
          <div className="grid grid-cols-2 gap-3">
            <SafetyCheck label="Execution gate" passed={trading?.checks?.execution_gate} />
            <SafetyCheck label="Strategy validation" passed={trading?.checks?.strategy_validation} />
            <SafetyCheck label="Stop & target protection" passed={trading?.checks?.stop_and_target_protection} />
            <SafetyCheck label="Automation" passed={trading?.automation_enabled} neutral={!trading?.automation_enabled} />
          </div>
          <div className="rounded-[var(--radius-md)] border border-[var(--border-color)] bg-[#171b22] p-4">
            <h3 className="text-[12px] font-semibold text-white mb-3">Risk limits</h3>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-[11px] text-[var(--text-muted)]">
              <RiskLimit label="Max position" value={`${Number(trading?.risk_controls?.max_position_pct || 0).toFixed(1)}%`} />
              <RiskLimit label="Daily loss stop" value={`${Number(trading?.risk_controls?.daily_loss_limit_pct || 0).toFixed(1)}%`} />
              <RiskLimit label="Max positions" value={trading?.risk_controls?.max_open_positions ?? "—"} />
              <RiskLimit label="Max leverage" value={`${trading?.risk_controls?.max_leverage ?? "—"}x`} />
              <RiskLimit label="Cash reserve" value={`${Number(trading?.risk_controls?.cash_reserve_pct || 0).toFixed(1)}%`} />
            </div>
          </div>
        </div>

        {trading?.assets && (
          <div className="border-t border-[var(--border-color)] p-5">
            <h3 className="text-[12px] font-semibold text-white mb-3">Live strategy checks by asset</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {Object.entries(trading.assets).map(([ticker, item]) => (
                <div key={ticker} className="rounded-[var(--radius-md)] border border-[var(--border-color)] bg-[#171b22] p-4">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-mono font-semibold text-white">{ticker}</span>
                    <span className={`surface-badge ${item.validated ? "text-[var(--positive)]" : "text-amber-300"}`}>
                      {item.validated ? "Validated" : "Not validated"}
                    </span>
                  </div>
                  <div className="text-[10px] text-[var(--text-muted)] mt-2">Last check: {formatTime(item.last_validation)}</div>
                  {!item.validated && item.reasons?.[0] && (
                    <div className="text-[10px] text-amber-200/80 mt-2 leading-relaxed">{item.reasons[0]}</div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </section>

      <section className="surface-card overflow-hidden">
        <div className="p-5 border-b border-[var(--border-color)] flex items-center justify-between gap-4">
          <div>
            <h2 className="heading-3">Market data & analysis services</h2>
            <p className="text-[11px] text-[var(--text-muted)] mt-1">A simple health check for the services behind your answers.</p>
          </div>
          <span className="surface-badge">{summary.median_latency_ms || 0} ms typical response</span>
        </div>
        <div className="overflow-x-auto">
          <table className="table-standard min-w-[650px]">
            <thead>
              <tr>
                <th>Service</th>
                <th>Status</th>
                <th className="text-right">Response</th>
                <th>What it does</th>
              </tr>
            </thead>
            <tbody>
              {displayedAgents.map((agent) => (
                <tr key={agent.id || agent.name}>
                  <td className="font-semibold text-white">{readableName(agent.name)}</td>
                  <td>
                    <span className={`surface-badge ${agent.status === "error" ? "text-[var(--negative)]" : agent.status === "stale" ? "text-amber-300" : "text-[var(--positive)]"}`}>
                      {agent.status === "active" ? "Working" : agent.status === "idle" ? "Ready" : readableName(agent.status_label || agent.status)}
                    </span>
                  </td>
                  <td className="text-right font-mono">{agent.latency_ms || 0} ms</td>
                  <td className="text-[11px] text-[var(--text-muted)]">{agent.role || "Market analysis"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="surface-card overflow-hidden">
        <div className="p-5 border-b border-[var(--border-color)] flex flex-col md:flex-row md:items-center md:justify-between gap-3">
          <div>
            <h2 className="heading-3">Prediction track record</h2>
            <p className="text-[11px] text-[var(--text-muted)] mt-1">Use resolved outcomes to judge where AITradra has been more or less reliable.</p>
          </div>
          <div className="flex gap-2">
            {["ticker", "model", "direction"].map((group) => (
              <button
                key={group}
                onClick={() => setGroupBy(group)}
                className={`px-3 py-1.5 rounded-[var(--radius-sm)] text-[11px] transition ${
                  groupBy === group
                    ? "bg-[var(--accent)] text-white"
                    : "bg-[#1e232b] text-[var(--text-muted)] border border-[var(--border-color)] hover:text-white"
                }`}
              >
                By {group === "ticker" ? "asset" : group}
              </button>
            ))}
          </div>
        </div>
        {leaderboardRows.length ? (
          <div className="overflow-x-auto">
            <table className="table-standard min-w-[560px]">
              <thead>
                <tr>
                  <th>{groupBy === "ticker" ? "Asset" : readableName(groupBy)}</th>
                  <th className="text-right">Accuracy</th>
                  <th className="text-right">Outcomes measured</th>
                </tr>
              </thead>
              <tbody>
                {leaderboardRows.map((row, index) => {
                  const name = row.group || row.key || row[groupBy] || row.name || `Result ${index + 1}`;
                  const accuracy = Number(row.avg_accuracy ?? row.accuracy ?? 0);
                  const normalized = accuracy <= 1 ? accuracy * 100 : accuracy;
                  return (
                    <tr key={`${name}-${index}`}>
                      <td className="font-semibold text-white">{name}</td>
                      <td className="text-right font-mono">{normalized.toFixed(1)}%</td>
                      <td className="text-right font-mono text-[var(--text-muted)]">{row.total_scored ?? row.count ?? row.total ?? 0}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="p-8 text-center text-[12px] text-[var(--text-muted)]">
            Prediction history will become more useful as more outcomes are resolved.
          </div>
        )}
      </section>
    </div>
  );
}

function SafetyCheck({ label, passed, neutral = false }) {
  return (
    <div className="rounded-[var(--radius-md)] border border-[var(--border-color)] bg-[#171b22] p-4">
      <div className="flex items-center gap-2">
        {passed ? (
          <CheckCircle2 size={14} className="text-[var(--positive)]" />
        ) : neutral ? (
          <Lock size={14} className="text-[var(--text-muted)]" />
        ) : (
          <Lock size={14} className="text-amber-300" />
        )}
        <span className="text-[11px] font-medium text-white">{label}</span>
      </div>
      <div className="text-[10px] text-[var(--text-muted)] mt-2">
        {passed ? "Passed" : neutral ? "Off by choice" : "Required before live use"}
      </div>
    </div>
  );
}

function RiskLimit({ label, value }) {
  return (
    <div>
      <div>{label}</div>
      <div className="font-mono text-white mt-1">{value}</div>
    </div>
  );
}
