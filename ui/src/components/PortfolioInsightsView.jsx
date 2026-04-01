import React, { useState, useEffect } from "react";
import {
  PieChart,
  Loader2,
  TrendingUp,
  TrendingDown,
  ShieldCheck,
  Shield,
  AlertTriangle,
  Activity,
} from "lucide-react";
import { API_BASE } from "../api_config";

const SECTOR_COLORS = [
  "#6366f1",
  "#8b5cf6",
  "#a855f7",
  "#d946ef",
  "#ec4899",
  "#f43f5e",
  "#ef4444",
  "#f97316",
  "#fb923c",
  "#facc15",
  "#84cc16",
  "#22c55e",
  "#10b981",
  "#14b8a6",
  "#06b6d4",
];

const RISK_ICONS = { LOW: ShieldCheck, MEDIUM: Shield, HIGH: AlertTriangle };
const RISK_COLORS = { LOW: "#10b981", MEDIUM: "#eab308", HIGH: "#ef4444" };

function SectionCard({ eyebrow, title, detail, accent = "indigo", children }) {
  const accentMap = {
    indigo: "from-indigo-500 to-sky-400",
    emerald: "from-emerald-500 to-teal-400",
    amber: "from-amber-400 to-orange-400",
  };

  return (
    <section className="surface-card p-4 md:p-5 xl:p-6">
      <div className="flex flex-col gap-2.5 border-b border-white/[0.08] pb-4 md:flex-row md:items-end md:justify-between">
        <div className="flex items-start gap-3">
          <span className={`mt-1 h-8 w-1 rounded-full bg-gradient-to-b ${accentMap[accent] || accentMap.indigo}`} />
          <div className="space-y-1">
            <p className="text-[9px] font-black uppercase tracking-[0.22em] text-slate-500">{eyebrow}</p>
            <h2 className="text-base font-semibold tracking-tight text-white md:text-lg">{title}</h2>
          </div>
        </div>
        {detail && <p className="max-w-xl text-[13px] leading-relaxed text-slate-400 md:text-right">{detail}</p>}
      </div>
      <div className="mt-4">{children}</div>
    </section>
  );
}

function MetricCard({ label, value, summary, icon: Icon, tone = "indigo", chip }) {
  const toneMap = {
    indigo: "border-indigo-400/20 bg-indigo-500/10 text-indigo-300",
    emerald: "border-emerald-400/20 bg-emerald-500/10 text-emerald-300",
    amber: "border-amber-400/20 bg-amber-500/10 text-amber-200",
    red: "border-red-400/20 bg-red-500/10 text-red-300",
  };

  return (
    <div className="surface-card-soft h-full p-4">
      <div className="flex items-start justify-between gap-3">
        <div className={`flex h-10 w-10 items-center justify-center rounded-[16px] border ${toneMap[tone] || toneMap.indigo}`}>
          <Icon size={16} />
        </div>
        {chip ? <span className="surface-badge">{chip}</span> : null}
      </div>

      <div className="mt-4 space-y-1.5">
        <p className="text-[9px] font-black uppercase tracking-[0.2em] text-slate-500">{label}</p>
        <div className="text-[28px] font-semibold tracking-tight text-white">{value}</div>
        <p className="text-[12px] leading-relaxed text-slate-400">{summary}</p>
      </div>
    </div>
  );
}

