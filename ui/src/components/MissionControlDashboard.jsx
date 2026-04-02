import React, { useEffect, useMemo, useState } from 'react';
import './MissionControlDashboard.css';
import {
  Activity,
  ArrowDownRight,
  ArrowUpRight,
  BarChart3,
  Clock,
  Cpu,
  Gauge,
  Layers,
  RefreshCw,
  ShieldAlert,
  Signal,
  Target,
  Terminal,
  TrendingUp,
  Zap,
} from 'lucide-react';
import { API_BASE } from '../api_config';
import DeepResearchSuggestions from './DeepResearchSuggestions';

const MOCK_OVERVIEW = {
  universe: { tracked_assets: 0, buy_setups: 0, high_risk: 0, stale_assets: 0 },
  portfolio: { initialized: false, total_balance: 0, profit_loss_percentage: 0 },
  agent_network: { summary: { total: 0, online: 0, stale: 0, error: 0, median_latency_ms: 0 }, agents: [] },
  market_pulse: { top_movers: [] },
  top_opportunities: [],
  sell_candidates: [],
  plugins: { summary: { active: 0 } },
};

function StatTile({ label, value, detail, icon: Icon, tone = 'indigo' }) {
  const IconComponent = Icon;
  const toneMap = {
    indigo: 'border-indigo-400/20 bg-indigo-500/10 text-indigo-300',
    emerald: 'border-emerald-400/20 bg-emerald-500/10 text-emerald-300',
    amber: 'border-amber-400/20 bg-amber-500/10 text-amber-200',
    red: 'border-red-400/20 bg-red-500/10 text-red-300',
  };

  return (
    <div className="surface-card-soft h-full p-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-[8px] font-black uppercase tracking-[0.18em] text-slate-500">{label}</p>
          <div className="mt-2 text-[26px] font-semibold tracking-tight text-white">{value}</div>
          <p className="mt-1.5 text-[12px] leading-relaxed text-slate-400">{detail}</p>
        </div>
        <div className={`flex h-10 w-10 items-center justify-center rounded-[16px] border ${toneMap[tone] || toneMap.indigo}`}>
          {IconComponent ? <IconComponent size={16} /> : null}
        </div>
      </div>
    </div>
  );
}

function Panel({ title, icon: Icon, action, children }) {
  const IconComponent = Icon;
  return (
    <section className="surface-card p-4 md:p-5">
      <div className="flex items-end justify-between gap-3 border-b border-white/[0.08] pb-4">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-[16px] border border-white/[0.08] bg-white/[0.03] text-slate-300">
            {IconComponent ? <IconComponent size={16} /> : null}
          </div>
          <div>
            <p className="text-[9px] font-black uppercase tracking-[0.18em] text-slate-500">Mission Control</p>
            <h2 className="mt-1 text-lg font-semibold text-white">{title}</h2>
          </div>
        </div>
        {action}
      </div>
      <div className="mt-4">{children}</div>
    </section>
  );
}

function AgentRow({ agent }) {
  const statusColor =
    agent.status === 'active'
      ? 'bg-emerald-500'
      : agent.status === 'idle'
        ? 'bg-sky-500'
        : agent.status === 'stale'
          ? 'bg-amber-400'
          : 'bg-red-500';

  return (
    <div className="flex items-center justify-between gap-3 rounded-[18px] border border-white/[0.06] bg-black/20 p-3">
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          <span className={`h-2.5 w-2.5 rounded-full ${statusColor}`} />
          <p className="truncate text-[13px] font-semibold text-white">{agent.name}</p>
        </div>
        <p className="mt-1 truncate text-[10px] font-black uppercase tracking-[0.14em] text-slate-500">
          {agent.current_task || agent.role || 'Awaiting next market task'}
        </p>
      </div>
      <div className="text-right">
        <p className="text-[13px] font-semibold text-white">{agent.health_score || 0}%</p>
        <p className="text-[9px] font-black uppercase tracking-[0.14em] text-slate-500">{agent.status_label || agent.status}</p>
      </div>
    </div>
  );
}

