import React from 'react';
import { Crosshair, Lock } from 'lucide-react';

export default function ShadowPortfolioCard() {
  return (
    <section className="bg-[var(--card-bg)] border border-[var(--border-color)] rounded-[var(--radius-lg)] shadow-sm p-6 flex flex-col items-center justify-center text-center relative overflow-hidden group">
      <div className="absolute inset-0 bg-gradient-to-br from-[#1b1f27] to-[var(--card-bg)] z-0" />
      
      <div className="relative z-10 flex flex-col items-center mb-6">
        <div className="flex h-14 w-14 items-center justify-center rounded-[var(--radius-lg)] bg-[#1e232b] border border-[var(--border-color)] mb-4 shadow-sm group-hover:border-slate-500 transition-colors">
           <Crosshair size={24} className="text-[var(--text-muted)] group-hover:text-white" />
        </div>
        <h2 className="heading-3 mb-1">Shadow Execution</h2>
        <span className="surface-badge !text-[var(--warning)] !border-[var(--warning)] !border-opacity-30 !bg-[#f59e0b10]">
           OFFLINE
        </span>
      </div>

      <div className="relative z-10 p-4 bg-[var(--app-bg)] w-full rounded-[var(--radius-md)] border border-[var(--border-color)] flex flex-col gap-3">
         <div className="flex items-center gap-2 text-[var(--accent)] text-[12px] font-medium justify-center">
            <Lock size={14} /> Production API Locked
         </div>
         <p className="text-[11px] text-[var(--text-muted)] leading-relaxed">
            Paper-trading engine must complete 7-day validation cycle before live execution via Hyperliquid is unlocked.
         </p>
      </div>
    </section>
  );
}
