import React, { useEffect, useMemo, useState } from "react";
import {
  Activity,
  AlertTriangle,
  BarChart3,
  BrainCircuit,
  CheckCircle2,
  Clock3,
  Loader2,
  Newspaper,
  RefreshCw,
  Shield,
  Sparkles,
  TrendingDown,
  TrendingUp,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import { API_BASE } from "../api_config";
import TradingViewChart from "./TradingViewChart";

function number(value, fallback = 0) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function normalizeBars(bars = []) {
  return bars
    .map((bar, index) => ({
      t: bar.t || bar.timestamp || bar.date || `T${index + 1}`,
      o: number(bar.o ?? bar.open),
      h: number(bar.h ?? bar.high),
      l: number(bar.l ?? bar.low),
      c: number(bar.c ?? bar.close),
      v: number(bar.v ?? bar.volume),
    }))
    .filter((bar) => bar.c > 0);
}

function compact(value) {
  const amount = number(value);
  if (!amount) return "—";
  if (amount >= 1_000_000_000) return `${(amount / 1_000_000_000).toFixed(1)}B`;
  if (amount >= 1_000_000) return `${(amount / 1_000_000).toFixed(1)}M`;
  if (amount >= 1_000) return `${(amount / 1_000).toFixed(1)}K`;
  return amount.toLocaleString();
}

export default function StockDetailView({ ticker }) {
  const tickerId = String(ticker || "").toUpperCase();
  const [brief, setBrief] = useState(null);
  const [chart, setChart] = useState([]);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [researching, setResearching] = useState(false);
  const [error, setError] = useState("");

  const load = async () => {
    if (!tickerId) return;
    setError("");
    try {
      const [briefResponse, chartResponse, historyResponse] = await Promise.all([
        fetch(`${API_BASE}/api/customer/brief/${tickerId}`),
        fetch(`${API_BASE}/api/stock/${tickerId}/chart?period=1d`),
        fetch(`${API_BASE}/api/customer/history?ticker=${encodeURIComponent(tickerId)}&limit=6`),
      ]);
      if (!briefResponse.ok) throw new Error(`Could not load ${tickerId} research`);
      setBrief(await briefResponse.json());
      if (chartResponse.ok) setChart(normalizeBars((await chartResponse.json()).ohlcv || []));
      if (historyResponse.ok) setHistory((await historyResponse.json()).history || []);
    } catch (e) {
      setError(e.message || "Market research is unavailable");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setLoading(true);
    setBrief(null);
    load();
    const timer = setInterval(load, 60000);
    return () => clearInterval(timer);
  }, [tickerId]);

  const runFullResearch = async () => {
    setResearching(true);
    setError("");
    try {
      const response = await fetch(`${API_BASE}/api/customer/research/${tickerId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          mode: "DEEP",
          query: `Explain ${tickerId} for a customer: what happened, why it happened, whether the evidence is bullish/bearish/neutral, the main risks, contradictions, prediction and what to watch next.`,
        }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data?.detail || "Full research failed");
      setBrief(data);
      const historyResponse = await fetch(`${API_BASE}/api/customer/history?ticker=${encodeURIComponent(tickerId)}&limit=6`);
      if (historyResponse.ok) setHistory((await historyResponse.json()).history || []);
    } catch (e) {
      setError(e.message || "Full AI research could not be completed");
    } finally {
      setResearching(false);
    }
  };

  const price = number(brief?.price?.current);
  const change = number(brief?.price?.change_pct);
  const isUp = change >= 0;
  const prediction = brief?.prediction || {};
  const risk = brief?.risk || {};
  const why = brief?.why_it_moved || {};
  const agents = brief?.agent_consensus?.agents || [];
  const news = brief?.news || [];
  const bars = useMemo(() => chart, [chart]);

  if (loading && !brief) {
    return (
      <div className="h-full flex flex-col items-center justify-center gap-3 bg-[var(--app-bg)]">
        <Loader2 size={24} className="text-[var(--accent)] animate-spin" />
        <span className="text-[12px] text-[var(--text-muted)]">Collecting price, news and agent analysis…</span>
      </div>
    );
  }

  if (error && !brief) {
    return (
      <div className="h-full flex flex-col items-center justify-center gap-2 bg-[var(--app-bg)] text-[var(--negative)]">
        <AlertTriangle size={28} />
        <p className="text-[13px] font-semibold">{tickerId} data is unavailable</p>
        <p className="text-[11px] text-[var(--text-muted)]">{error}</p>
        <button onClick={load} className="btn-standard mt-3"><RefreshCw size={13} /> Try again</button>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto w-full p-4 md:p-6 lg:p-8 max-w-[1440px] mx-auto animate-fade-in flex flex-col gap-6">
      <header className="surface-card p-5 md:p-6 flex flex-col lg:flex-row lg:items-center justify-between gap-5">
        <div>
          <div className="flex items-center gap-3">
            <div className="h-12 w-12 rounded-[var(--radius-md)] bg-[#1e232b] border border-[var(--border-color)] flex items-center justify-center font-bold text-white">{tickerId.slice(0, 2)}</div>
            <div>
              <div className="flex items-center gap-2"><h1 className="heading-1">{tickerId}</h1><span className="surface-badge">{brief?.price?.fresh ? "Current data" : "Best available data"}</span></div>
              <div className="flex flex-wrap items-center gap-3 mt-1">
                <span className="text-xl font-mono font-semibold text-white">{price ? `$${price.toFixed(2)}` : "Price unavailable"}</span>
                <span className="flex items-center gap-1 text-[13px] font-mono" style={{ color: isUp ? "var(--positive)" : "var(--negative)" }}>
                  {isUp ? <TrendingUp size={14} /> : <TrendingDown size={14} />}{isUp ? "+" : ""}{change.toFixed(2)}%
                </span>
                <span className="surface-badge">Source: {brief?.price?.source || "unknown"}</span>
              </div>
            </div>
          </div>
        </div>
        <button onClick={runFullResearch} disabled={researching} className="btn-primary px-5 py-3 text-[12px] shrink-0">
          {researching ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} />}
          {researching ? "Agents are researching…" : "Run full AI research"}
        </button>
      </header>

      {error && <div className="surface-card p-4 text-[12px] text-amber-200 border-amber-500/20">{error}</div>}

      <div className="grid grid-cols-1 xl:grid-cols-[1fr_360px] gap-6">
        <div className="flex flex-col gap-6">
          <section className="surface-card overflow-hidden">
            <div className="p-5 border-b border-[var(--border-color)] flex items-center gap-2"><BarChart3 size={16} className="text-[var(--accent)]" /><h2 className="heading-3">Price movement</h2></div>
            <div className="p-5 min-h-[380px]">{bars.length ? <TradingViewChart data={bars} ticker={tickerId} /> : <div className="h-[340px] flex items-center justify-center text-[12px] text-[var(--text-muted)]">Chart data is syncing.</div>}</div>
          </section>

          <section className="surface-card overflow-hidden">
            <div className="p-5 border-b border-[var(--border-color)] flex items-center gap-2"><Activity size={16} className="text-[var(--accent)]" /><h2 className="heading-3">What happened & why</h2></div>
            <div className="p-5">
              <p className="text-[14px] text-white leading-relaxed">{why.summary || "AITradra is collecting evidence for this move."}</p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-5">
                {(why.drivers || []).map((driver, index) => (
                  <div key={`${driver.label}-${index}`} className="rounded-[var(--radius-md)] border border-[var(--border-color)] bg-[#171b22] p-4">
                    <div className="flex items-center justify-between gap-2"><span className="text-[11px] font-semibold text-white">{driver.label}</span><span className="surface-badge">{driver.impact}</span></div>
                    <p className="text-[11px] text-[var(--text-muted)] leading-relaxed mt-2">{driver.detail}</p>
                    {driver.url && <a href={driver.url} target="_blank" rel="noreferrer" className="text-[10px] text-[var(--accent)] mt-2 inline-block">Read source →</a>}
                  </div>
                ))}
              </div>
            </div>
          </section>

          <section className="surface-card overflow-hidden">
            <div className="p-5 border-b border-[var(--border-color)] flex items-center gap-2"><BrainCircuit size={16} className="text-[var(--accent)]" /><h2 className="heading-3">What the AI team concluded</h2></div>
            <div className="p-5">
              <div className="prose prose-invert prose-sm max-w-none text-[var(--text-main)]"><ReactMarkdown>{brief?.agent_consensus?.summary || prediction.reason || "Analysis is syncing."}</ReactMarkdown></div>
              {agents.length > 0 && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-5">
                  {agents.slice(0, 10).map((agent, index) => (
                    <div key={`${agent.name}-${index}`} className="rounded-[var(--radius-md)] border border-[var(--border-color)] bg-[#171b22] p-4">
                      <div className="flex items-center justify-between gap-2"><span className="text-[11px] font-semibold text-white">{agent.name}</span><span className="surface-badge">{agent.signal}</span></div>
                      <p className="text-[10px] leading-relaxed text-[var(--text-muted)] mt-2">{agent.summary}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </section>

          <section className="surface-card overflow-hidden">
            <div className="p-5 border-b border-[var(--border-color)] flex items-center gap-2"><Newspaper size={16} className="text-[var(--accent)]" /><h2 className="heading-3">Evidence & latest news</h2></div>
            <div className="divide-y divide-[var(--border-color)]">
              {news.length ? news.map((item, index) => (
                <div key={`${item.headline}-${index}`} className="p-4 flex items-start gap-3">
                  <Newspaper size={14} className="text-[var(--text-muted)] mt-0.5 shrink-0" />
                  <div className="min-w-0 flex-1">
                    <div className="text-[12px] text-white font-medium">{item.headline}</div>
                    {item.summary && <p className="text-[10px] text-[var(--text-muted)] mt-1 line-clamp-2">{item.summary}</p>}
                    <div className="text-[9px] text-[var(--text-muted)] mt-2">{item.source || "Market source"}{item.published_at ? ` • ${String(item.published_at)}` : ""}</div>
                  </div>
                  {item.url && <a href={item.url} target="_blank" rel="noreferrer" className="text-[10px] text-[var(--accent)] shrink-0">Open</a>}
                </div>
              )) : <div className="p-8 text-center text-[11px] text-[var(--text-muted)]">No recent article is attached to this asset yet.</div>}
            </div>
          </section>
        </div>

        <aside className="flex flex-col gap-5">
          <section className="surface-card p-5">
            <div className="flex items-center gap-2 mb-4"><CheckCircle2 size={16} className="text-[var(--accent)]" /><h2 className="heading-3">AI view</h2></div>
            <div className="text-2xl font-bold text-white">{prediction.recommendation || "HOLD"}</div>
            <div className="text-[12px] text-[var(--text-muted)] mt-1">{prediction.direction || "SIDEWAYS"} • {number(prediction.confidence).toFixed(0)}% confidence</div>
            <div className="grid grid-cols-2 gap-3 mt-5">
              <Metric label="Current" value={prediction.current_price ? `$${number(prediction.current_price).toFixed(2)}` : "—"} />
              <Metric label="Model target" value={prediction.target_price ? `$${number(prediction.target_price).toFixed(2)}` : "—"} />
              <Metric label="Expected move" value={`${number(prediction.expected_move_pct).toFixed(2)}%`} />
              <Metric label="Main driver" value={String(prediction.primary_driver || "—").replace(/_/g, " ")} />
            </div>
          </section>

          <section className="surface-card p-5">
            <div className="flex items-center gap-2 mb-4"><Shield size={16} className="text-[var(--warning)]" /><h2 className="heading-3">Risk</h2></div>
            <div className="text-xl font-bold text-white">{risk.level || "MEDIUM"}</div>
            <div className="grid grid-cols-2 gap-3 mt-4">
              <Metric label="Volatility" value={`${number(risk.annualized_volatility).toFixed(1)}%`} />
              <Metric label="Max drawdown" value={`${number(risk.max_drawdown).toFixed(1)}%`} />
              <Metric label="VaR (95%)" value={`${number(risk.var_95).toFixed(1)}%`} />
              <Metric label="Data quality" value={brief?.data_quality?.grade || "—"} />
            </div>
          </section>

          <section className="surface-card p-5">
            <div className="flex items-center gap-2 mb-4"><Clock3 size={16} className="text-[var(--accent)]" /><h2 className="heading-3">What to watch next</h2></div>
            <div className="flex flex-col gap-3">
              {(brief?.what_to_watch_next || []).map((item, index) => <div key={index} className="flex items-start gap-2 text-[11px] text-[var(--text-muted)]"><span className="text-[var(--accent)] font-bold">{index + 1}.</span><span>{item}</span></div>)}
              {!brief?.what_to_watch_next?.length && <p className="text-[11px] text-[var(--text-muted)]">Run full AI research to generate the next checks.</p>}
            </div>
          </section>

          <section className="surface-card p-5">
            <div className="text-[11px] font-semibold text-white mb-3">Recent research history</div>
            <div className="flex flex-col gap-3">
              {history.length ? history.map((item) => (
                <div key={item.id} className="border-l border-[var(--border-color)] pl-3">
                  <div className="text-[10px] text-white">{item.title}</div>
                  <div className="text-[9px] text-[var(--text-muted)] mt-1">{new Date(item.created_at).toLocaleString()}</div>
                </div>
              )) : <p className="text-[10px] text-[var(--text-muted)]">No saved research yet.</p>}
            </div>
          </section>
        </aside>
      </div>

      <div className="surface-card p-4 flex items-start gap-3 text-[11px] text-[var(--text-muted)]">
        <AlertTriangle size={15} className="text-[var(--warning)] shrink-0 mt-0.5" />
        Predictions are evidence-based estimates, not guaranteed outcomes. Review the source data, risk and your own financial situation before trading.
      </div>
    </div>
  );
}

function Metric({ label, value }) {
  return (
    <div className="rounded-[var(--radius-md)] bg-[#171b22] border border-[var(--border-color)] p-3">
      <div className="text-[9px] uppercase tracking-wider text-[var(--text-muted)]">{label}</div>
      <div className="text-[11px] font-semibold text-white mt-1 break-words">{value}</div>
    </div>
  );
}
