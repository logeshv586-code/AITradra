import React, { useEffect, useMemo, useState } from "react";
import {
  Loader2,
  PlayCircle,
  RefreshCw,
  Shield,
  TrendingDown,
  TrendingUp,
  Wallet,
  Zap,
} from "lucide-react";

import { API_BASE } from "../api_config";

const fmtMoney = (value) =>
  new Intl.NumberFormat(undefined, {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2,
  }).format(Number(value || 0));

function StatCard({ label, value, detail, icon: Icon, tone = "indigo" }) {
  const IconComponent = Icon;
  const toneMap = {
    indigo: "border-indigo-400/20 bg-indigo-500/10 text-indigo-300",
    emerald: "border-emerald-400/20 bg-emerald-500/10 text-emerald-300",
    amber: "border-amber-400/20 bg-amber-500/10 text-amber-200",
    red: "border-red-400/20 bg-red-500/10 text-red-300",
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

export default function VirtualPortfolioView({ onSelect }) {
  const [data, setData] = useState(null);
  const [overview, setOverview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [initialBalance, setInitialBalance] = useState("2000");
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [tradeBusy, setTradeBusy] = useState("");
  const [error, setError] = useState("");

  const fetchAll = async ({ refreshing = false } = {}) => {
    if (refreshing) setIsRefreshing(true);
    try {
      const [statusRes, intelRes] = await Promise.all([
        fetch(`${API_BASE}/api/simulation/status`),
        fetch(`${API_BASE}/api/intel/overview`),
      ]);
      const [statusData, intelData] = await Promise.all([statusRes.json(), intelRes.json()]);
      setData(statusData);
      setOverview(intelData);
    } catch (err) {
      console.error("Failed to fetch virtual portfolio data:", err);
      setError("Virtual portfolio data is temporarily unavailable.");
    } finally {
      setLoading(false);
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    fetchAll();
    const interval = setInterval(() => fetchAll({ refreshing: true }), 20000);
    return () => clearInterval(interval);
  }, []);

  const initializeSimulation = async () => {
    try {
      setLoading(true);
      setError("");
      await fetch(`${API_BASE}/api/simulation/init`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ initial_balance: parseFloat(initialBalance) }),
      });
      await fetchAll();
    } catch (err) {
      console.error("Failed to init simulation:", err);
      setLoading(false);
      setError("Could not initialize the virtual portfolio.");
    }
  };

  const handleQuickBuy = async (idea) => {
    if (!data?.initialized || !data?.available_cash || tradeBusy) return;
    const amount = Math.min(Math.max(Math.round((data.available_cash || 0) * 0.1), 100), 1000, data.available_cash);
    if (amount <= 0) return;

    try {
      setTradeBusy(`BUY-${idea.ticker}`);
      setError("");
      const res = await fetch(`${API_BASE}/api/simulation/buy`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ticker: idea.ticker,
          amount,
          prediction: idea.recommendation,
        }),
      });
      const payload = await res.json();
      if (payload?.error) {
        setError(payload.error);
      }
      await fetchAll({ refreshing: true });
    } catch (err) {
      console.error("Failed to execute virtual buy:", err);
      setError("Virtual buy failed.");
    } finally {
      setTradeBusy("");
    }
  };

  const handleQuickSell = async (ticker) => {
    if (!data?.initialized || tradeBusy) return;
    try {
      setTradeBusy(`SELL-${ticker}`);
      setError("");
      const res = await fetch(`${API_BASE}/api/simulation/sell`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ticker }),
      });
      const payload = await res.json();
      if (payload?.error) {
        setError(payload.error);
      }
      await fetchAll({ refreshing: true });
    } catch (err) {
      console.error("Failed to execute virtual sell:", err);
      setError("Virtual sell failed.");
    } finally {
      setTradeBusy("");
    }
  };

  const buyIdeas = useMemo(() => overview?.top_opportunities?.slice(0, 4) || [], [overview]);
  const sellIdeas = useMemo(
    () => (overview?.portfolio_actions || []).filter((item) => ["SELL", "TRIM"].includes(item.action)).slice(0, 4),
    [overview],
  );

  if (loading) {
    return (
      <div className="workspace-canvas flex flex-1 items-center justify-center p-8">
        <div className="surface-card-soft flex flex-col items-center gap-3 px-7 py-6">
          <Loader2 size={24} className="animate-spin text-indigo-400" />
          <span className="text-[8px] font-mono uppercase tracking-[0.34em] text-indigo-300/60">SYNCING PAPER DESK</span>
        </div>
      </div>
    );
  }

  if (!data?.initialized) {
    return (
      <div className="workspace-canvas flex flex-1 items-center justify-center p-8">
        <div className="surface-card max-w-lg w-full p-8 text-center">
          <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-[28px] border border-indigo-400/20 bg-indigo-500/10">
            <Wallet size={36} className="text-indigo-300" />
          </div>

          <h2 className="mt-6 text-3xl font-semibold tracking-tight text-white">Virtual Portfolio</h2>
          <p className="mt-2 text-[11px] font-mono uppercase tracking-[0.28em] text-slate-500">
            Zero-risk execution sandbox
          </p>
          <p className="mx-auto mt-4 max-w-md text-sm leading-relaxed text-slate-400">
            Start a paper account, then use the live intelligence board to simulate entries and exits before risking real capital.
          </p>

          <div className="mt-8 text-left">
            <label className="ml-1 text-[10px] font-black uppercase tracking-[0.26em] text-indigo-300/60">
              Starting Balance
            </label>
            <input
              type="number"
              value={initialBalance}
              onChange={(e) => setInitialBalance(e.target.value)}
              className="mt-2 w-full rounded-2xl border border-white/10 bg-black/40 px-5 py-4 text-lg font-mono text-white shadow-inner focus:border-indigo-500/40 focus:outline-none"
              placeholder="2000"
            />
          </div>

          {error ? <p className="mt-4 text-sm text-red-300">{error}</p> : null}

          <button onClick={initializeSimulation} className="skeuo-button mt-6 w-full h-14 gap-3 text-sm tracking-[0.18em]">
            <PlayCircle size={18} />
            INIT_VIRTUAL_BOOK
          </button>
        </div>
      </div>
    );
  }

  const totalTrades = data.accuracy_metrics?.total_trades || 0;
  const accuracyScore = totalTrades ? Number(data.accuracy_metrics?.accuracy_score || 0).toFixed(1) : "Calibrating";

  return (
    <div className="workspace-canvas flex-1 overflow-y-auto no-scrollbar animate-fade-in">
      <div className="mx-auto flex max-w-[1440px] flex-col gap-4 px-3 py-3 md:px-5 md:py-5 xl:px-6 xl:py-6">
        <header className="surface-card p-4 md:p-5 xl:p-6">
          <div className="grid gap-4 xl:grid-cols-[minmax(0,1.45fr)_360px]">
            <div className="space-y-4">
              <div className="flex items-start gap-3.5">
                <div className="flex h-12 w-12 items-center justify-center rounded-[18px] border border-indigo-400/20 bg-indigo-500/10 shadow-[0_18px_40px_rgba(0,0,0,0.22)]">
                  <Wallet size={20} className="text-indigo-300" />
                </div>

                <div className="space-y-2.5">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="surface-badge">Virtual Portfolio</span>
                    <span className="surface-badge border-emerald-400/20 bg-emerald-500/10 text-emerald-300">
                      {data.positions?.length || 0} positions
                    </span>
                  </div>
                  <div>
                    <h1 className="text-[28px] font-semibold tracking-tight text-white md:text-[34px]">Paper Trading Desk</h1>
                    <p className="mt-1.5 max-w-3xl text-[13px] leading-relaxed text-slate-400 md:text-sm">
                      Virtual execution tied to the live intelligence board so we can test entries, exits, and signal quality without using real money.
                    </p>
                  </div>
                </div>
              </div>

              <div className="grid gap-3 sm:grid-cols-3">
                <div className="surface-card-soft p-3.5">
                  <p className="text-[8px] font-black uppercase tracking-[0.18em] text-slate-500">Balance</p>
                  <div className="mt-2 flex items-end justify-between gap-3">
                    <div>
                      <p className="text-base font-semibold text-white">{fmtMoney(data.total_balance)}</p>
                      <p className="text-[10px] text-slate-400">Current equity</p>
                    </div>
                    <span className={`text-lg font-semibold ${Number(data.total_profit_loss || 0) >= 0 ? "text-emerald-300" : "text-red-300"}`}>
                      {Number(data.profit_loss_percentage || 0) >= 0 ? "+" : ""}
                      {Number(data.profit_loss_percentage || 0).toFixed(2)}%
                    </span>
                  </div>
                </div>

                <div className="surface-card-soft p-3.5">
                  <p className="text-[8px] font-black uppercase tracking-[0.18em] text-slate-500">Cash ready</p>
                  <div className="mt-2 flex items-end justify-between gap-3">
                    <div>
                      <p className="text-base font-semibold text-white">{fmtMoney(data.available_cash)}</p>
                      <p className="text-[10px] text-slate-400">Deployable liquidity</p>
                    </div>
                    <span className="text-lg font-semibold text-indigo-300">{buyIdeas.length} ideas</span>
                  </div>
                </div>

                <div className="surface-card-soft p-3.5">
                  <p className="text-[8px] font-black uppercase tracking-[0.18em] text-slate-500">Model calibration</p>
                  <div className="mt-2 flex items-end justify-between gap-3">
                    <div>
                      <p className="text-base font-semibold text-white">{accuracyScore}</p>
                      <p className="text-[10px] text-slate-400">{totalTrades} closed trades</p>
                    </div>
                    <span className="text-lg font-semibold text-amber-200">{sellIdeas.length} exits</span>
                  </div>
                </div>
              </div>
            </div>

            <div className="surface-card-soft p-4 md:p-5">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-[9px] font-black uppercase tracking-[0.22em] text-slate-500">Desk Controls</p>
                  <h2 className="mt-1 text-lg font-semibold text-white">Quick Refresh</h2>
                </div>
                <button onClick={() => fetchAll({ refreshing: true })} className="skeuo-button h-10 px-4 gap-2 text-[10px] tracking-[0.18em]">
                  <RefreshCw size={14} className={isRefreshing ? "animate-spin" : ""} />
                  SYNC
                </button>
              </div>

              <div className="mt-4 space-y-4">
                <div className="rounded-[18px] border border-white/[0.06] bg-black/20 p-3.5">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <p className="text-[9px] font-black uppercase tracking-[0.18em] text-slate-400">Best current idea</p>
                      <p className="mt-1.5 text-[12px] leading-relaxed text-slate-300">
                        {buyIdeas[0]
                          ? `${buyIdeas[0].ticker} is the strongest current paper-trade candidate with a ${buyIdeas[0].timing_window.toLowerCase()}.`
                          : "No fresh buy setup is strong enough to auto-prioritize right now."}
                      </p>
                    </div>
                    <Zap size={16} className="shrink-0 text-indigo-300" />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-2.5">
                  <div className="rounded-[18px] border border-white/[0.06] bg-black/20 p-3.5">
                    <p className="text-[8px] font-black uppercase tracking-[0.16em] text-slate-500">Invested</p>
                    <p className="mt-1.5 text-xl font-semibold text-white">{fmtMoney(data.invested_amount)}</p>
                  </div>
                  <div className="rounded-[18px] border border-white/[0.06] bg-black/20 p-3.5">
                    <p className="text-[8px] font-black uppercase tracking-[0.16em] text-slate-500">Open P/L</p>
                    <p className={`mt-1.5 text-xl font-semibold ${Number(data.total_profit_loss || 0) >= 0 ? "text-emerald-300" : "text-red-300"}`}>
                      {fmtMoney(data.total_profit_loss)}
                    </p>
                  </div>
                </div>

                {error ? <p className="text-sm text-red-300">{error}</p> : null}
              </div>
            </div>
          </div>
        </header>

        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
          <StatCard
            label="Equity value"
            value={fmtMoney(data.total_balance)}
            detail="Total cash plus marked-to-market position value."
            icon={Wallet}
            tone="indigo"
          />
          <StatCard
            label="Available cash"
            value={fmtMoney(data.available_cash)}
            detail="Unused paper capital ready for the next idea."
            icon={RefreshCw}
            tone="emerald"
          />
          <StatCard
            label="Deployed capital"
            value={fmtMoney(data.invested_amount)}
            detail="Capital currently allocated across open virtual positions."
            icon={TrendingUp}
            tone="indigo"
          />
          <StatCard
            label="Floating P/L"
            value={fmtMoney(data.total_profit_loss)}
            detail={`${Number(data.profit_loss_percentage || 0) >= 0 ? "+" : ""}${Number(data.profit_loss_percentage || 0).toFixed(2)}% on the current book.`}
            icon={Number(data.total_profit_loss || 0) >= 0 ? TrendingUp : TrendingDown}
            tone={Number(data.total_profit_loss || 0) >= 0 ? "emerald" : "red"}
          />
          <StatCard
            label="Signal accuracy"
            value={accuracyScore}
            detail={totalTrades ? `${totalTrades} closed trades scored so far.` : "No closed trades yet, so the score is still calibrating."}
            icon={Shield}
            tone="amber"
          />
        </div>

        <div className="grid gap-4 xl:grid-cols-2">
          <section className="surface-card p-4 md:p-5">
            <div className="flex items-end justify-between gap-3 border-b border-white/[0.08] pb-4">
              <div>
                <p className="text-[9px] font-black uppercase tracking-[0.18em] text-slate-500">Paper Entries</p>
                <h2 className="mt-1 text-lg font-semibold text-white">Top Buy Ideas</h2>
              </div>
              <span className="surface-badge">{buyIdeas.length} live</span>
            </div>

            <div className="mt-4 grid gap-3">
              {buyIdeas.length === 0 ? (
                <EmptyPanel text="No strong buy candidates are available for the paper book right now." />
              ) : (
                buyIdeas.map((idea) => (
                  <article key={idea.ticker} className="surface-card-soft p-4">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-[15px] font-semibold text-white">{idea.ticker}</span>
                          <span className="surface-badge">{idea.recommendation}</span>
                        </div>
                        <p className="mt-1 text-[10px] font-black uppercase tracking-[0.16em] text-slate-500">{idea.sector}</p>
                      </div>
                      <div className="text-right">
                        <div className="text-[18px] font-semibold text-white">{fmtMoney(idea.price)}</div>
                        <div className="text-[10px] font-black text-emerald-300">{Math.round(idea.confidence_score || 0)}% conf</div>
                      </div>
                    </div>

                    <div className="mt-4 rounded-[16px] border border-white/[0.06] bg-black/20 p-3">
                      <p className="text-[8px] font-black uppercase tracking-[0.16em] text-slate-500">Timing Window</p>
                      <p className="mt-1.5 text-[13px] font-semibold text-white">{idea.timing_window}</p>
                      <p className="mt-1.5 text-[12px] leading-relaxed text-slate-400">{idea.timing_note}</p>
                    </div>

                    <div className="mt-4 flex items-center justify-between gap-3">
                      <div className="text-[11px] text-slate-400">
                        Suggested paper allocation: {fmtMoney(Math.min(Math.max(Math.round((data.available_cash || 0) * 0.1), 100), 1000, data.available_cash || 0))}
                      </div>
                      <button
                        onClick={() => handleQuickBuy(idea)}
                        disabled={Boolean(tradeBusy) || !data.available_cash}
                        className="skeuo-button h-10 px-4 gap-2 text-[10px] tracking-[0.18em] disabled:opacity-50"
                      >
                        {tradeBusy === `BUY-${idea.ticker}` ? <Loader2 size={14} className="animate-spin" /> : <TrendingUp size={14} />}
                        PAPER BUY
                      </button>
                    </div>
                  </article>
                ))
              )}
            </div>
          </section>

          <section className="surface-card p-4 md:p-5">
            <div className="flex items-end justify-between gap-3 border-b border-white/[0.08] pb-4">
              <div>
                <p className="text-[9px] font-black uppercase tracking-[0.18em] text-slate-500">Paper Exits</p>
                <h2 className="mt-1 text-lg font-semibold text-white">Sell Or Trim Alerts</h2>
              </div>
              <span className="surface-badge">{sellIdeas.length} live</span>
            </div>

            <div className="mt-4 grid gap-3">
              {sellIdeas.length === 0 ? (
                <EmptyPanel text="No open positions currently require an immediate exit or trim." />
              ) : (
                sellIdeas.map((idea) => (
                  <article key={idea.ticker} className="surface-card-soft p-4">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-[15px] font-semibold text-white">{idea.ticker}</span>
                          <span className="surface-badge">{idea.action}</span>
                        </div>
                        <p className="mt-1 text-[10px] font-black uppercase tracking-[0.16em] text-slate-500">{idea.sector}</p>
                      </div>
                      <div className="text-right">
                        <div className="text-[18px] font-semibold text-white">{fmtMoney(idea.price)}</div>
                        <div className="text-[10px] font-black text-red-300">{idea.risk_level} risk</div>
                      </div>
                    </div>

                    <div className="mt-4 rounded-[16px] border border-white/[0.06] bg-black/20 p-3">
                      <p className="text-[8px] font-black uppercase tracking-[0.16em] text-slate-500">Why exit now</p>
                      <p className="mt-1.5 text-[13px] font-semibold text-white">{idea.timing_window}</p>
                      <p className="mt-1.5 text-[12px] leading-relaxed text-slate-400">{idea.timing_note}</p>
                    </div>

                    <div className="mt-4 flex items-center justify-between gap-3">
                      <div className="text-[11px] text-slate-400">{idea.reasoning_summary}</div>
                      <button
                        onClick={() => handleQuickSell(idea.ticker)}
                        disabled={Boolean(tradeBusy)}
                        className="skeuo-button h-10 px-4 gap-2 text-[10px] tracking-[0.18em] disabled:opacity-50"
                      >
                        {tradeBusy === `SELL-${idea.ticker}` ? <Loader2 size={14} className="animate-spin" /> : <TrendingDown size={14} />}
                        PAPER SELL
                      </button>
                    </div>
                  </article>
                ))
              )}
            </div>
          </section>
        </div>

        <section className="surface-card p-4 md:p-5">
          <div className="flex items-end justify-between gap-3 border-b border-white/[0.08] pb-4">
            <div>
              <p className="text-[9px] font-black uppercase tracking-[0.18em] text-slate-500">Open Positions</p>
              <h2 className="mt-1 text-lg font-semibold text-white">Live Holdings</h2>
            </div>
            <span className="surface-badge">{data.positions?.length || 0} open</span>
          </div>

          <div className="mt-4 overflow-x-auto">
            <table className="w-full border-collapse text-left">
              <thead>
                <tr className="border-b border-white/[0.06] bg-white/[0.02]">
                  <th className="px-4 py-3 text-[9px] font-black uppercase tracking-[0.18em] text-slate-500">Ticker</th>
                  <th className="px-4 py-3 text-[9px] font-black uppercase tracking-[0.18em] text-slate-500">Buy Price</th>
                  <th className="px-4 py-3 text-[9px] font-black uppercase tracking-[0.18em] text-slate-500">Live Price</th>
                  <th className="px-4 py-3 text-[9px] font-black uppercase tracking-[0.18em] text-slate-500">Quantity</th>
                  <th className="px-4 py-3 text-[9px] font-black uppercase tracking-[0.18em] text-slate-500">Current Signal</th>
                  <th className="px-4 py-3 text-[9px] font-black uppercase tracking-[0.18em] text-slate-500">P/L</th>
                  <th className="px-4 py-3 text-[9px] font-black uppercase tracking-[0.18em] text-slate-500">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.05]">
                {(data.positions || []).length === 0 ? (
                  <tr>
                    <td colSpan="7" className="px-4 py-12 text-center text-[11px] text-slate-500">
                      No open paper positions yet. Use the buy ideas above to simulate the first trade.
                    </td>
                  </tr>
                ) : (
                  data.positions.map((position) => (
                    <tr
                      key={position.ticker}
                      className="cursor-pointer transition-colors hover:bg-white/[0.03]"
                      onClick={() => onSelect && onSelect(position.ticker)}
                    >
                      <td className="px-4 py-4">
                        <div>
                          <div className="text-[14px] font-semibold text-white">{position.ticker}</div>
                          <div className="text-[9px] font-black uppercase tracking-[0.16em] text-slate-500">
                            {position.signal_context?.recommendation || "HOLD"} / {position.signal_context?.risk_level || "MEDIUM"}
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-4 text-[12px] font-mono text-slate-300">{fmtMoney(position.buy_price)}</td>
                      <td className="px-4 py-4 text-[12px] font-mono text-white">{fmtMoney(position.current_price || position.buy_price)}</td>
                      <td className="px-4 py-4 text-[12px] font-mono text-slate-400">{Number(position.quantity || 0).toFixed(4)}</td>
                      <td className="px-4 py-4">
                        <div className="space-y-1">
                          <div className="text-[12px] font-semibold text-white">
                            {position.signal_context?.prediction_direction || "SIDEWAYS"} {Number(position.signal_context?.confidence_score || 0) ? `(${Math.round(position.signal_context?.confidence_score || 0)}%)` : ""}
                          </div>
                          <div className="text-[9px] font-black uppercase tracking-[0.16em] text-slate-500">
                            {position.signal_context?.primary_driver || "technical"}
                          </div>
                        </div>
                      </td>
                      <td className={`px-4 py-4 text-[12px] font-semibold ${Number(position.profit_loss || 0) >= 0 ? "text-emerald-300" : "text-red-300"}`}>
                        {fmtMoney(position.profit_loss)}
                      </td>
                      <td className="px-4 py-4">
                        <button
                          onClick={(event) => {
                            event.stopPropagation();
                            handleQuickSell(position.ticker);
                          }}
                          disabled={Boolean(tradeBusy)}
                          className="rounded-full border border-white/[0.08] bg-white/[0.03] px-3 py-1.5 text-[9px] font-black uppercase tracking-[0.16em] text-slate-200 transition hover:border-red-400/30 hover:bg-red-500/10 hover:text-red-200 disabled:opacity-50"
                        >
                          Exit
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>

        <section className="surface-card p-4 md:p-5">
          <div className="flex items-end justify-between gap-3 border-b border-white/[0.08] pb-4">
            <div>
              <p className="text-[9px] font-black uppercase tracking-[0.18em] text-slate-500">Execution History</p>
              <h2 className="mt-1 text-lg font-semibold text-white">Recent Paper Trades</h2>
            </div>
            <span className="surface-badge">{data.history?.length || 0} events</span>
          </div>

          <div className="mt-4 grid gap-3">
            {(data.history || []).length === 0 ? (
              <EmptyPanel text="The paper desk has not executed any virtual trades yet." />
            ) : (
              [...data.history].slice(-8).reverse().map((item, index) => (
                <article key={`${item.ticker}-${index}`} className="surface-card-soft p-4">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="surface-badge">{item.type}</span>
                        <span className="text-[14px] font-semibold text-white">{item.ticker}</span>
                      </div>
                      <p className="mt-2 text-[12px] leading-relaxed text-slate-400">
                        {item.type === "BUY"
                          ? `Entered with ${item.signal_context?.recommendation || item.prediction_at_buy || "HOLD"} context at ${fmtMoney(item.price)}.`
                          : `Exited at ${fmtMoney(item.price)} with realized P/L of ${fmtMoney(item.profit_loss)}.`}
                      </p>
                    </div>
                    <div className="text-right">
                      <div className="text-[13px] font-semibold text-white">{fmtMoney(item.amount)}</div>
                      <div className="mt-1 text-[9px] font-black uppercase tracking-[0.16em] text-slate-500">
                        {new Date(item.timestamp).toLocaleString()}
                      </div>
                    </div>
                  </div>
                </article>
              ))
            )}
          </div>
        </section>
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