function TerminalLine({ item }) {
  const tone =
    item.type === 'warning'
      ? 'text-amber-200'
      : item.type === 'signal'
        ? 'text-emerald-300'
        : item.type === 'system'
          ? 'text-indigo-300'
          : 'text-slate-300';

  return (
    <div className="flex gap-3 border-b border-white/[0.03] py-2.5 text-[11px] last:border-b-0">
      <span className="w-[64px] shrink-0 font-mono text-slate-600">[{item.time}]</span>
      <span className="w-[72px] shrink-0 font-black uppercase tracking-[0.14em] text-slate-500">{item.sender}</span>
      <span className={`leading-relaxed ${tone}`}>{item.text}</span>
    </div>
  );
}

function ActionItem({ item }) {
  return (
    <article className="surface-card-soft p-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-[14px] font-semibold text-white">{item.ticker}</span>
            <span className="surface-badge">{item.action || item.recommendation}</span>
          </div>
          <p className="mt-1 text-[10px] font-black uppercase tracking-[0.14em] text-slate-500">{item.sector}</p>
        </div>
        <div className="text-right">
          <div className="text-[17px] font-semibold text-white">${Number(item.price || 0).toFixed(2)}</div>
          <div className="text-[10px] font-black text-emerald-300">{Math.round(item.confidence_score || 0)}% conf</div>
        </div>
      </div>
      <div className="mt-3 rounded-[16px] border border-white/[0.06] bg-black/20 p-3">
        <p className="text-[8px] font-black uppercase tracking-[0.14em] text-slate-500">{item.timing_window}</p>
        <p className="mt-1.5 text-[12px] leading-relaxed text-slate-300">{item.timing_note || item.reasoning_summary}</p>
      </div>
    </article>
  );
}

