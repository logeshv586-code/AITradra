import React, { useEffect, useMemo, useState } from "react";
import {
  Activity,
  AlertTriangle,
  BarChart3,
  Loader2,
  Newspaper,
  Shield,
  TrendingDown,
  TrendingUp,
  Zap,
} from "lucide-react";
import { API_BASE } from "../api_config";
import CandlestickChart from "./CandlestickChart";
import QuanticInsightView from "./QuanticInsightView";

function toNumber(value, fallback = 0) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function normalizeBars(bars = []) {
  return bars
    .map((bar, index) => ({
      t: bar.t || bar.date || `T${index + 1}`,
      o: toNumber(bar.o ?? bar.open),
      h: toNumber(bar.h ?? bar.high),
      l: toNumber(bar.l ?? bar.low),
      c: toNumber(bar.c ?? bar.close),
      v: toNumber(bar.v ?? bar.volume),
    }))
    .filter((bar) => bar.c > 0);
}

function formatCompactNumber(value) {
  const amount = toNumber(value);
  if (!amount) return "n/a";
  if (amount >= 1_000_000_000) return `$${(amount / 1_000_000_000).toFixed(1)}B`;
  if (amount >= 1_000_000) return `${(amount / 1_000_000).toFixed(1)}M`;
  return amount.toLocaleString();
}

