import { Shield } from 'lucide-react';

function percent(value) {
  return typeof value === 'number' && Number.isFinite(value) ? `${value.toFixed(2)}%` : 'Unavailable';
}

export default function TradeGuidanceCard({ guidance }) {
  const economics = guidance?.economics || {};
  const action = guidance?.action || 'WAIT';
  return (
    <section className="surface-card p-5" aria-label="Buy and sell guidance">
      <div className="flex items-center gap-2 mb-4"><Shield size={16} className="text-[var(--accent)]" /><h2 className="heading-3">Trade plan</h2></div>
      <p className="text-2xl font-bold text-white">{action}</p>
      <p className="text-[11px] text-[var(--text-muted)] mt-1">Paper evaluation · Live trading requires separate approval and checks</p>
      {Number.isFinite(guidance?.paper_account_value) ? <p className="text-[11px] text-[var(--text-muted)] mt-2">Reviewed hypothetical account: {guidance.paper_account_value.toLocaleString()}</p> : null}
      <div className="grid grid-cols-3 gap-3 mt-4 text-[11px]">
        {[["Entry reference", economics.entry], ["Target", economics.take_profit], ["Stop", economics.stop_loss]].map(([label, value]) => (
          <div key={label}><div className="text-[var(--text-muted)]">{label}</div><div className="mt-1 font-semibold">{Number.isFinite(value) ? value.toLocaleString(undefined, { maximumFractionDigits: 8 }) : 'Unavailable'}</div></div>
        ))}
      </div>
      <dl className="grid grid-cols-2 gap-4 mt-5 text-[12px]">
        <div><dt className="text-[var(--text-muted)]">Net return if target fills</dt><dd className="font-semibold mt-1">{percent(economics.net_target_return_pct)}</dd></div>
        <div><dt className="text-[var(--text-muted)]">Estimated loss at stop</dt><dd className="font-semibold mt-1">{percent(economics.stop_scenario_loss_pct)}</dd></div>
        <div><dt className="text-[var(--text-muted)]">Net reward / risk</dt><dd className="font-semibold mt-1">{Number.isFinite(economics.net_reward_risk) ? `${economics.net_reward_risk.toFixed(2)} : 1` : 'Unavailable'}</dd></div>
        <div><dt className="text-[var(--text-muted)]">Fees + slippage per side</dt><dd className="font-semibold mt-1">{Number.isFinite(economics.fee_bps_per_side) ? `${economics.fee_bps_per_side} + ${economics.slippage_bps_per_side} bps` : 'Unavailable'}</dd></div>
      </dl>
      <p className="text-[10px] text-[var(--text-muted)] mt-3">Percentages are based on position value before leverage. Actual costs vary by venue.</p>
      {action === 'SELL' ? <p className="text-[11px] text-[var(--text-muted)] mt-3">{guidance.sell_meaning}</p> : null}
      <ul className="list-disc pl-4 mt-4 space-y-2 text-[11px] text-[var(--text-muted)]">
        {(guidance?.reasons?.length ? guidance.reasons : !guidance ? ['Run full research to review a complete trade plan.'] : []).map(reason => <li key={reason}>{reason}</li>)}
      </ul>
      <p className="text-[11px] text-[var(--text-muted)] mt-4">{guidance?.notice || 'Profit is not guaranteed. Losses can exceed the planned stop amount.'}</p>
    </section>
  );
}
