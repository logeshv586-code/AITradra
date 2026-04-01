import React, { useState, useEffect } from "react";
import { Newspaper, ExternalLink, Loader2, Filter, AlertTriangle, Info, Zap, Globe, Activity } from "lucide-react";

import { API_BASE } from "../api_config";

const IMPACT_CONFIG = {
  HIGH:   { color: "var(--accent-negative)", icon: AlertTriangle },
  MEDIUM: { color: "#fbbf24", icon: Zap },
  LOW:    { color: "var(--text-secondary)", icon: Info },
};

export default function NewsEvidenceView() {
  const [articles, setArticles] = useState([]);
  const [stats, setStats] = useState({});
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("ALL");

  useEffect(() => {
    const fetchNews = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/market/news-evidence`);
        const data = await res.json();
        setArticles(data.articles || []);
        setStats({ total: data.total_cached, high: data.high_impact, medium: data.medium_impact });
      } catch (err) {
        console.error("News fetch failed:", err);
      }
      setLoading(false);
    };
    fetchNews();
    const interval = setInterval(fetchNews, 300000); // 5 min
    return () => clearInterval(interval);
  }, []);

  const filtered = filter === "ALL" ? articles : articles.filter(a => a.impact === filter);

  if (loading) return (
    <div className="flex-1 flex items-center justify-center institutional-bg">
      <div className="text-center space-y-4">
        <Loader2 size={24} className="text-indigo-500 animate-spin mx-auto" />
        <p className="text-[10px] font-mono text-slate-500 tracking-[0.3em] uppercase animate-pulse">Scanning Global Flux...</p>
      </div>
    </div>
  );

  return (
    <div className="flex-1 p-8 overflow-y-auto no-scrollbar animate-fade-in institutional-bg">
      <div className="max-w-6xl mx-auto space-y-10">
        
        {/* Institutional Header */}
        <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-6 border-b border-white/[0.08] pb-8">
          <div className="flex items-center gap-5">
            <div className="w-12 h-12 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center shadow-lg">
              <Newspaper size={24} className="text-indigo-400" />
            </div>
            <div className="flex flex-col gap-1">
              <h1 className="text-[24px] font-bold text-white tracking-tight uppercase leading-none">Evidence Corpus</h1>
              <p className="text-[10px] font-mono text-slate-500 tracking-[0.4em] uppercase">
                INTELLIGENCE_NEXUS // {stats.total || 0} NODES_CACHED // V4_ARCHIVE
              </p>
            </div>
          </div>

          {/* Skeuomorphic Filter Toggle */}
          <div className="skeuo-toggle inline-flex h-10 min-w-fit">
            {["ALL", "HIGH", "MEDIUM", "LOW"].map(f => {
              const isActive = filter === f;
              return (
                <button key={f} onClick={() => setFilter(f)}
                  className={`skeuo-toggle-item !px-6 flex items-center h-full text-[9px] font-bold uppercase tracking-widest transition-all ${isActive ? 'active' : 'text-slate-600 hover:text-slate-400'}`}>
                  {f}
                </button>
              );
            })}
          </div>
        </div>

        {/* High-Precision Articles Matrix */}
        <div className="grid gap-3">
          {filtered.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-24 gap-4 opacity-40">
              <Newspaper size={32} className="text-slate-800 animate-pulse" />
              <div className="flex flex-col items-center gap-1">
                <span className="text-[10px] font-mono font-bold text-slate-700 uppercase tracking-widest">No matching corpus nodes</span>
                <span className="text-[8px] font-mono text-slate-800 uppercase">RSS_SYNC_ACTIVE [5M_INTERVAL]</span>
              </div>
            </div>
          ) : (
            filtered.map((article, i) => {
              const impact = IMPACT_CONFIG[article.impact] || IMPACT_CONFIG.LOW;
              const ImpactIcon = impact.icon;
              return (
                <a key={i} href={article.url || "#"} target="_blank" rel="noopener noreferrer"
                  className="glass-card group p-5 border border-white/[0.06] hover:border-white/[0.15] hover:bg-white/[0.02] transition-all duration-120 block relative overflow-hidden"
                  style={{ borderLeft: `2px solid ${impact.color}` }}>
                  
                  <div className="flex items-start justify-between gap-6">
                    <div className="flex-1 space-y-3">
                      {/* Meta Tracking Line */}
                      <div className="flex items-center gap-4">
                        <div className="flex items-center gap-2 px-2 py-0.5 rounded-md text-[8px] font-bold tracking-widest border uppercase"
                          style={{ background: `${impact.color}08`, color: impact.color, borderColor: `${impact.color}20` }}>
                          <ImpactIcon size={10} /> {article.impact}_IMPACT
                        </div>
                        <div className="flex items-center gap-1.5">
                           <span className="text-[10px] font-bold text-indigo-400/80 uppercase tracking-widest">{article.source}</span>
                        </div>
                        <div className="w-[1px] h-3 bg-white/[0.08]" />
                        {article.published_at && (
                          <span className="text-[9px] font-mono font-bold text-slate-700 uppercase">{article.published_at}</span>
                        )}
                      </div>

                      {/* Content Stack */}
                      <div className="space-y-1.5">
                        <h3 className="text-[15px] font-bold text-white leading-snug group-hover:text-indigo-400 transition-colors uppercase tracking-tight">
                          {article.headline}
                        </h3>
                        {article.summary && (
                          <p className="text-[11px] text-slate-500 leading-relaxed font-medium line-clamp-1 italic max-w-4xl border-l border-white/[0.04] pl-4">
                            "{article.summary}"
                          </p>
                        )}
                      </div>
                    </div>

                    {/* External Link Interface */}
                    {article.url && (
                      <div className="w-10 h-10 shrink-0 flex items-center justify-center rounded-xl bg-white/[0.02] border border-white/[0.08] text-slate-600 group-hover:text-indigo-400 group-hover:border-indigo-500/30 transition-all duration-120 group-hover:scale-105">
                         <ExternalLink size={14} />
                      </div>
                    )}
                  </div>
                </a>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