export default function StockDetailView({ ticker }) {
  const tickerId = String(ticker || "").toUpperCase();
  const [stockData, setStockData] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!tickerId) return;

    let cancelled = false;
    const load = async () => {
      setLoading(true);
      setError("");
      try {
        // Step 1: Load stock data FIRST (fast endpoint, no LLM required)
        const stockRes = await fetch(`${API_BASE}/api/stock/${tickerId}`);
        if (!stockRes.ok) {
          throw new Error(`Failed to load ${tickerId} terminal data`);
        }
        const stockPayload = await stockRes.json();
        if (!cancelled) {
          setStockData(stockPayload);
          setLoading(false); // Render terminal immediately with stock data
        }

        // Step 2: Load analysis in background (slow LLM pipeline — don't block UI)
        try {
          const controller = new AbortController();
          const timeout = setTimeout(() => controller.abort(), 120000); // 2 min max
          const analysisRes = await fetch(`${API_BASE}/api/stock/${tickerId}/analysis`, {
            signal: controller.signal,
          });
          clearTimeout(timeout);
          if (analysisRes.ok && !cancelled) {
            const analysisPayload = await analysisRes.json();
            setAnalysis(analysisPayload);
          }
        } catch (analysisErr) {
          // Analysis is non-critical — terminal still works without it
          console.warn(`Analysis lazy-load for ${tickerId}:`, analysisErr.name === 'AbortError' ? 'timed out' : analysisErr.message);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err.message || "Terminal data unavailable");
          setLoading(false);
        }
      }
    };

    load();
    return () => {
      cancelled = true;
    };
  }, [tickerId]);

  const priceData = useMemo(() => stockData?.price_data || {}, [stockData]);
  const intelligence = analysis || stockData?.intelligence || {};
  const intelligenceProfile =
    stockData?.intelligence_profile ||
    intelligence.intelligence_profile ||
    {};
  const adaptivePlan =
    stockData?.adaptive_plan ||
    intelligence.adaptive_plan ||
    intelligenceProfile.adaptive_plan ||
    {};
  const dataQuality = intelligenceProfile.data_quality || {};
  const modelRouter = intelligenceProfile.model_router || {};
  const chartData = useMemo(
    () => normalizeBars(stockData?.ohlcv_history || priceData.ohlcv || []),
    [stockData, priceData],
  );
  const news = stockData?.news || intelligence.top_headlines || [];
  const direction = intelligence.prediction_direction || intelligence.consensus || "SIDEWAYS";
  const confidence = toNumber(intelligence.confidence_score ?? intelligence.confidence);
  const recommendation = intelligence.recommendation || "HOLD";
  const expectedMove = toNumber(intelligence.expected_move_percent);
  const riskLevel = intelligence.risk_level || "MEDIUM";
  const reasoningSummary =
    intelligence.response ||
    intelligence.reasoning_summary ||
    intelligence.sections?.verdict ||
    "Mythic analysis is synchronizing for this instrument.";
  const sections = intelligence.sections || {};
  const providerLabel = modelRouter.last_provider_used || modelRouter.active_provider || "adaptive";

  const price = toNumber(priceData.px);
  const change = toNumber(priceData.pct_chg ?? priceData.chg);
  const isUp = change >= 0;
  const signalTone =
    direction === "UP"
      ? "var(--positive)"
      : direction === "DOWN"
        ? "var(--negative)"
        : "var(--warning)";

  if (loading) {
    return (
      <div className="h-full flex flex-col items-center justify-center gap-4 bg-[var(--app-bg)] w-full">
        <Loader2 size={24} className="text-[var(--accent)] animate-spin" />
        <span className="text-[12px] font-medium text-[var(--text-muted)]">
          Synchronizing stock terminal...
        </span>
      </div>
    );
  }

  if (error || !stockData) {
    return (
      <div className="h-full flex flex-col items-center justify-center gap-2 bg-[var(--app-bg)] w-full text-[var(--negative)]">
        <AlertTriangle size={28} className="mb-2" />
        <p className="font-semibold text-[13px]">Stock Terminal Offline</p>
        <p className="text-[11px] font-mono opacity-80">{error || "No data"}</p>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto w-full p-4 md:p-6 lg:p-8 max-w-[1440px] mx-auto animate-fade-in flex flex-col gap-6 lg:gap-8">
      <header className="surface-card p-6 flex flex-col lg:flex-row lg:items-center justify-between gap-6">
        <div className="flex items-center gap-4">
          <div className="flex h-14 w-14 items-center justify-center rounded-[var(--radius-md)] bg-[#1e232b] border border-[var(--border-color)] text-white font-bold text-lg">
            {tickerId.slice(0, 2)}
          </div>
          <div className="flex flex-col">
            <div className="flex items-center gap-3">
              <h1 className="heading-1">{tickerId}</h1>
              <span className="surface-badge">{stockData?.name || "Equity"}</span>
            </div>
            <div className="flex items-center gap-4 mt-1">
              <span className="font-mono text-xl font-semibold text-white">${price.toFixed(2)}</span>
              <span className="flex items-center gap-1 text-[13px] font-mono font-medium" style={{ color: isUp ? "var(--positive)" : "var(--negative)" }}>
                {isUp ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
                {isUp ? "+" : ""}{change.toFixed(2)}%
              </span>
              <span className="surface-badge">{priceData.source_used || "syncing"}</span>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {[
            { label: "Volume", value: formatCompactNumber(priceData.volume) },
            { label: "52W High", value: priceData.week52_high ? `$${toNumber(priceData.week52_high).toFixed(2)}` : "n/a" },
            { label: "52W Low", value: priceData.week52_low ? `$${toNumber(priceData.week52_low).toFixed(2)}` : "n/a" },
            { label: "Market Cap", value: formatCompactNumber(priceData.mktcap) },
          ].map((item) => (
            <div key={item.label} className="flex flex-col border-l border-[var(--border-color)] pl-4">
              <span className="text-small-caps">{item.label}</span>
              <span className="font-mono text-[14px] text-white mt-1">{item.value}</span>
            </div>
          ))}
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_360px] gap-6 lg:gap-8">
        <div className="flex flex-col gap-6 lg:gap-8">
          <section className="surface-card flex flex-col">
            <div className="p-5 border-b border-[var(--border-color)] flex items-center gap-2 bg-[#1b1f27]">
              <BarChart3 size={16} className="text-[var(--accent)]" />
              <h2 className="heading-3">Price Action</h2>
            </div>
            <div className="p-5 h-[340px] md:h-[400px]">
              <CandlestickChart data={chartData} />
            </div>
          </section>

          <section className="surface-card flex flex-col">
            <div className="p-5 border-b border-[var(--border-color)] flex items-center gap-2 bg-[#1b1f27]">
              <Activity size={16} className="text-[var(--accent)]" />
              <h2 className="heading-3">Key Fundamentals</h2>
            </div>
            <div className="p-6 grid grid-cols-2 md:grid-cols-4 gap-6">
              {[
                { label: "P/E", value: priceData.pe ? Number(priceData.pe).toFixed(1) : "n/a" },
                { label: "Avg Vol", value: formatCompactNumber(priceData.avg_volume) },
                { label: "Open", value: priceData.open ? `$${toNumber(priceData.open).toFixed(2)}` : "n/a" },
                { label: "Close", value: priceData.close ? `$${toNumber(priceData.close).toFixed(2)}` : "n/a" },
                { label: "Signal", value: recommendation },
                { label: "Risk", value: riskLevel },
                { label: "Move", value: `${expectedMove.toFixed(2)}%` },
                { label: "Confidence", value: `${confidence.toFixed(0)}%` },
              ].map((metric) => (
                <div key={metric.label} className="flex flex-col gap-1">
                  <span className="text-small-caps">{metric.label}</span>
                  <span className="text-[13px] text-white font-medium">{metric.value}</span>
                </div>
              ))}
            </div>
          </section>

          <section className="surface-card flex flex-col">
            <div className="p-5 border-b border-[var(--border-color)] flex items-center gap-2 bg-[#1b1f27]">
              <Zap size={16} className="text-[var(--accent)]" />
              <h2 className="heading-3">Mythic Synthesis</h2>
            </div>
            <div className="p-6 flex flex-col gap-4">
              <p className="text-[13px] leading-relaxed text-[var(--text-main)]">{reasoningSummary}</p>
              {Object.entries(sections).length > 0 && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {Object.entries(sections).slice(0, 4).map(([key, value]) => (
                    <div key={key} className="p-4 bg-[#1e232b] rounded-[var(--radius-md)] border border-[var(--border-color)]">
                      <p className="text-small-caps mb-2">{key.replace(/_/g, " ")}</p>
                      <p className="text-[12px] text-[var(--text-muted)] leading-relaxed">{value}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </section>
        </div>

        <div className="flex flex-col gap-6">
          <section className="surface-card flex flex-col">
            <div className="p-5 border-b border-[var(--border-color)] flex items-center gap-2 bg-[#1b1f27]">
              <Zap size={16} className="text-[var(--warning)]" />
              <h2 className="heading-3">Signal Stack</h2>
            </div>
            <div className="p-6 flex flex-col gap-5">
              <div className="flex items-center justify-between">
                <span className="text-small-caps">Direction</span>
                <span className="font-mono font-bold" style={{ color: signalTone }}>{direction}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-small-caps">Recommendation</span>
                <span className="font-mono font-bold text-white">{recommendation}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-small-caps">Expected Move</span>
                <span className="font-mono font-bold text-white">{expectedMove.toFixed(2)}%</span>
              </div>
              <div className="space-y-2">
                <div className="flex justify-between items-center text-[11px]">
                  <span className="font-medium text-[var(--text-muted)] uppercase tracking-wider">Confidence</span>
                  <span className="font-mono text-white">{confidence.toFixed(0)}%</span>
                </div>
                <div className="h-1.5 w-full bg-[#1e232b] rounded-full overflow-hidden">
                  <div className="h-full rounded-full" style={{ width: `${Math.min(confidence, 100)}%`, backgroundColor: signalTone }} />
                </div>
              </div>
            </div>
          </section>

          <section className="surface-card flex flex-col">
            <div className="p-5 border-b border-[var(--border-color)] flex items-center gap-2 bg-[#1b1f27]">
              <Activity size={16} className="text-[var(--accent)]" />
              <h2 className="heading-3">Adaptive Engine</h2>
            </div>
            <div className="p-6 flex flex-col gap-4">
              <div className="grid grid-cols-2 gap-3">
                <div className="flex flex-col gap-1">
                  <span className="text-small-caps">Data Grade</span>
                  <span className="font-mono text-white">{dataQuality.grade || "LOW"}</span>
                </div>
                <div className="flex flex-col gap-1 text-right">
                  <span className="text-small-caps">Model Route</span>
                  <span className="font-mono text-white">{providerLabel}</span>
                </div>
              </div>
              <div className="rounded-[var(--radius-md)] border border-[var(--border-color)] bg-[#1e232b] p-4">
                <div className="flex items-center justify-between gap-3 mb-3">
                  <span className="text-small-caps">Mode</span>
                  <span className="font-mono text-[11px] text-white uppercase">{adaptivePlan.mode || "confirmation_wait"}</span>
                </div>
                <div className="flex flex-col gap-2">
                  {(adaptivePlan.next_actions || []).slice(0, 3).map((action) => (
                    <div key={action} className="flex items-start gap-2 text-[11px] leading-relaxed text-[var(--text-muted)]">
                      <div className="mt-1.5 h-1.5 w-1.5 rounded-full bg-[var(--accent)] shrink-0" />
                      <span>{action}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </section>

          <section className="surface-card flex flex-col">
            <div className="p-5 border-b border-[var(--border-color)] flex items-center gap-2 bg-[#1b1f27]">
              <Shield size={16} className="text-[var(--accent)]" />
              <h2 className="heading-3">Risk Overview</h2>
            </div>
            <div className="p-6 flex flex-col gap-3">
              <div className="flex items-center justify-between text-[13px]">
                <span className="font-medium text-[var(--text-muted)] uppercase tracking-wider">Risk Level</span>
                <span className="font-mono text-white">{riskLevel}</span>
              </div>
              <div className="flex items-center justify-between text-[13px]">
                <span className="font-medium text-[var(--text-muted)] uppercase tracking-wider">Primary Driver</span>
                <span className="font-mono text-white">{intelligence.primary_driver || "technical"}</span>
              </div>
              <div className="flex items-center justify-between text-[13px]">
                <span className="font-medium text-[var(--text-muted)] uppercase tracking-wider">Headline Count</span>
                <span className="font-mono text-white">{news.length}</span>
              </div>
            </div>
          </section>

          <QuanticInsightView ticker={tickerId} quantic={analysis?.quantic || intelligence.quantic} />

          <section className="surface-card flex flex-col flex-1">
            <div className="p-5 border-b border-[var(--border-color)] flex items-center justify-between bg-[#1b1f27]">
              <div className="flex items-center gap-2">
                <Newspaper size={16} className="text-[var(--accent)]" />
                <h2 className="heading-3">Latest News</h2>
              </div>
              <span className="surface-badge">{news.length}</span>
            </div>
            <div className="p-4 flex flex-col gap-3 max-h-[400px] overflow-y-auto no-scrollbar">
              {news.length === 0 ? (
                <p className="py-8 text-center text-[12px] text-[var(--text-muted)]">No recent news available.</p>
              ) : (
                news.slice(0, 8).map((item, index) => (
                  <a
                    key={`${item.headline || item.title || "news"}-${index}`}
                    href={item.url || "#"}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="group flex flex-col gap-2 p-3 rounded-[var(--radius-md)] border border-transparent hover:border-[var(--border-color)] hover:bg-[#1e232b] transition-colors"
                  >
                    <p className="text-[12px] font-medium text-[var(--text-main)] leading-snug line-clamp-2 group-hover:text-[var(--accent)] transition-colors">
                      {item.headline || item.title}
                    </p>
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] text-[var(--text-muted)]">{item.source || "Feed"}</span>
                      {item.published_at && (
                        <span className="text-[10px] text-[var(--text-muted)]">{item.published_at}</span>
                      )}
                    </div>
                  </a>
                ))
              )}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
