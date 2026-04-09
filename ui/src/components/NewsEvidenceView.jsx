import React, { useEffect, useMemo, useState } from "react";
import {
  Activity,
  AlertTriangle,
  Clock,
  ExternalLink,
  Info,
  Layers,
  Loader2,
  Newspaper,
  Shield,
  TrendingDown,
  TrendingUp,
  Zap,
} from "lucide-react";

import { API_BASE } from "../api_config";

const IMPACT_CONFIG = {
  HIGH: { color: "var(--accent-negative)", icon: AlertTriangle },
  MEDIUM: { color: "#fbbf24", icon: Zap },
  LOW: { color: "var(--text-secondary)", icon: Info },
};

const ACTION_TONES = {
  BUY: "border-emerald-400/20 bg-emerald-500/10 text-emerald-300",
  "HOLD / ADD": "border-sky-400/20 bg-sky-500/10 text-sky-300",
  HOLD: "border-sky-400/20 bg-sky-500/10 text-sky-300",
  SELL: "border-red-400/20 bg-red-500/10 text-red-300",
  TRIM: "border-amber-400/20 bg-amber-500/10 text-amber-200",
  WAIT: "border-white/10 bg-white/[0.04] text-slate-300",
  WATCH: "border-white/10 bg-white/[0.04] text-slate-300",
};

function StatCard({ label, value, detail, icon: Icon, tone = "indigo" }) {
  const IconComponent = Icon;
  const toneMap = {
    indigo: "border-indigo-400/20 bg-indigo-500/10 text-indigo-300",
    emerald: "border-emerald-400/20 bg-emerald-500/10 text-emerald-300",
    amber: "border-amber-400/20 bg-amber-500/10 text-amber-200",
  };

  return (
    <div className="surface-card-soft h-full p-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-[8px] font-black uppercase tracking-[0.18em] text-slate-500">{label}</p>
          <div className="mt-2 text-[28px] font-semibold tracking-tight text-white">{value}</div>
          <p className="mt-1.5 text-[12px] leading-relaxed text-slate-400">{detail}</p>
        </div>
        <div className={`flex h-10 w-10 items-center justify-center rounded-[16px] border ${toneMap[tone] || toneMap.indigo}`}>
          {IconComponent ? <IconComponent size={16} /> : null}
        </div>
      </div>
    </div>
  );
}

function ActionCard({ item, emphasis = "buy" }) {
  const actionTone = ACTION_TONES[item.action] || ACTION_TONES.WATCH;
  const accent =
    emphasis === "buy" ? "from-emerald-400/20 to-transparent" : emphasis === "sell" ? "from-red-400/20 to-transparent" : "from-indigo-400/20 to-transparent";

  return (
    <article className={`surface-card-soft overflow-hidden border border-white/[0.06] bg-[linear-gradient(145deg,rgba(255,255,255,0.03),rgba(255,255,255,0.01))]`}>
      <div className={`h-px w-full bg-gradient-to-r ${accent}`} />
      <div className="space-y-4 p-4">
        <div className="flex items-start justify-between gap-3">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-[15px] font-semibold tracking-tight text-white">{item.ticker}</span>
              <span className={`rounded-full border px-2 py-0.5 text-[8px] font-black uppercase tracking-[0.16em] ${actionTone}`}>
                {item.action}
              </span>
            </div>
            <p className="mt-1 text-[10px] font-black uppercase tracking-[0.16em] text-slate-500">{item.sector}</p>
          </div>
          <div className="text-right">
            <div className="text-[18px] font-semibold text-white">${Number(item.price || 0).toFixed(2)}</div>
            <div className={`text-[10px] font-black ${Number(item.change_pct || 0) >= 0 ? "text-emerald-300" : "text-red-300"}`}>
              {Number(item.change_pct || 0) >= 0 ? "+" : ""}
              {Number(item.change_pct || 0).toFixed(2)}%
            </div>
          </div>
        </div>

        <div className="grid gap-2 sm:grid-cols-3">
          <MetricPill label="Confidence" value={`${Math.round(item.confidence_score || 0)}%`} />
          <MetricPill label="Risk" value={item.risk_level || "MEDIUM"} />
          <MetricPill label="Horizon" value={item.time_horizon || "2 to 6 weeks"} />
        </div>

        <div className="rounded-[16px] border border-white/[0.06] bg-black/20 p-3">
          <p className="text-[8px] font-black uppercase tracking-[0.16em] text-slate-500">Timing Window</p>
          <p className="mt-1.5 text-[13px] font-semibold text-white">{item.timing_window}</p>
          <p className="mt-1.5 text-[12px] leading-relaxed text-slate-400">{item.timing_note}</p>
        </div>

        <div className="space-y-2">
          <p className="text-[9px] font-black uppercase tracking-[0.16em] text-slate-500">Reasoning</p>
          <p className="text-[12px] leading-relaxed text-slate-300">{item.reasoning_summary}</p>
          {item.top_headline ? (
            <p className="text-[11px] italic leading-relaxed text-slate-500">"{item.top_headline}"</p>
          ) : null}
        </div>

        <div className="flex flex-wrap items-center gap-2 text-[9px] font-black uppercase tracking-[0.14em] text-slate-500">
          <span className="surface-badge">{item.recommendation}</span>
          <span className="surface-badge">Driver {item.primary_driver}</span>
          <span className="surface-badge">{item.plugin_alignment || 0} plugin votes</span>
          <span className="surface-badge">{item.stale ? "Stale input" : `${item.freshness_minutes ?? 0}m fresh`}</span>
        </div>
      </div>
    </article>
  );
}

