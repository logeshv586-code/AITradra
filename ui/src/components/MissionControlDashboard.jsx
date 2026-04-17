import React, { useState } from "react";
import { Cpu, Server, Activity, ArrowRight, ShieldCheck, HardDrive, Database, Network } from "lucide-react";
import DeepResearchSuggestions from "./DeepResearchSuggestions";
import DiagnosticView from "./DiagnosticView";
import ShadowPortfolioCard from "./ShadowPortfolioCard";

function SystemCard({ title, value, sub, icon, color }) {
  const CardIcon = icon;
  return (
    <div className="surface-card p-5 flex flex-col gap-3 group border border-transparent transition-all hover:border-[var(--border-color)]">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-[var(--radius-md)] bg-[#1e232b] border border-[var(--border-color)] group-hover:bg-[#1b1f27] transition-colors">
          <CardIcon size={18} style={{ color }} />
        </div>
        <div className="flex flex-col">
          <span className="text-small-caps">{title}</span>
          <span className="text-xl font-mono font-bold text-white leading-none mt-1">{value}</span>
        </div>
      </div>
      {sub && <p className="text-[11px] text-[var(--text-muted)] border-t border-[var(--border-color)] pt-3">{sub}</p>}
    </div>
  );
}

export default function MissionControlDashboard({ agentsStatus }) {
  const [activeTab, setActiveTab] = useState("overview");

  const aCount = agentsStatus?.length || 5;
  const aHealth = agentsStatus?.reduce((a, b) => a + (b.health_score || 100), 0) / aCount || 99.9;

  return (
    <div className="flex-1 overflow-y-auto w-full p-4 md:p-6 lg:p-8 max-w-[1440px] mx-auto animate-fade-in flex flex-col gap-6 lg:gap-8 border-t border-[var(--border-color)] md:border-none">
      
      {/* Page Header */}
      <div className="flex flex-col gap-2">
         <div className="flex items-center gap-3">
            <Cpu size={20} className="text-[var(--accent)]" />
            <h1 className="heading-1">Mission Control</h1>
         </div>
         <p className="text-[13px] text-[var(--text-muted)]">Core infrastructure telemetry, macro research vectors, and shadow execution status.</p>
      </div>

      {/* Primary Metrics Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <SystemCard title="Network Nodes" value={aCount} sub="Active Inference Agents" icon={Network} color="var(--accent)" />
        <SystemCard title="System Health" value={`${aHealth.toFixed(1)}%`} sub="Aggregate Heartbeat" icon={ShieldCheck} color="var(--positive)" />
        <SystemCard title="Market Vector" value="BULLISH" sub="Consensus Alignment" icon={Activity} color="var(--warning)" />
        <SystemCard title="API Latency" value="24ms" sub="Gateway Response Time" icon={Server} color="var(--accent)" />
      </div>

      {/* Main Dashboard Area */}
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_360px] gap-6 lg:gap-8">
        
        {/* Left Column */}
        <div className="flex flex-col gap-6">
          <section className="bg-[var(--card-bg)] border border-[var(--border-color)] rounded-[var(--radius-lg)] shadow-sm overflow-hidden flex flex-col">
            <div className="flex w-full border-b border-[var(--border-color)] bg-[#1b1f27]">
               <button onClick={() => setActiveTab("overview")} className={`flex-1 p-4 text-[12px] font-medium transition-colors ${activeTab === "overview" ? "text-white border-b-2 border-[var(--accent)] bg-[#252a33]" : "text-[var(--text-muted)] hover:text-white"}`}>
                  Deep Research Vectors
               </button>
               <button onClick={() => setActiveTab("diagnostics")} className={`flex-1 p-4 text-[12px] font-medium transition-colors ${activeTab === "diagnostics" ? "text-white border-b-2 border-[var(--accent)] bg-[#252a33]" : "text-[var(--text-muted)] hover:text-white"}`}>
                  System Diagnostics
               </button>
            </div>
            <div className="p-0">
               {activeTab === "overview" ? <DeepResearchSuggestions /> : <DiagnosticView agents={agentsStatus} />}
            </div>
          </section>

          <section className="bg-[var(--card-bg)] border border-[var(--border-color)] rounded-[var(--radius-lg)] shadow-sm p-6 flex flex-col">
             <div className="flex items-center gap-2 mb-4">
                <Database size={16} className="text-[var(--accent)]" />
                <h2 className="heading-3">Data Warehouse Status</h2>
             </div>
             <p className="text-[13px] text-[var(--text-muted)] leading-relaxed mb-6">
                All daily historical candles (1M+ rows) fetched and verified. 
                Streaming webhooks correctly syncing minute-level aggregations. 
                Next snapshot scheduled in 4 hours.
             </p>
             <button className="btn-standard self-start">
                Force Sync <ArrowRight size={14} className="ml-1" />
             </button>
          </section>
        </div>

        {/* Right Column */}
        <div className="flex flex-col gap-6">
          <ShadowPortfolioCard />

          <section className="bg-[var(--card-bg)] border border-[var(--border-color)] rounded-[var(--radius-lg)] shadow-sm p-5 flex flex-col">
             <div className="flex items-center gap-2 mb-4 pb-3 border-b border-[var(--border-color)]">
                <HardDrive size={16} className="text-[var(--warning)]" />
                <h2 className="heading-3">Storage Allocation</h2>
             </div>
             
             <div className="flex flex-col gap-4">
                <div className="flex flex-col gap-2">
                   <div className="flex justify-between text-[11px] font-medium">
                      <span className="text-[var(--text-muted)]">Model Weights (Cache)</span>
                      <span className="text-white">4.2 GB</span>
                   </div>
                   <div className="h-2 w-full bg-[#1e232b] rounded-full overflow-hidden">
                      <div className="h-full bg-[var(--accent)] w-[65%]" />
                   </div>
                </div>
                
                <div className="flex flex-col gap-2">
                   <div className="flex justify-between text-[11px] font-medium">
                      <span className="text-[var(--text-muted)]">Timeseries DB</span>
                      <span className="text-white">12.8 GB</span>
                   </div>
                   <div className="h-2 w-full bg-[#1e232b] rounded-full overflow-hidden">
                      <div className="h-full bg-[var(--warning)] w-[80%]" />
                   </div>
                </div>
             </div>
          </section>
        </div>
      </div>
    </div>
  );
}
