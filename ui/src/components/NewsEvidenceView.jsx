import React, { useState, useEffect } from "react";
import { Newspaper, ExternalLink, Loader2, Filter, AlertTriangle, Info, Zap } from "lucide-react";

import { API_BASE } from "../api_config";

const IMPACT_CONFIG = {
  HIGH:   { color: "#ef4444", bg: "rgba(239,68,68,0.12)", border: "rgba(239,68,68,0.25)", icon: AlertTriangle },
  MEDIUM: { color: "#fbbf24", bg: "rgba(251,191,36,0.12)", border: "rgba(251,191,36,0.25)", icon: Zap },
  LOW:    { color: "#94a3b8", bg: "rgba(148,163,184,0.08)", border: "rgba(148,163,184,0.15)", icon: Info },
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
    <div className="flex-1 flex items-center justify-center">
      <div className="text-center space-y-3">
        <Loader2 size={32} className="text-purple-400 animate-spin mx-auto" />
        <p className="text-xs font-mono text-slate-500 tracking-widest">SCANNING NEWS SOURCES...</p>
      </div>
    </div>
  );

  return (
    <div className="flex-1 p-4 overflow-y-auto no-scrollbar animate-fade-in">
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Header */}
          <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-4 border-b border-white/5 pb-4">
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <div className="p-2.5 bg-indigo-500/10 rounded-xl border border-indigo-500/30 shadow-lg soft-glow">
                <Newspaper size={20} className="text-indigo-400" />
              </div>
              <div>
                <h1 className="text-2xl font-black text-white tracking-tighter uppercase font-mono">Archive // Evidence</h1>
                <p className="text-[9px] font-mono text-slate-500 tracking-[0.4em] uppercase mt-0.5">
                  Nexus Intelligence • {stats.total || 0} CACHED ARTICLES
                </p>
              </div>
            </div>
          </div>


          {/* 🧠 Skeuomorphic Filter Toggle */}
          <div className="skeuo-toggle p-1 h-9">
            {["ALL", "HIGH", "MEDIUM", "LOW"].map(f => {
              const isActive = filter === f;
              return (
                <button key={f} onClick={() => setFilter(f)}
                  className={`skeuo-toggle-item !px-3.5 flex items-center h-full text-[9px] tracking-widest ${isActive ? 'active' : 'text-slate-500 opacity-60 hover:opacity-100'}`}>
                  {f}
                </button>
              );
            })}
          </div>
        </div>


        {/* Articles Grid */}
        <div className="grid gap-2.5">
          {filtered.length === 0 ? (
            <div className="text-center py-20 text-slate-600">
              <Newspaper size={48} className="mx-auto mb-4 opacity-30" />
              <p className="text-sm font-mono tracking-wider">NO ARTICLES MATCHING FILTER</p>
              <p className="text-[10px] mt-1 text-slate-700">RSS feeds refresh every 5 minutes</p>
            </div>
          ) : (
            filtered.map((article, i) => {
              const impact = IMPACT_CONFIG[article.impact] || IMPACT_CONFIG.LOW;
              const ImpactIcon = impact.icon;
              return (
                <a key={i} href={article.url || "#"} target="_blank" rel="noopener noreferrer"
                  className="clay-card p-3 group hover:scale-[1.002] transition-all block"
                  style={{ borderLeft: `2.5px solid ${impact.color}40` }}>
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1 space-y-1.5">
                      {/* Impact + Source + Time */}
                      <div className="flex items-center gap-2.5">
                        <span className="flex items-center gap-1 px-1.5 py-0.5 rounded-md text-[7px] font-black tracking-widest"
                          style={{ background: impact.bg, color: impact.color, border: `1px solid ${impact.border}` }}>
                          <ImpactIcon size={8} /> {article.impact}
                        </span>
                        <span className="text-[10px] text-indigo-400/80 font-black tracking-widest uppercase">{article.source}</span>
                        {article.published_at && (
                          <span className="text-[9px] text-slate-600 font-mono italic">{article.published_at}</span>
                        )}
                      </div>
                      {/* Headline */}
                      <h3 className="text-[14px] font-black text-white leading-tight group-hover:text-indigo-400 transition-all font-sans tracking-tight">
                        {article.headline}
                      </h3>
                      {/* Summary */}
                      {article.summary && (
                        <p className="text-[11px] text-slate-400 leading-relaxed font-medium line-clamp-1 max-w-4xl border-l border-white/5 pl-3 ml-1">{article.summary}</p>
                      )}
                    </div>
                    {article.url && (
                      <div className="skeuo-button w-7 h-7 !p-0 !rounded-lg opacity-60 group-hover:opacity-100 group-hover:scale-105">
                        <ExternalLink size={12} className="text-indigo-400" />
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
