import React from 'react';
import {
  Activity,
  BarChart3,
  Layers3,
  ShieldAlert,
  Sparkles,
  TrendingDown,
  TrendingUp,
} from 'lucide-react';

function toNumber(value, fallback = 0) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function clamp(value, min = 0, max = 100) {
  return Math.min(Math.max(value, min), max);
}

function toPercent(value, digits = 1) {
  let parsed = toNumber(value);
  if (parsed !== 0 && Math.abs(parsed) <= 1) {
    parsed *= 100;
  }
  return parsed.toFixed(digits);
}

function formatLevel(value) {
  if (typeof value === 'string' && value.trim()) {
    return value;
  }

  const parsed = toNumber(value, NaN);
  if (!Number.isFinite(parsed)) {
    return 'Awaiting';
  }

  return `$${parsed.toFixed(2)}`;
}

function titleize(value) {
  return String(value || 'level')
    .replace(/[_-]+/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function getTone(signal) {
  switch (String(signal || '').toUpperCase()) {
    case 'BULLISH':
      return {
        text: 'text-emerald-400',
        soft: 'bg-emerald-500/10 border-emerald-500/20',
        fill: 'from-emerald-500 to-cyan-400',
      };
    case 'BEARISH':
      return {
        text: 'text-red-400',
        soft: 'bg-red-500/10 border-red-500/20',
        fill: 'from-red-500 to-amber-400',
      };
    default:
      return {
        text: 'text-amber-300',
        soft: 'bg-amber-500/10 border-amber-500/20',
        fill: 'from-amber-400 to-slate-400',
      };
  }
}

export default function QuanticInsightView({ ticker, quantic }) {
  const hasPayload = Boolean(quantic?.available);
  const smc = quantic?.smc || {};
  const monteCarlo = quantic?.monte_carlo || {};
  const orderBlocks = Array.isArray(smc.institutional_order_blocks)
    ? smc.institutional_order_blocks.slice(0, 4)
    : [];
  const signal = smc.signal || 'NEUTRAL';
  const tone = getTone(signal);

  const smartMoneyScore = clamp(
    toNumber(
      quantic?.smart_money_score,
      signal === 'BULLISH' ? 68 : signal === 'BEARISH' ? 32 : 50,
    ),
  );
  const smcConfidence = clamp(
    toNumber(smc.confidence_pct, toNumber(toPercent(smc.confidence), 0)),
  );
  const orderFlowImbalance = toNumber(smc.order_flow_imbalance);
  const var95 = Math.abs(toNumber(monteCarlo.var_95));
  const cvar95 = Math.abs(toNumber(monteCarlo.cvar_95));
  const maxDrawdown = Math.abs(toNumber(monteCarlo.max_dd));
  const executionMs = toNumber(quantic?.execution_time_ms);
  const distribution = Array.isArray(monteCarlo.distribution)
    ? monteCarlo.distribution.slice(0, 12)
    : [];

  const histogramBars = distribution.length
    ? distribution.map((point) => clamp(Math.abs(toNumber(point)) * 100, 12, 100))
    : [28, 42, 58, 72, 84, 64, 48, 34];

  return (
    <div className="glass-card p-6 bg-white/[0.01] border border-white/[0.08] relative overflow-hidden">
      <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-indigo-500/60 to-transparent" />

      <div className="flex items-start justify-between gap-4 mb-6">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-indigo-500/10 border border-indigo-500/20">
            <Sparkles size={16} className="text-indigo-300" />
          </div>
          <div>
            <h3 className="text-[10px] font-bold uppercase tracking-[0.2em] text-white">
              Quantic Insight Layer
            </h3>
            <p className="text-[9px] text-slate-600 font-bold uppercase tracking-widest mt-1">
              {ticker} smart money and Monte Carlo telemetry
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {quantic?.timeframe && (
            <span className="px-2 py-0.5 rounded-md text-[8px] font-bold uppercase tracking-widest border border-white/[0.08] text-slate-400 bg-white/[0.02]">
              {quantic.timeframe}
            </span>
          )}
          <span
            className={`px-2 py-0.5 rounded-md text-[8px] font-bold uppercase tracking-widest border ${hasPayload && quantic?.success ? tone.soft : 'bg-white/[0.03] border-white/[0.08] text-slate-500'}`}
          >
            {hasPayload ? (quantic?.success ? signal : 'Degraded') : 'Standby'}
          </span>
        </div>
      </div>

      {!hasPayload ? (
        <div className="rounded-2xl border border-dashed border-white/[0.08] bg-black/20 p-5 text-center">
          <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-slate-500">
            Quantic scan syncing
          </p>
          <p className="text-[11px] text-slate-600 mt-2 leading-5">
            Mythic analysis has not published a structured quantic block for this instrument yet.
          </p>
        </div>
      ) : (
        <div className="space-y-5">
          <div className="grid grid-cols-1 sm:grid-cols-[1.2fr_0.8fr] gap-4">
            <div className="rounded-2xl border border-white/[0.08] bg-black/20 p-5">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <Activity size={13} className={tone.text} />
                  <span className="text-[9px] font-bold uppercase tracking-[0.2em] text-slate-500">
                    SMC Gauge
                  </span>
                </div>
                <span className={`text-[11px] font-bold uppercase tracking-widest ${tone.text}`}>
                  {signal}
                </span>
              </div>

              <div className="space-y-3">
                <div>
                  <div className="flex items-center justify-between text-[10px] font-bold uppercase tracking-widest">
                    <span className="text-slate-600">Smart Money Score</span>
                    <span className={tone.text}>{smartMoneyScore.toFixed(0)}/100</span>
                  </div>
                  <div className="mt-2 h-2 rounded-full bg-white/[0.04] overflow-hidden border border-white/[0.04]">
                    <div
                      className={`h-full rounded-full bg-gradient-to-r ${tone.fill}`}
                      style={{ width: `${smartMoneyScore}%` }}
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-3">
                    <div className="text-[8px] font-bold uppercase tracking-[0.2em] text-slate-600">
                      SMC Confidence
                    </div>
                    <div className="mt-2 text-[18px] font-mono font-bold text-white">
                      {smcConfidence.toFixed(0)}%
                    </div>
                  </div>
                  <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-3">
                    <div className="text-[8px] font-bold uppercase tracking-[0.2em] text-slate-600">
                      Flow Imbalance
                    </div>
                    <div className={`mt-2 text-[18px] font-mono font-bold ${orderFlowImbalance >= 0 ? 'text-emerald-300' : 'text-red-300'}`}>
                      {orderFlowImbalance >= 0 ? '+' : ''}
                      {orderFlowImbalance.toFixed(2)}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div className="rounded-2xl border border-white/[0.08] bg-black/20 p-5">
              <div className="flex items-center gap-2 mb-4">
                <ShieldAlert size={13} className="text-amber-300" />
                <span className="text-[9px] font-bold uppercase tracking-[0.2em] text-slate-500">
                  VaR Meter
                </span>
              </div>

              <div className="space-y-4">
                <div>
                  <div className="flex items-center justify-between text-[10px] font-bold uppercase tracking-widest">
                    <span className="text-slate-600">95% Value at Risk</span>
                    <span className="text-red-300">{toPercent(var95, 1)}%</span>
                  </div>
                  <div className="mt-2 h-2 rounded-full bg-white/[0.04] overflow-hidden border border-white/[0.04]">
                    <div
                      className="h-full rounded-full bg-gradient-to-r from-amber-400 via-orange-400 to-red-400"
                      style={{ width: `${clamp(var95 * 10, 6, 100)}%` }}
                    />
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-2">
                  <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-3">
                    <div className="text-[8px] font-bold uppercase tracking-[0.18em] text-slate-600">
                      Sharpe
                    </div>
                    <div className="mt-2 text-[14px] font-mono font-bold text-white">
                      {toNumber(monteCarlo.sharpe).toFixed(2)}
                    </div>
                  </div>
                  <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-3">
                    <div className="text-[8px] font-bold uppercase tracking-[0.18em] text-slate-600">
                      CVaR
                    </div>
                    <div className="mt-2 text-[14px] font-mono font-bold text-white">
                      {toPercent(cvar95, 1)}%
                    </div>
                  </div>
                  <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-3">
                    <div className="text-[8px] font-bold uppercase tracking-[0.18em] text-slate-600">
                      Max DD
                    </div>
                    <div className="mt-2 text-[14px] font-mono font-bold text-white">
                      {toPercent(maxDrawdown, 1)}%
                    </div>
                  </div>
                </div>

                <div className="flex items-end gap-1 h-12">
                  {histogramBars.map((height, index) => (
                    <div
                      // Distribution bars are decorative when raw distribution is unavailable.
                      key={`${index}-${height}`}
                      className="flex-1 rounded-t-md bg-gradient-to-t from-indigo-500/30 via-cyan-400/40 to-white/60"
                      style={{ height: `${height}%` }}
                    />
                  ))}
                </div>
              </div>
            </div>
          </div>

          <div className="rounded-2xl border border-white/[0.08] bg-black/20 p-5">
            <div className="flex items-center justify-between gap-3 mb-4">
              <div className="flex items-center gap-2">
                <Layers3 size={13} className="text-cyan-300" />
                <span className="text-[9px] font-bold uppercase tracking-[0.2em] text-slate-500">
                  Institutional Order Blocks
                </span>
              </div>
              {executionMs > 0 && (
                <span className="text-[8px] font-mono text-slate-600 uppercase tracking-widest">
                  {Math.round(executionMs)}ms
                </span>
              )}
            </div>

            {orderBlocks.length ? (
              <div className="space-y-3">
                {orderBlocks.map((block, index) => (
                  <div
                    key={`${block.label || block.type}-${index}`}
                    className="flex items-center justify-between gap-4 rounded-xl border border-white/[0.06] bg-white/[0.02] px-4 py-3"
                  >
                    <div className="flex items-center gap-3">
                      <div className={`w-2 h-2 rounded-full ${signal === 'BULLISH' ? 'bg-emerald-400' : signal === 'BEARISH' ? 'bg-red-400' : 'bg-amber-300'}`} />
                      <div>
                        <div className="text-[11px] font-bold text-white uppercase tracking-wide">
                          {titleize(block.label || block.type)}
                        </div>
                        <div className="text-[9px] font-bold text-slate-600 uppercase tracking-[0.2em]">
                          {titleize(block.type)}
                        </div>
                      </div>
                    </div>
                    <div className="text-[13px] font-mono font-bold text-white">
                      {formatLevel(block.price)}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="rounded-xl border border-dashed border-white/[0.08] bg-white/[0.02] p-4 text-[11px] text-slate-600 leading-5">
                No institutional blocks were extracted from the current quantic synthesis. The layer is still returning
                Monte Carlo telemetry and summary guidance.
              </div>
            )}
          </div>

          {(quantic?.summary || quantic?.errors?.length) && (
            <div className="rounded-2xl border border-indigo-500/10 bg-indigo-500/[0.04] p-4">
              <div className="flex items-center gap-2 mb-2">
                <BarChart3 size={13} className="text-indigo-300" />
                <span className="text-[9px] font-bold uppercase tracking-[0.2em] text-indigo-200/70">
                  Synthesis Trace
                </span>
              </div>
              <p className="text-[11px] text-slate-300 leading-5">
                {quantic.summary || quantic.errors.join(' | ')}
              </p>
            </div>
          )}
        </div>
      )}

      {quantic?.smc?.signal === 'BULLISH' && (
        <div className="absolute top-6 right-24 hidden sm:flex items-center gap-1 text-[8px] font-bold uppercase tracking-[0.2em] text-emerald-300/80">
          <TrendingUp size={10} />
          Flow Supportive
        </div>
      )}
      {quantic?.smc?.signal === 'BEARISH' && (
        <div className="absolute top-6 right-24 hidden sm:flex items-center gap-1 text-[8px] font-bold uppercase tracking-[0.2em] text-red-300/80">
          <TrendingDown size={10} />
          Flow Defensive
        </div>
      )}
    </div>
  );
}
