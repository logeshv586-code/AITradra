import React, { useState, useEffect } from "react";
import { Newspaper, ExternalLink, Loader2, Filter, AlertTriangle, Info, Zap } from "lucide-react";

const API_BASE = "http://localhost:8000";

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
    <div className="flex-1 p-8 overflow-y-auto no-scrollbar animate-fade-in">
      <div className="max-w-5xl mx-auto space-y-8">
        {/* Header */}
        <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-6 border-b border-white/5 pb-6">
          <div className="space-y-2">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-purple-500/10 rounded-2xl border border-purple-500/30 shadow-lg">
                <Newspaper size={24} className="text-purple-400" />
              </div>
              <div>
                <h2 className="text-3xl font-black text-white tracking-tighter uppercase">News & Evidence</h2>
                <p className="text-[10px] font-mono text-slate-500 tracking-[0.3em] uppercase mt-1">
                  {stats.total || 0} CACHED ARTICLES • {stats.high || 0} HIGH IMPACT
                </p>
              </div>
            </div>
          </div>

          {/* Impact Stats */}
          <div className="flex gap-3">
            {["ALL", "HIGH", "MEDIUM", "LOW"].map(f => {
              const isActive = filter === f;
              const cfg = IMPACT_CONFIG[f];
              const color = cfg ? cfg.color : "#6366f1";
              return (
                <button key={f} onClick={() => setFilter(f)}
                  className="px-4 py-2 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all"
                  style={{
                    background: isActive ? `${color}20` : "transparent",
                    border: `1px solid ${isActive ? `${color}40` : "rgba(255,255,255,0.05)"}`,
                    color: isActive ? color : "#64748b",
                  }}>
                  {f}
                </button>
              );
            })}
          </div>
        </div>

        {/* Articles Grid */}
        <div className="grid gap-4">
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
                  className="clay-card p-5 group hover:scale-[1.005] transition-all block"
                  style={{ borderLeft: `3px solid ${impact.color}30` }}>
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 space-y-2">
                      {/* Impact + Source + Time */}
                      <div className="flex items-center gap-3">
                        <span className="flex items-center gap-1.5 px-2 py-0.5 rounded-md text-[8px] font-black tracking-widest"
                          style={{ background: impact.bg, color: impact.color, border: `1px solid ${impact.border}` }}>
                          <ImpactIcon size={9} /> {article.impact}
                        </span>
                        <span className="text-[10px] text-indigo-400 font-bold">{article.source}</span>
                        {article.published_at && (
                          <span className="text-[9px] text-slate-600 font-mono">{article.published_at}</span>
                        )}
                      </div>
                      {/* Headline */}
                      <h3 className="text-sm font-bold text-white leading-snug group-hover:text-indigo-300 transition-colors">
                        {article.headline}
                      </h3>
                      {/* Summary */}
                      {article.summary && (
                        <p className="text-[11px] text-slate-400 leading-relaxed line-clamp-2">{article.summary}</p>
                      )}
                    </div>
                    {article.url && (
                      <ExternalLink size={14} className="text-slate-600 group-hover:text-indigo-400 transition-colors shrink-0 mt-1" />
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