function RiskBar({ label, pct, value, color }) {
  const tone =
    color === 'emerald'
      ? 'bg-emerald-500'
      : color === 'amber'
        ? 'bg-amber-400'
        : color === 'red'
          ? 'bg-red-500'
          : 'bg-indigo-500';

  return (
    <div className="space-y-2 rounded-[18px] border border-white/[0.06] bg-black/20 p-3">
      <div className="flex items-center justify-between gap-3">
        <span className="text-[11px] text-slate-300">{label}</span>
        <span className="text-[11px] font-semibold text-white">{value}</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full border border-white/[0.05] bg-black/40">
        <div className={`h-full rounded-full ${tone}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

function fmtCurrency(value) {
  return new Intl.NumberFormat(undefined, {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(Number(value || 0));
}

export default function MissionControlDashboard({ agentsStatus = [], liveStocks = [] }) {
  const [overview, setOverview] = useState(null);
  const [currentTime, setCurrentTime] = useState(new Date());
  const [activeSection, setActiveSection] = useState('overview');

  useEffect(() => {
    const t = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    let cancelled = false;

    const fetchOverview = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/intel/overview`);
        const data = await res.json();
        if (!cancelled) setOverview(data);
      } catch (err) {
        console.error('Mission Control overview fetch failed:', err);
      }
    };

    fetchOverview();
    const interval = setInterval(fetchOverview, 60000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  const data = overview || MOCK_OVERVIEW;
  const universe = data.universe ?? MOCK_OVERVIEW.universe;
  const portfolio = data.portfolio ?? MOCK_OVERVIEW.portfolio;
  const agentSummary = data.agent_network?.summary ?? MOCK_OVERVIEW.agent_network.summary;

  const agents = useMemo(() => {
    if (data.agent_network?.agents?.length) return data.agent_network.agents;
    if (agentsStatus?.length) return agentsStatus;
    return [];
  }, [data, agentsStatus]);

  const movers = useMemo(() => {
    if (data.market_pulse?.top_movers?.length) return data.market_pulse.top_movers;
    if (liveStocks?.length) {
      return liveStocks.slice(0, 5).map((stock) => ({
        ticker: stock.id || stock.name,
        price: stock.px,
        change_pct: stock.chg,
        sector: stock.sector,
      }));
    }
    return [];
  }, [data, liveStocks]);

  const terminalLogs = useMemo(() => {
    const now = new Date();
    const stamp = (minutesBack) =>
      new Date(now.getTime() - minutesBack * 60000).toLocaleTimeString([], {
        hour: '2-digit',
        minute: '2-digit',
      });

    const logs = [];
    if (data.top_opportunities?.[0]) {
      logs.push({
        sender: 'INTEL',
        text: `${data.top_opportunities[0].ticker} promoted to top buy setup. Window: ${data.top_opportunities[0].timing_window}.`,
        time: stamp(12),
        type: 'signal',
      });
    }
    if (data.sell_candidates?.[0]) {
      logs.push({
        sender: 'RISK',
        text: `${data.sell_candidates[0].ticker} flagged for ${data.sell_candidates[0].action}. ${data.sell_candidates[0].timing_note}`,
        time: stamp(8),
        type: 'warning',
      });
    }
    logs.push({
      sender: 'AGENTS',
      text: `${agentSummary.online || 0} agents online, ${agentSummary.stale || 0} stale, ${agentSummary.error || 0} errors.`,
      time: stamp(5),
      type: 'info',
    });
    logs.push({
      sender: 'PLUGINS',
      text: `${data.plugins?.summary?.active || 0} local plugins active with ${data.market_pulse?.plugin_signal_count || 0} overlay signals.`,
      time: stamp(3),
      type: 'system',
    });
    return logs;
  }, [data, agentSummary]);

  const chartBars = useMemo(() => {
    const seed = data.top_opportunities?.length ? 52 : 38;
    const base = [seed, 60, 54, 68, 72, 66, 78, 85, 81, 93, 95, 103];
    return base.map((value, idx) => value + ((idx % 2 === 0 ? 1 : -1) * Math.round((universe.buy_setups || 1) * 1.5)));
  }, [data, universe]);

  const maxBar = Math.max(...chartBars, 1);
  const aumValue = portfolio.initialized ? fmtCurrency(portfolio.total_balance) : `${universe.tracked_assets || 0} tracked`;
  const aumDetail = portfolio.initialized
    ? `${Number(portfolio.profit_loss_percentage || 0) >= 0 ? '+' : ''}${Number(portfolio.profit_loss_percentage || 0).toFixed(2)}% virtual P/L`
    : 'Virtual portfolio not initialized';
  const riskValue = universe.high_risk ? `${universe.high_risk} high` : universe.tracked_assets ? 'Controlled' : 'Waiting';
  const riskDetail = `${universe.stale_assets || 0} stale inputs across the board`;
  const latencyValue = `${agentSummary.median_latency_ms || 0}ms`;
  const latencyDetail = `${agentSummary.error || 0} active errors`;

  return (
    <div className="workspace-canvas flex-1 overflow-y-auto no-scrollbar animate-fade-in">
      <div className="mx-auto flex max-w-[1440px] flex-col gap-4 px-3 py-3 md:px-5 md:py-5 xl:px-6 xl:py-6">
        <header className="surface-card p-4 md:p-5 xl:p-6">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <span className="surface-badge">Mission Control</span>
                <span className="surface-badge border-emerald-400/20 bg-emerald-500/10 text-emerald-300">Live Engine</span>
              </div>
              <h1 className="mt-3 text-[30px] font-semibold tracking-tight text-white md:text-[36px]">Mission Control</h1>
              <p className="mt-1.5 max-w-3xl text-[13px] leading-relaxed text-slate-400 md:text-sm">
                Unified command view for the watchlist universe, agent freshness, local plugin overlays, and paper-trading posture.
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <div className="flex items-center gap-2 rounded-full border border-white/[0.08] bg-white/[0.03] px-3 py-2 text-[9px] font-black uppercase tracking-[0.18em] text-slate-300">
                <Clock size={12} />
                {currentTime.toLocaleTimeString()}
              </div>
              <button
                onClick={() => setOverview(null)}
                className="rounded-full border border-white/[0.08] bg-white/[0.03] px-3 py-2 text-[9px] font-black uppercase tracking-[0.18em] text-slate-300 transition hover:border-white/[0.18] hover:bg-white/[0.06]"
              >
                Reset Cache
              </button>
            </div>
          </div>
        </header>

        <div className="flex flex-wrap gap-2">
          <button
            className={`rounded-full border px-4 py-2 text-[10px] font-black uppercase tracking-[0.18em] transition ${
              activeSection === 'overview'
                ? 'border-indigo-400/20 bg-indigo-500/10 text-indigo-300'
                : 'border-white/[0.08] bg-white/[0.03] text-slate-400 hover:text-white'
            }`}
            onClick={() => setActiveSection('overview')}
          >
            <Gauge size={13} className="mr-2 inline-block" />
            System Overview
          </button>
          <button
            className={`rounded-full border px-4 py-2 text-[10px] font-black uppercase tracking-[0.18em] transition ${
              activeSection === 'research'
                ? 'border-indigo-400/20 bg-indigo-500/10 text-indigo-300'
                : 'border-white/[0.08] bg-white/[0.03] text-slate-400 hover:text-white'
            }`}
            onClick={() => setActiveSection('research')}
          >
            <Target size={13} className="mr-2 inline-block" />
            Deep Research
          </button>
        </div>

        {activeSection === 'overview' ? (
          <>
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
              <StatTile label="Paper AUM" value={aumValue} detail={aumDetail} icon={BarChart3} tone="indigo" />
              <StatTile label="Agent Network" value={`${agentSummary.online || 0}/${agentSummary.total || agents.length}`} detail={`${agentSummary.stale || 0} stale nodes`} icon={Cpu} tone="emerald" />
              <StatTile label="Risk Exposure" value={riskValue} detail={riskDetail} icon={ShieldAlert} tone="amber" />
              <StatTile label="Latency" value={latencyValue} detail={latencyDetail} icon={Zap} tone="amber" />
            </div>

            <div className="grid gap-4 xl:grid-cols-[minmax(0,1.2fr)_minmax(320px,0.8fr)]">
              <div className="space-y-4">
                <Panel title="Alpha Forecast Engine" icon={TrendingUp}>
                  <div className="flex h-[220px] items-end gap-2 rounded-[18px] border border-white/[0.06] bg-black/20 p-4">
                    {chartBars.map((value, index) => (
                      <div key={index} className="flex h-full flex-1 items-end">
                        <div
                          className="w-full rounded-t-[10px] bg-[linear-gradient(180deg,rgba(99,102,241,0.95),rgba(14,165,233,0.35))]"
                          style={{ height: `${(value / maxBar) * 100}%` }}
                        />
                      </div>
                    ))}
                  </div>
                </Panel>

                <div className="grid gap-4 xl:grid-cols-2">
                  <Panel title="Axiom Terminal" icon={Terminal}>
                    <div className="rounded-[18px] border border-white/[0.06] bg-black/30 p-4 font-mono">
                      {terminalLogs.map((item, index) => (
                        <TerminalLine key={`${item.sender}-${index}`} item={item} />
                      ))}
                    </div>
                  </Panel>

                  <Panel title="Risk Analysis" icon={ShieldAlert}>
                    <div className="space-y-3">
                      <RiskBar label="High-risk assets" pct={universe.tracked_assets ? Math.round(((universe.high_risk || 0) / universe.tracked_assets) * 100) : 0} value={`${universe.high_risk || 0}`} color="red" />
                      <RiskBar label="Buy setups" pct={universe.tracked_assets ? Math.round(((universe.buy_setups || 0) / universe.tracked_assets) * 100) : 0} value={`${universe.buy_setups || 0}`} color="emerald" />
                      <RiskBar label="Stale inputs" pct={universe.tracked_assets ? Math.round(((universe.stale_assets || 0) / universe.tracked_assets) * 100) : 0} value={`${universe.stale_assets || 0}`} color="amber" />
                      <RiskBar label="Plugin overlays" pct={Math.min((data.market_pulse?.plugin_signal_count || 0), 100)} value={`${data.market_pulse?.plugin_signal_count || 0}`} color="indigo" />
                    </div>
                  </Panel>
                </div>
              </div>

              <div className="space-y-4">
                <Panel
                  title="Agent Health Matrix"
                  icon={Layers}
                  action={
                    <button
                      onClick={() => setOverview(null)}
                      className="rounded-full border border-white/[0.08] bg-white/[0.03] p-2 text-slate-400 transition hover:text-white"
                      title="Reset"
                    >
                      <RefreshCw size={12} />
                    </button>
                  }
                >
                  <div className="space-y-3">
                    {agents.length === 0 ? (
                      <div className="rounded-[18px] border border-white/[0.06] bg-white/[0.02] p-4 text-sm text-slate-400">
                        Agent heartbeats will appear here once the pipeline runs.
                      </div>
                    ) : (
                      agents.slice(0, 8).map((agent) => <AgentRow key={agent.id || agent.name} agent={agent} />)
                    )}
                  </div>
                </Panel>

                <Panel title="Market Pulse" icon={Signal}>
                  <div className="space-y-3">
                    {movers.length === 0 ? (
                      <div className="rounded-[18px] border border-white/[0.06] bg-white/[0.02] p-4 text-sm text-slate-400">
                        Market movers will appear here after watchlist data syncs.
                      </div>
                    ) : (
                      movers.slice(0, 6).map((ticker) => {
                        const trend = Number(ticker.change_pct || 0) >= 0 ? 'up' : 'down';
                        return (
                          <div key={ticker.ticker || ticker.symbol} className="flex items-center justify-between rounded-[18px] border border-white/[0.06] bg-black/20 p-3">
                            <div className="flex items-center gap-3">
                              <div className={`flex h-9 w-9 items-center justify-center rounded-[14px] border ${trend === 'up' ? 'border-emerald-400/20 bg-emerald-500/10 text-emerald-300' : 'border-red-400/20 bg-red-500/10 text-red-300'}`}>
                                {trend === 'up' ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}
                              </div>
                              <div>
                                <p className="text-[13px] font-semibold text-white">{ticker.ticker || ticker.symbol}</p>
                                <p className="text-[9px] font-black uppercase tracking-[0.14em] text-slate-500">{ticker.sector || 'Global'}</p>
                              </div>
                            </div>
                            <div className="text-right">
                              <p className="text-[13px] font-semibold text-white">${Number(ticker.price || 0).toFixed(2)}</p>
                              <p className={`text-[10px] font-black ${trend === 'up' ? 'text-emerald-300' : 'text-red-300'}`}>
                                {Number(ticker.change_pct || 0) >= 0 ? '+' : ''}
                                {Number(ticker.change_pct || 0).toFixed(2)}%
                              </p>
                            </div>
                          </div>
                        );
                      })
                    )}
                  </div>
                </Panel>
              </div>
            </div>

            <div className="grid gap-4 xl:grid-cols-2">
              <Panel title="Top Opportunities" icon={TrendingUp}>
                <div className="grid gap-3">
                  {(data.top_opportunities || []).length === 0 ? (
                    <div className="rounded-[18px] border border-white/[0.06] bg-white/[0.02] p-4 text-sm text-slate-400">
                      No top opportunities are ranked yet.
                    </div>
                  ) : (
                    data.top_opportunities.slice(0, 3).map((item) => <ActionItem key={item.ticker} item={item} />)
                  )}
                </div>
              </Panel>

              <Panel title="Sell / Trim Candidates" icon={ShieldAlert}>
                <div className="grid gap-3">
                  {(data.sell_candidates || []).length === 0 ? (
                    <div className="rounded-[18px] border border-white/[0.06] bg-white/[0.02] p-4 text-sm text-slate-400">
                      No immediate defense actions are flagged right now.
                    </div>
                  ) : (
                    data.sell_candidates.slice(0, 3).map((item) => <ActionItem key={item.ticker} item={item} />)
                  )}
                </div>
              </Panel>
            </div>
          </>
        ) : (
          <div className="surface-card p-4 md:p-5 xl:p-6">
            <DeepResearchSuggestions />
          </div>
        )}

        <footer className="surface-card-soft flex flex-col gap-2 px-4 py-3 text-[10px] font-black uppercase tracking-[0.16em] text-slate-500 md:flex-row md:items-center md:justify-between">
          <div className="flex flex-wrap items-center gap-3">
            <span className="inline-flex items-center gap-2"><Activity size={12} /> {universe.tracked_assets || 0} assets tracked</span>
            <span className="inline-flex items-center gap-2"><Cpu size={12} /> {agentSummary.online || 0} agents online</span>
            <span className="inline-flex items-center gap-2"><Layers size={12} /> {data.plugins?.summary?.active || 0} plugins active</span>
          </div>
          <span>AXIOM v4.2 Mission Control</span>
        </footer>
      </div>
    </div>
  );
}