function DonutChart({ sectors, totalAssets, dominantSector }) {
  const total = sectors.reduce((sum, sector) => sum + sector.allocation_pct, 0) || 1;
  let cumulativeAngle = 0;
  const size = 184;
  const center = size / 2;
  const radius = 66;
  const thickness = 18;

  const arcs = sectors.slice(0, 10).map((sector, index) => {
    const pct = sector.allocation_pct / total;
    const startAngle = cumulativeAngle;
    cumulativeAngle += pct * 360;
    const endAngle = cumulativeAngle;
    const startRad = (startAngle - 90) * (Math.PI / 180);
    const endRad = (endAngle - 90) * (Math.PI / 180);
    const outerRadius = radius;
    const innerRadius = radius - thickness;
    const largeArc = pct > 0.5 ? 1 : 0;
    const x1 = center + outerRadius * Math.cos(startRad);
    const y1 = center + outerRadius * Math.sin(startRad);
    const x2 = center + outerRadius * Math.cos(endRad);
    const y2 = center + outerRadius * Math.sin(endRad);
    const x3 = center + innerRadius * Math.cos(endRad);
    const y3 = center + innerRadius * Math.sin(endRad);
    const x4 = center + innerRadius * Math.cos(startRad);
    const y4 = center + innerRadius * Math.sin(startRad);
    const path = `M ${x1} ${y1} A ${outerRadius} ${outerRadius} 0 ${largeArc} 1 ${x2} ${y2} L ${x3} ${y3} A ${innerRadius} ${innerRadius} 0 ${largeArc} 0 ${x4} ${y4} Z`;
    const color = SECTOR_COLORS[index % SECTOR_COLORS.length];

    return (
      <path key={sector.sector} d={path} fill={color} fillOpacity={0.85} stroke="rgba(8,12,18,0.9)" strokeWidth="1">
        <title>{sector.sector}: {sector.allocation_pct}%</title>
      </path>
    );
  });

  return (
    <div className="relative flex items-center justify-center">
      <div className="absolute inset-5 rounded-full bg-[radial-gradient(circle,rgba(99,102,241,0.15),transparent_72%)] blur-2xl" />
      <svg width={size} height={size} className="drop-shadow-[0_24px_40px_rgba(0,0,0,0.35)]">
        <circle
          cx={center}
          cy={center}
          r={radius - thickness / 2}
          fill="none"
          stroke="rgba(255,255,255,0.06)"
          strokeWidth={thickness}
        />
        {arcs}
      </svg>

      <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center text-center">
        <span className="text-[9px] font-black uppercase tracking-[0.2em] text-slate-500">Tracked</span>
        <span className="mt-1 text-[34px] font-semibold tracking-tight text-white">{totalAssets}</span>
        {dominantSector && (
          <span className="mt-2.5 rounded-full border border-white/[0.08] bg-white/[0.03] px-2.5 py-1 text-[8px] font-black uppercase tracking-[0.16em] text-slate-300">
            {dominantSector.sector}
          </span>
        )}
      </div>
    </div>
  );
}