function MetricPill({ label, value }) {
  return (
    <div className="rounded-[14px] border border-white/[0.06] bg-black/25 p-3">
      <p className="text-[8px] font-black uppercase tracking-[0.14em] text-slate-600">{label}</p>
      <p className="mt-1.5 text-[12px] font-semibold text-white">{value}</p>
    </div>
  );
}

export default function NewsEvidenceView() {
  const [overview, setOverview] = useState(null);
  const [fallbackNews, setFallbackNews] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("ALL");

  useEffect(() => {
    let cancelled = false;

    const fetchOverview = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/intel/overview`);
        const data = await res.json();
        if (!cancelled) {
          setOverview(data);
          if (!(data?.news_feed || []).length) {
            const fallbackRes = await fetch(`${API_BASE}/api/market/news-evidence`);
            const fallbackData = await fallbackRes.json();
            setFallbackNews(
              (fallbackData.articles || []).map((article) => ({
                ticker: "GLOBAL",
                headline: article.headline,
                source: article.source,
                published_at: article.published_at,
                sentiment_score: 0,
                impact: article.impact || "LOW",
              }))
            );
          } else {
            setFallbackNews([]);
          }
        }
      } catch (err) {
        console.error("Intel overview fetch failed:", err);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    fetchOverview();
    const interval = setInterval(fetchOverview, 60000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  const filteredNews = useMemo(() => {
    const news = (overview?.news_feed || []).length ? (overview?.news_feed || []) : fallbackNews;
    return filter === "ALL" ? news : news.filter((item) => item.impact === filter);
  }, [fallbackNews, filter, overview]);

  if (loading) {
    return (
      <div className="workspace-canvas flex flex-1 items-center justify-center p-8">
        <div className="surface-card-soft flex flex-col items-center gap-3 px-7 py-6">
          <Loader2 size={24} className="animate-spin text-indigo-400" />
          <span className="text-[8px] font-mono uppercase tracking-[0.34em] text-indigo-300/60">BUILDING INTEL BOARD</span>
        </div>
      </div>
    );
  }

  if (!overview) {
    return (
      <div className="workspace-canvas flex flex-1 items-center justify-center p-8">
        <div className="surface-card-soft max-w-md p-6 text-center">
          <p className="text-sm leading-relaxed text-slate-400">Market intelligence is currently unavailable.</p>
        </div>
      </div>
    );
  }

  const universe = overview.universe || {};
  const freshness = overview.freshness || {};
  const plugins = overview.plugins || {};
  const pluginSources = plugins.sources || [];
  const topOpportunities = overview.top_opportunities || [];
  const sellCandidates = overview.sell_candidates || [];
  const portfolioActions = overview.portfolio_actions || [];

  return (
    <div className="workspace-canvas flex-1 overflow-y-auto no-scrollbar animate-fade-in">
      <div className="mx-auto flex max-w-[1440px] flex-col gap-4 px-3 py-3 md:px-5 md:py-5 xl:px-6 xl:py-6">
        <header className="surface-card p-4 md:p-5 xl:p-6">
          <div className="grid gap-4 xl:grid-cols-[minmax(0,1.5fr)_360px]">
            <div className="space-y-4">
              <div className="flex items-start gap-3.5">
                <div className="flex h-12 w-12 items-center justify-center rounded-[18px] border border-indigo-400/20 bg-indigo-500/10 shadow-[0_18px_40px_rgba(0,0,0,0.22)]">
                  <Newspaper size={20} className="text-indigo-300" />
                </div>

                <div className="space-y-2.5">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="surface-badge">Market Intelligence</span>
                    <span className="surface-badge border-emerald-400/20 bg-emerald-500/10 text-emerald-300">Local-first</span>
                    <span className="surface-badge border-white/[0.08] bg-white/[0.03] text-slate-300">
                      {plugins.summary?.active || 0} plugins active
                    </span>
                  </div>
                  <div>
                    <h1 className="text-[28px] font-semibold tracking-tight text-white md:text-[34px]">
                      Market Intel Board
                    </h1>
                    <p className="mt-1.5 max-w-3xl text-[13px] leading-relaxed text-slate-400 md:text-sm">
                      Transparent buy, watch, and sell timing based on live local intelligence snapshots, agent freshness,
                      and optional plugin overlays.
                    </p>
                  </div>
                </div>
              </div>

              <div className="grid gap-3 sm:grid-cols-3">
                <div className="surface-card-soft p-3.5">
                  <p className="text-[8px] font-black uppercase tracking-[0.18em] text-slate-500">Tracked assets</p>
                  <div className="mt-2 flex items-end justify-between gap-3">
                    <div>
                      <p className="text-base font-semibold text-white">{universe.tracked_assets || 0}</p>
                      <p className="text-[10px] text-slate-400">Live universe</p>
                    </div>
                    <span className="text-lg font-semibold text-indigo-300">{universe.buy_setups || 0} buy</span>
                  </div>
                </div>

                <div className="surface-card-soft p-3.5">
                  <p className="text-[8px] font-black uppercase tracking-[0.18em] text-slate-500">Freshness</p>
                  <div className="mt-2 flex items-end justify-between gap-3">
                    <div>
                      <p className="text-base font-semibold text-white">{freshness.fresh_assets || 0} fresh</p>
                      <p className="text-[10px] text-slate-400">Snapshot health</p>
                    </div>
                    <span className="text-lg font-semibold text-amber-200">{freshness.average_age_minutes || 0}m</span>
                  </div>
                </div>

                <div className="surface-card-soft p-3.5">
                  <p className="text-[8px] font-black uppercase tracking-[0.18em] text-slate-500">Plugin overlays</p>
                  <div className="mt-2 flex items-end justify-between gap-3">
                    <div>
                      <p className="text-base font-semibold text-white">{overview.market_pulse?.plugin_signal_count || 0}</p>
                      <p className="text-[10px] text-slate-400">External local signals</p>
                    </div>
                    <span className="text-lg font-semibold text-emerald-300">{plugins.summary?.total || 0} sources</span>
                  </div>
                </div>
              </div>
            </div>

            <div className="surface-card-soft p-4 md:p-5">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-[9px] font-black uppercase tracking-[0.22em] text-slate-500">Desk Read</p>
                  <h2 className="mt-1 text-lg font-semibold text-white">Signal Snapshot</h2>
                </div>
                <span className="surface-badge">
                  {universe.bullish || 0} up / {universe.bearish || 0} down
                </span>
              </div>

              <div className="mt-4 space-y-4">
                <div className="rounded-[18px] border border-white/[0.06] bg-black/20 p-3.5">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-[8px] font-black uppercase tracking-[0.16em] text-slate-500">Primary desk call</p>
                      <p className="mt-1.5 text-[13px] leading-relaxed text-slate-300">
                        {topOpportunities[0]
                          ? `${topOpportunities[0].ticker} leads the board with a ${topOpportunities[0].timing_window.toLowerCase()} and ${Math.round(topOpportunities[0].confidence_score || 0)}% confidence.`
                          : "Waiting for stronger buy setups to stand out from the watchlist."}
                      </p>
                    </div>
                    <TrendingUp size={16} className="shrink-0 text-emerald-300" />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-2.5">
                  <div className="rounded-[18px] border border-white/[0.06] bg-black/20 p-3.5">
                    <p className="text-[8px] font-black uppercase tracking-[0.16em] text-slate-500">High risk</p>
                    <p className="mt-1.5 text-xl font-semibold text-red-300">{universe.high_risk || 0}</p>
                  </div>
                  <div className="rounded-[18px] border border-white/[0.06] bg-black/20 p-3.5">
                    <p className="text-[8px] font-black uppercase tracking-[0.16em] text-slate-500">Stale assets</p>
                    <p className="mt-1.5 text-xl font-semibold text-amber-200">{universe.stale_assets || 0}</p>
                  </div>
                </div>

                <div className="rounded-[18px] border border-white/[0.06] bg-[linear-gradient(145deg,rgba(99,102,241,0.18),rgba(16,185,129,0.06))] p-3.5">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <p className="text-[9px] font-black uppercase tracking-[0.18em] text-slate-300">Local plugin rail</p>
                      <p className="mt-1.5 text-[12px] leading-relaxed text-slate-200/85">
                        The intel board is ready for local GitHub mirrors like MiroFish exports. Drop JSON signal files into the
                        configured plugin path and they will appear here as overlay votes.
                      </p>
                    </div>
                    <Layers size={16} className="shrink-0 text-indigo-200" />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </header>

        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <StatCard
            label="Buy setups"
            value={topOpportunities.length}
            detail="High-priority entries with supportive timing windows."
            icon={TrendingUp}
            tone="emerald"
          />
          <StatCard
            label="Sell / trim"
            value={sellCandidates.length}
            detail="Held or tracked names where defense matters now."
            icon={TrendingDown}
            tone="amber"
          />
          <StatCard
            label="Portfolio actions"
            value={portfolioActions.length}
            detail="Open virtual positions with current signal context."
            icon={Shield}
            tone="indigo"
          />
          <StatCard
            label="Agent network"
            value={`${overview.agent_network?.summary?.online || 0}/${overview.agent_network?.summary?.total || 0}`}
            detail={`${overview.agent_network?.summary?.stale || 0} stale, ${overview.agent_network?.summary?.error || 0} in error.`}
            icon={Activity}
            tone="amber"
          />
        </div>

        <div className="grid gap-4 xl:grid-cols-2">
          <section className="surface-card p-4 md:p-5">
            <div className="flex items-end justify-between gap-3 border-b border-white/[0.08] pb-4">
              <div>
                <p className="text-[9px] font-black uppercase tracking-[0.18em] text-slate-500">Action Board</p>
                <h2 className="mt-1 text-lg font-semibold text-white">Top Buy Setups</h2>
              </div>
              <span className="surface-badge">{topOpportunities.length} ranked</span>
            </div>
            <div className="mt-4 grid gap-3">
              {topOpportunities.length === 0 ? (
                <EmptyPanel text="No high-confidence buy setups are available right now." />
              ) : (
                topOpportunities.slice(0, 4).map((item) => <ActionCard key={item.ticker} item={item} emphasis="buy" />)
              )}
            </div>
          </section>

          <section className="surface-card p-4 md:p-5">
            <div className="flex items-end justify-between gap-3 border-b border-white/[0.08] pb-4">
              <div>
                <p className="text-[9px] font-black uppercase tracking-[0.18em] text-slate-500">Defense Board</p>
                <h2 className="mt-1 text-lg font-semibold text-white">Sell Or Trim Candidates</h2>
              </div>
              <span className="surface-badge">{sellCandidates.length} ranked</span>
            </div>
            <div className="mt-4 grid gap-3">
              {sellCandidates.length === 0 ? (
                <EmptyPanel text="No immediate sell or trim signals are standing out right now." />
              ) : (
                sellCandidates.slice(0, 4).map((item) => <ActionCard key={item.ticker} item={item} emphasis="sell" />)
              )}
            </div>
          </section>
        </div>

        <div className="grid gap-4 xl:grid-cols-[minmax(0,1.3fr)_minmax(320px,0.7fr)]">
          <section className="surface-card p-4 md:p-5">
            <div className="flex flex-col gap-4 border-b border-white/[0.08] pb-4 md:flex-row md:items-end md:justify-between">
              <div>
                <p className="text-[9px] font-black uppercase tracking-[0.18em] text-slate-500">Evidence Feed</p>
                <h2 className="mt-1 text-lg font-semibold text-white">Catalyst Headlines</h2>
              </div>

              <div className="skeuo-toggle inline-flex h-10 min-w-fit">
                {["ALL", "HIGH", "MEDIUM", "LOW"].map((impact) => (
                  <button
                    key={impact}
                    onClick={() => setFilter(impact)}
                    className={`skeuo-toggle-item !px-6 flex items-center h-full text-[9px] font-bold uppercase tracking-widest transition-all ${
                      filter === impact ? "active" : "text-slate-600 hover:text-slate-400"
                    }`}
                  >
                    {impact}
                  </button>
                ))}
              </div>
            </div>

            <div className="mt-4 grid gap-3">
              {filteredNews.length === 0 ? (
                <EmptyPanel text="No news items match the current impact filter." />
              ) : (
                filteredNews.map((article, index) => {
                  const impact = IMPACT_CONFIG[article.impact] || IMPACT_CONFIG.LOW;
                  const ImpactIcon = impact.icon;
                  return (
                    <article
                      key={`${article.ticker}-${index}`}
                      className="surface-card-soft border border-white/[0.06] p-4"
                      style={{ borderLeft: `2px solid ${impact.color}` }}
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div className="space-y-2 min-w-0">
                          <div className="flex flex-wrap items-center gap-2">
                            <span
                              className="rounded-full border px-2 py-0.5 text-[8px] font-black uppercase tracking-[0.16em]"
                              style={{ background: `${impact.color}12`, borderColor: `${impact.color}30`, color: impact.color }}
                            >
                              <ImpactIcon size={10} className="inline-block mr-1" />
                              {article.impact}
                            </span>
                            <span className="surface-badge">{article.ticker}</span>
                            <span className="text-[9px] font-black uppercase tracking-[0.16em] text-slate-500">
                              {article.source}
                            </span>
                          </div>
                          <h3 className="text-[15px] font-semibold leading-snug text-white">{article.headline}</h3>
                          <div className="flex flex-wrap items-center gap-3 text-[10px] font-mono text-slate-500">
                            <span>Sentiment {Number(article.sentiment_score || 0).toFixed(2)}</span>
                            {article.published_at ? (
                              <span className="inline-flex items-center gap-1">
                                <Clock size={10} /> {article.published_at}
                              </span>
                            ) : null}
                          </div>
                        </div>

                        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-white/[0.08] bg-white/[0.02] text-slate-600">
                          <ExternalLink size={14} />
                        </div>
                      </div>
                    </article>
                  );
                })
              )}
            </div>
          </section>

          <section className="surface-card p-4 md:p-5">
            <div className="border-b border-white/[0.08] pb-4">
              <p className="text-[9px] font-black uppercase tracking-[0.18em] text-slate-500">Plugin Rail</p>
              <h2 className="mt-1 text-lg font-semibold text-white">Local Sources</h2>
            </div>

            <div className="mt-4 space-y-3">
              {pluginSources.length === 0 ? (
                <EmptyPanel text="No local plugins are configured." />
              ) : (
                pluginSources.map((plugin) => (
                  <article key={plugin.id} className="surface-card-soft p-4">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="text-[13px] font-semibold text-white">{plugin.name}</span>
                          <span className="surface-badge">{plugin.type}</span>
                          <span className="surface-badge">{plugin.status}</span>
                        </div>
                        <p className="mt-2 text-[12px] leading-relaxed text-slate-400">{plugin.description}</p>
                      </div>
                      <Layers size={16} className="shrink-0 text-indigo-300" />
                    </div>

                    <div className="mt-3 flex flex-wrap items-center gap-2 text-[9px] font-black uppercase tracking-[0.14em] text-slate-500">
                      <span className="surface-badge">{plugin.mode}</span>
                      <span className="surface-badge">Cadence {plugin.cadence}</span>
                      {plugin.freshness_minutes != null ? <span className="surface-badge">{plugin.freshness_minutes}m old</span> : null}
                    </div>

                    {plugin.path ? (
                      <p className="mt-2 break-all text-[10px] leading-relaxed text-slate-600">{plugin.path}</p>
                    ) : null}
                  </article>
                ))
              )}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}

function EmptyPanel({ text }) {
  return (
    <div className="rounded-[18px] border border-white/[0.06] bg-white/[0.02] p-5 text-sm text-slate-400">
      {text}
    </div>
  );
}
