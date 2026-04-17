import React, { useState, useEffect } from "react";
import { PieChart, Loader2, Shield, Target } from "lucide-react";
import { API_BASE } from "../api_config";

export default function PortfolioInsightsView() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/portfolio/insights`);
        if (!res.ok) throw new Error("Could not fetch portfolio insights");
        const json = await res.json();
        if (!cancelled) setData(json.portfolio || json);
      } catch (err) {
        if (!cancelled) setError(err.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    load();
    const id = setInterval(load, 30_000);
    return () => { cancelled = true; clearInterval(id); };
  }, []);

  if (loading) return (
     <div className="h-full flex flex-col items-center justify-center gap-4 bg-[var(--app-bg)] w-full">
        <Loader2 size={24} className="text-[var(--accent)] animate-spin" />
        <span className="text-[12px] font-medium text-[var(--text-muted)]">Analyzing Assets...</span>
     </div>
  );

  if (error || !data) return (
     <div className="h-full flex flex-col items-center justify-center gap-2 bg-[var(--app-bg)] w-full text-[var(--negative)]">
        <Shield size={28} className="mb-2" />
        <p className="font-semibold text-[13px]">Portfolio Data Unavailable</p>
        <p className="text-[11px] font-mono opacity-80">{error || "No data"}</p>
     </div>
  );

  const sectors = data.sectors || [];
  const aggregate = data.aggregate || {};
  const riskDistribution = data.risk_distribution || {};
  const totalAssets = data.total_assets || sectors.reduce((sum, sector) => sum + (sector.count || 0), 0);

  return (
    <div className="flex-1 overflow-y-auto w-full p-4 md:p-6 lg:p-8 max-w-[1440px] mx-auto animate-fade-in flex flex-col gap-6 lg:gap-8">

      {/* Page Header */}
      <div className="flex flex-col md:flex-row gap-6 justify-between items-start md:items-center">
         <div className="flex flex-col gap-2">
            <div className="flex items-center gap-3">
               <PieChart size={20} className="text-[var(--accent)]" />
               <h1 className="heading-1">Portfolio Insights</h1>
            </div>
            <p className="text-[13px] text-[var(--text-muted)]">Live position tracking and risk analytics.</p>
         </div>
         
         <div className="flex flex-col items-start md:items-end p-4 border border-[var(--border-color)] bg-[var(--card-bg)] rounded-[var(--radius-lg)] shadow-sm">
            <span className="text-small-caps mb-1">Tracked Assets</span>
            <span className="text-2xl font-mono text-white font-bold">{totalAssets}</span>
         </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_360px] gap-6 lg:gap-8">
         
         {/* Left: Positions Table */}
         <div className="flex flex-col gap-6">
            <section className="bg-[var(--card-bg)] border border-[var(--border-color)] rounded-[var(--radius-lg)] shadow-sm overflow-hidden">
               <div className="p-5 border-b border-[var(--border-color)] flex items-center justify-between bg-[#1b1f27]">
                  <h2 className="heading-3">Sector Allocation</h2>
                  <span className="surface-badge">{sectors.length} Sectors</span>
               </div>
               
               {sectors.length > 0 ? (
                  <div className="overflow-x-auto">
                     <table className="table-standard min-w-[600px]">
                        <thead>
                           <tr>
                              <th className="w-2/5">Sector</th>
                              <th className="w-1/5 text-right">Assets</th>
                              <th className="w-1/5 text-right">Allocation</th>
                              <th className="w-1/5 text-right">Coverage</th>
                           </tr>
                        </thead>
                        <tbody>
                           {sectors.map((sector, i) => {
                              return (
                              <tr key={i}>
                                 <td>
                                    <div className="flex flex-col">
                                       <span className="font-semibold text-white">{sector.sector}</span>
                                       <span className="text-[11px] text-[var(--text-muted)]">{(sector.tickers || []).slice(0, 3).join(", ") || "No symbols"}</span>
                                    </div>
                                 </td>
                                 <td className="text-right font-mono text-[var(--text-muted)]">{sector.count || 0}</td>
                                 <td className="text-right font-mono font-medium text-white">{(sector.allocation_pct || 0).toFixed(1)}%</td>
                                 <td className="text-right font-mono font-bold text-[var(--accent)]">
                                    {(sector.tickers || []).length} tracked
                                 </td>
                              </tr>
                           )})}
                        </tbody>
                     </table>
                  </div>
               ) : (
                  <div className="p-12 text-center text-[13px] text-[var(--text-muted)]">
                     No sector allocation data is available yet.
                  </div>
               )}
            </section>
         </div>

         {/* Right: Risk & Performance */}
         <div className="flex flex-col gap-6">
            <section className="surface-card flex flex-col">
               <div className="p-5 border-b border-[var(--border-color)] flex items-center gap-2 bg-[#1b1f27]">
                  <Target size={16} className="text-[var(--warning)]" />
                  <h2 className="heading-3">Performance Metrics</h2>
               </div>
               
               <div className="p-5 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-1 gap-4">
                  <div className="flex flex-col gap-1 p-4 bg-[#1e232b] rounded-[var(--radius-md)] border border-[var(--border-color)]">
                     <span className="text-small-caps">Average Change</span>
                     <span className="text-[16px] font-mono font-bold text-white whitespace-pre-wrap">{aggregate.avg_change_pct?.toFixed?.(2) || "0.00"}%</span>
                  </div>
                  <div className="flex flex-col gap-1 p-4 bg-[#1e232b] rounded-[var(--radius-md)] border border-[var(--border-color)]">
                     <span className="text-small-caps">Bull/Bear Ratio</span>
                     <span className="text-[16px] font-mono font-bold text-white whitespace-pre-wrap">{aggregate.bull_bear_ratio?.toFixed?.(2) || "0.00"}</span>
                  </div>
               </div>
            </section>

            <section className="surface-card flex flex-col">
               <div className="p-5 border-b border-[var(--border-color)] flex items-center gap-2 bg-[#1b1f27]">
                  <Shield size={16} className="text-[var(--negative)]" />
                  <h2 className="heading-3">Risk Profile</h2>
               </div>
               <div className="p-5 flex flex-col gap-4">
                  {Object.keys(riskDistribution).length > 0 ? (
                     Object.entries(riskDistribution).map(([k, v]) => (
                        <div key={k} className="flex items-center justify-between text-[13px]">
                           <span className="font-medium text-[var(--text-muted)] uppercase tracking-wider">{k}</span>
                           <span className="font-mono text-white font-medium">{v}</span>
                        </div>
                     ))
                  ) : (
                     <p className="text-[12px] text-[var(--text-muted)]">Risk metrics calculating...</p>
                  )}
               </div>
            </section>
         </div>
      </div>
    </div>
  );
}