export default function PortfolioInsightsView() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/portfolio/insights`);
        const payload = await res.json();
        setData(payload);
      } catch (err) {
        console.error("Portfolio fetch failed:", err);
      }
      setLoading(false);
    };
    fetchData();
  }, []);

  if (loading) {
    return (
      <div className="workspace-canvas flex flex-1 items-center justify-center p-8">
        <div className="surface-card-soft flex flex-col items-center gap-3 px-7 py-6">
          <Loader2 size={24} className="animate-spin text-emerald-400" />
          <span className="text-[8px] font-mono uppercase tracking-[0.34em] text-emerald-300/50">SYNCING PORTFOLIO</span>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="workspace-canvas flex flex-1 items-center justify-center p-8">
        <div className="surface-card-soft max-w-md p-6 text-center">
          <p className="text-sm leading-relaxed text-slate-400">Portfolio intelligence is currently unavailable.</p>
        </div>
      </div>
    );
  }

  const { sectors = [], risk_distribution = {}, aggregate = {}, total_assets = 0 } = data;
  const bullishCount = aggregate.bullish_count || 0;
  const bearishCount = aggregate.bearish_count || 0;
  const bullPct = total_assets ? Math.round((bullishCount / total_assets) * 100) : 0;
  const dominantSector = sectors[0];
  const lowRisk = risk_distribution.LOW || 0;
  const mediumRisk = risk_distribution.MEDIUM || 0;
  const highRisk = risk_distribution.HIGH || 0;
  const highRiskPct = total_assets ? Math.round((highRisk / total_assets) * 100) : 0;
  const lowRiskPct = total_assets ? Math.round((lowRisk / total_assets) * 100) : 0;
  const mediumRiskPct = total_assets ? Math.round((mediumRisk / total_assets) * 100) : 0;
  const riskScore = total_assets ? (lowRisk + mediumRisk * 2 + highRisk * 3) / total_assets : 0;
  const riskStance = riskScore >= 2.25 ? "Elevated" : riskScore >= 1.65 ? "Moderate" : "Controlled";
  const marketTone = bullPct >= 60 ? "Constructive" : bullPct <= 40 ? "Defensive" : "Balanced";
  const avgChange = Number(aggregate.avg_change_pct || 0);

  return (
    <div className="workspace-canvas flex-1 overflow-y-auto no-scrollbar animate-fade-in selection:bg-indigo-500/30">
      <div className="mx-auto flex max-w-[1380px] flex-col gap-4 px-3 py-3 md:px-5 md:py-5 xl:px-6 xl:py-6">
        <header className="surface-card p-4 md:p-5 xl:p-6">
          <div className="grid gap-4 xl:grid-cols-[minmax(0,1.55fr)_320px]">
            <div className="space-y-4">
              <div className="flex items-start gap-3.5">
                <div className="flex h-12 w-12 items-center justify-center rounded-[18px] border border-emerald-400/20 bg-emerald-500/10 shadow-[0_18px_40px_rgba(0,0,0,0.22)]">
                  <PieChart size={20} className="text-emerald-300" />
                </div>

                <div className="space-y-2.5">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="surface-badge">Portfolio Intelligence</span>
                    <span className="surface-badge border-emerald-400/20 bg-emerald-500/10 text-emerald-300">Live Book</span>
                  </div>
                  <div>
                    <h1 className="text-[28px] font-semibold tracking-tight text-white md:text-[34px]">Portfolio Intelligence</h1>
                    <p className="mt-1.5 max-w-3xl text-[13px] leading-relaxed text-slate-400 md:text-sm">
                      Enterprise summary of allocation, breadth, and risk posture across the monitored portfolio.
                    </p>
                  </div>
                </div>
              </div>

              <div className="grid gap-3 sm:grid-cols-3">
                <div className="surface-card-soft p-3.5">
                  <p className="text-[8px] font-black uppercase tracking-[0.18em] text-slate-500">Largest sector</p>
                  <div className="mt-2 flex items-end justify-between gap-3">
                    <div>
                      <p className="text-base font-semibold text-white">{dominantSector?.sector || "N/A"}</p>
                      <p className="text-[10px] text-slate-400">Primary cluster</p>
                    </div>
                    <span className="text-lg font-semibold text-indigo-300">{dominantSector?.allocation_pct || 0}%</span>
                  </div>
                </div>

                <div className="surface-card-soft p-3.5">
                  <p className="text-[8px] font-black uppercase tracking-[0.18em] text-slate-500">Risk posture</p>
                  <div className="mt-2 flex items-end justify-between gap-3">
                    <div>
                      <p className="text-base font-semibold text-white">{riskStance}</p>
                      <p className="text-[10px] text-slate-400">Mix status</p>
                    </div>
                    <span className="text-lg font-semibold text-amber-200">{highRiskPct}%</span>
                  </div>
                </div>

                <div className="surface-card-soft p-3.5">
                  <p className="text-[8px] font-black uppercase tracking-[0.18em] text-slate-500">Signal balance</p>
                  <div className="mt-2 flex items-end justify-between gap-3">
                    <div>
                      <p className="text-base font-semibold text-white">{marketTone}</p>
                      <p className="text-[10px] text-slate-400">Breadth tone</p>
                    </div>
                    <span className="text-lg font-semibold text-emerald-300">{bullPct}%</span>
                  </div>
                </div>
              </div>
            </div>

            <div className="surface-card-soft p-4 md:p-5">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-[9px] font-black uppercase tracking-[0.22em] text-slate-500">Desk Summary</p>
                  <h2 className="mt-1 text-lg font-semibold text-white">Book Snapshot</h2>
                </div>
                <span className="surface-badge">Axiom v4.2</span>
              </div>

              <div className="mt-4 space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-[9px] font-black uppercase tracking-[0.18em] text-slate-500">Active assets</span>
                  <span className="text-[28px] font-semibold text-white">{total_assets}</span>
                </div>

                <div className="space-y-2">
                  <div className="flex items-center justify-between text-[9px] font-black uppercase tracking-[0.16em] text-slate-500">
                    <span>Bull / bear ratio</span>
                    <span className="text-white">{aggregate.bull_bear_ratio || 0}x</span>
                  </div>
                  <div className="h-2 overflow-hidden rounded-full border border-white/[0.05] bg-black/40">
                    <div className="h-full rounded-full bg-gradient-to-r from-emerald-400 via-emerald-500 to-indigo-400" style={{ width: `${bullPct}%` }} />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-2.5">
                  <div className="rounded-[18px] border border-white/[0.06] bg-black/20 p-3.5">
                    <p className="text-[8px] font-black uppercase tracking-[0.16em] text-slate-500">Clusters</p>
                    <p className="mt-1.5 text-xl font-semibold text-white">{sectors.length}</p>
                  </div>
                  <div className="rounded-[18px] border border-white/[0.06] bg-black/20 p-3.5">
                    <p className="text-[8px] font-black uppercase tracking-[0.16em] text-slate-500">Low risk</p>
                    <p className="mt-1.5 text-xl font-semibold text-emerald-300">{lowRiskPct}%</p>
                  </div>
                </div>

                <div className="rounded-[18px] border border-white/[0.06] bg-[linear-gradient(135deg,rgba(99,102,241,0.18),rgba(16,185,129,0.08))] p-3.5">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <p className="text-[9px] font-black uppercase tracking-[0.18em] text-slate-300">Session read</p>
                      <p className="mt-1.5 text-[12px] leading-relaxed text-slate-200/85">
                        {dominantSector
                          ? `${dominantSector.sector} remains the largest concentration while ${marketTone.toLowerCase()} breadth supports the current book.`
                          : "Portfolio holdings will appear here once assets are available."}
                      </p>
                    </div>
                    <Activity size={16} className="shrink-0 text-indigo-200" />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </header>

        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <MetricCard
            label="Total assets"
            value={total_assets}
            summary="Names currently tracked in the active portfolio workspace."
            icon={PieChart}
            tone="indigo"
            chip="LIVE"
          />
          <MetricCard
            label="Average move"
            value={`${avgChange >= 0 ? "+" : ""}${avgChange}%`}
            summary="Mean day-over-day change across the monitored book."
            icon={avgChange >= 0 ? TrendingUp : TrendingDown}
            tone={avgChange >= 0 ? "emerald" : "red"}
            chip="SESSION"
          />
          <MetricCard
            label="Bullish breadth"
            value={`${bullishCount}`}
            summary={`${bullPct}% of tracked assets are currently positive on the session.`}
            icon={TrendingUp}
            tone="emerald"
            chip={`${bullPct}%`}
          />
          <MetricCard
            label="High risk exposure"
            value={`${highRiskPct}%`}
            summary="Holdings above the beta or intraday movement thresholds."
            icon={AlertTriangle}
            tone="amber"
            chip={`${highRisk} assets`}
          />
        </div>

        <div className="grid gap-4 xl:grid-cols-[minmax(0,1.15fr)_minmax(320px,0.85fr)]">
          <SectionCard
            eyebrow="Allocation"
            title="Sector Allocation Structure"
            detail={
              dominantSector
                ? `${dominantSector.sector} leads the book at ${dominantSector.allocation_pct}% of current notional exposure.`
                : "Allocation insights update automatically as the watchlist changes."
            }
            accent="indigo"
          >
            {sectors.length === 0 ? (
              <div className="rounded-[18px] border border-white/[0.06] bg-white/[0.02] p-5 text-sm text-slate-400">
                No allocation data is available yet.
              </div>
            ) : (
              <div className="grid gap-5 xl:grid-cols-[220px_minmax(0,1fr)] xl:items-center">
                <div className="flex justify-center xl:justify-start">
                  <DonutChart sectors={sectors} totalAssets={total_assets} dominantSector={dominantSector} />
                </div>

                <div className="grid gap-3 md:grid-cols-2">
                  {sectors.slice(0, 8).map((sector, index) => (
                    <div key={sector.sector} className="surface-card-soft p-3.5">
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: SECTOR_COLORS[index % SECTOR_COLORS.length] }} />
                            <p className="truncate text-[13px] font-semibold text-white">{sector.sector}</p>
                          </div>
                          <p className="mt-1 text-[9px] font-black uppercase tracking-[0.16em] text-slate-500">
                            {sector.count} holdings
                          </p>
                        </div>
                        <span className="text-base font-semibold text-white">{sector.allocation_pct}%</span>
                      </div>
                      <div className="mt-3 h-1.5 overflow-hidden rounded-full border border-white/[0.05] bg-black/30">
                        <div
                          className="h-full rounded-full transition-all duration-700"
                          style={{
                            width: `${sector.allocation_pct}%`,
                            background: `linear-gradient(90deg, ${SECTOR_COLORS[index % SECTOR_COLORS.length]}, rgba(255,255,255,0.7))`,
                          }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </SectionCard>

          <SectionCard
            eyebrow="Risk"
            title="Risk and Signal Blend"
            detail={`${highRiskPct}% of the book currently sits inside the higher-risk bucket.`}
            accent="amber"
          >
            <div className="space-y-3">
              {["LOW", "MEDIUM", "HIGH"].map((level) => {
                const count = risk_distribution[level] || 0;
                const pct = total_assets ? Math.round((count / total_assets) * 100) : 0;
                const Icon = RISK_ICONS[level];
                const color = RISK_COLORS[level];

                return (
                  <div key={level} className="surface-card-soft p-3.5">
                    <div className="flex items-center justify-between gap-3">
                      <div className="flex items-center gap-3">
                        <div
                          className="flex h-9 w-9 items-center justify-center rounded-[14px] border"
                          style={{ backgroundColor: `${color}12`, borderColor: `${color}30`, color }}
                        >
                          <Icon size={14} />
                        </div>
                        <div>
                          <p className="text-[13px] font-semibold text-white">{level} Risk</p>
                          <p className="text-[9px] font-black uppercase tracking-[0.16em] text-slate-500">
                            {count} assets monitored
                          </p>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className="text-lg font-semibold text-white">{pct}%</p>
                        <p className="text-[9px] font-black uppercase tracking-[0.14em] text-slate-500">Book share</p>
                      </div>
                    </div>
                    <div className="mt-3 h-1.5 overflow-hidden rounded-full border border-white/[0.05] bg-black/30">
                      <div
                        className="relative h-full rounded-full transition-all duration-1000"
                        style={{ width: `${pct}%`, backgroundColor: color }}
                      >
                        <div className="absolute inset-0 bg-white/10 animate-[shimmer_3s_infinite]" />
                      </div>
                    </div>
                  </div>
                );
              })}

              <div className="rounded-[18px] border border-white/[0.06] bg-[linear-gradient(145deg,rgba(99,102,241,0.12),rgba(16,185,129,0.05))] p-4">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="text-[9px] font-black uppercase tracking-[0.18em] text-slate-400">Signal Balance</p>
                    <h3 className="mt-1.5 text-xl font-semibold text-white">{marketTone}</h3>
                    <p className="mt-1.5 max-w-sm text-[12px] leading-relaxed text-slate-300/80">
                      {bullishCount} bullish names versus {bearishCount} bearish names across the current session.
                    </p>
                  </div>
                  <span className="surface-badge">{aggregate.bull_bear_ratio || 0}x ratio</span>
                </div>

                <div className="mt-4 h-2.5 overflow-hidden rounded-full border border-white/[0.05] bg-black/35 p-[2px]">
                  <div className="flex h-full gap-[2px]">
                    <div className="h-full rounded-full bg-emerald-500/90" style={{ width: `${bullPct}%` }} />
                    <div className="h-full rounded-full bg-red-500/75" style={{ width: `${100 - bullPct}%` }} />
                  </div>
                </div>

                <div className="mt-3 grid gap-2.5 sm:grid-cols-3">
                  <div className="rounded-[16px] border border-white/[0.06] bg-black/20 p-3">
                    <p className="text-[8px] font-black uppercase tracking-[0.14em] text-slate-500">Low risk</p>
                    <p className="mt-1.5 text-lg font-semibold text-emerald-300">{lowRiskPct}%</p>
                  </div>
                  <div className="rounded-[16px] border border-white/[0.06] bg-black/20 p-3">
                    <p className="text-[8px] font-black uppercase tracking-[0.14em] text-slate-500">Medium risk</p>
                    <p className="mt-1.5 text-lg font-semibold text-amber-200">{mediumRiskPct}%</p>
                  </div>
                  <div className="rounded-[16px] border border-white/[0.06] bg-black/20 p-3">
                    <p className="text-[8px] font-black uppercase tracking-[0.14em] text-slate-500">High risk</p>
                    <p className="mt-1.5 text-lg font-semibold text-red-300">{highRiskPct}%</p>
                  </div>
                </div>
              </div>
            </div>
          </SectionCard>
        </div>

        <SectionCard
          eyebrow="Holdings"
          title="Sector Ledger"
          detail="Each card groups the primary tickers inside a sector so the desk can review concentration quickly."
          accent="emerald"
        >
          {sectors.length === 0 ? (
            <div className="rounded-[18px] border border-white/[0.06] bg-white/[0.02] p-5 text-sm text-slate-400">
              No sector clusters are available.
            </div>
          ) : (
            <div className="grid gap-3 md:grid-cols-2 2xl:grid-cols-3">
              {sectors.map((sector, index) => (
                <article key={sector.sector} className="surface-card-soft flex h-full flex-col gap-3 p-3.5">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: SECTOR_COLORS[index % SECTOR_COLORS.length] }} />
                        <h3 className="truncate text-[14px] font-semibold text-white">{sector.sector}</h3>
                      </div>
                      <p className="mt-1 text-[9px] font-black uppercase tracking-[0.16em] text-slate-500">
                        {sector.count} assets in cluster
                      </p>
                    </div>
                    <span className="text-base font-semibold text-white">{sector.allocation_pct}%</span>
                  </div>

                  <div className="h-1.5 overflow-hidden rounded-full border border-white/[0.05] bg-black/30">
                    <div
                      className="h-full rounded-full transition-all duration-700"
                      style={{
                        width: `${sector.allocation_pct}%`,
                        background: `linear-gradient(90deg, ${SECTOR_COLORS[index % SECTOR_COLORS.length]}, rgba(255,255,255,0.7))`,
                      }}
                    />
                  </div>

                  <div className="flex flex-wrap gap-1.5">
                    {sector.tickers.map((ticker) => (
                      <span
                        key={ticker}
                        className="rounded-full border border-white/[0.08] bg-black/25 px-2 py-1 text-[9px] font-black uppercase tracking-[0.14em] text-slate-300"
                      >
                        {ticker}
                      </span>
                    ))}
                  </div>
                </article>
              ))}
            </div>
          )}
        </SectionCard>
      </div>
    </div>
  );
}
