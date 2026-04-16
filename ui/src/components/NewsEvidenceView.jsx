import React, { useState, useEffect } from "react";
import { Newspaper, Loader2, Shield, Calendar, ArrowUpRight, TrendingUp, TrendingDown, Target, Zap, Activity } from "lucide-react";
import { API_BASE } from "../api_config";

function getSentimentStyle(sentiment) {
  const s = (sentiment || "").toLowerCase();
  if (s === "positive" || s === "bullish" || s === "high") return "text-[var(--positive)]";
  if (s === "negative" || s === "bearish" || s === "low")  return "text-[var(--negative)]";
  return "text-[var(--warning)]";
}

export default function NewsEvidenceView() {
  const [data, setData] = useState({ summary: "", articles: [], key_themes: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/intel/overview`);
        if (!res.ok) {
           const fb = await fetch(`${API_BASE}/api/market/news-evidence`);
           if (!fb.ok) throw new Error("Could not fetch intelligence data");
           const d = await fb.json();
           if (!cancelled) setData(d);
           return;
        }
        const json = await res.json();
        if (!cancelled) setData(json.market_intel || json);
      } catch (err) {
        if (!cancelled) setError(err.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    load();
    const id = setInterval(load, 300_000); // 5 min
    return () => { cancelled = true; clearInterval(id); };
  }, []);

  if (loading) return (
     <div className="h-full flex flex-col items-center justify-center gap-4 bg-[var(--app-bg)] w-full">
        <Loader2 size={24} className="text-[var(--accent)] animate-spin" />
        <span className="text-[12px] font-medium text-[var(--text-muted)]">Acquiring Intel Data...</span>
     </div>
  );

  if (error) return (
     <div className="h-full flex flex-col items-center justify-center gap-2 bg-[var(--app-bg)] w-full text-[var(--negative)]">
        <Shield size={28} className="mb-2" />
        <p className="font-semibold text-[13px]">Intel Feed Offline</p>
        <p className="text-[11px] font-mono opacity-80">{error}</p>
     </div>
  );

  return (
    <div className="flex-1 overflow-y-auto w-full p-4 md:p-6 lg:p-8 max-w-[1440px] mx-auto animate-fade-in flex flex-col gap-6 lg:gap-8">

      {/* Page Header */}
      <div className="flex flex-col md:flex-row gap-4 justify-between items-start md:items-center">
         <div className="flex flex-col gap-2">
            <div className="flex items-center gap-3">
               <Newspaper size={20} className="text-[var(--accent)]" />
               <h1 className="heading-1">Market Intelligence</h1>
            </div>
            <p className="text-[13px] text-[var(--text-muted)]">Live synthesis of macro news, corporate fundamentals, and social sentiment.</p>
         </div>

         {data.articles?.length > 0 && (
            <div className="flex items-center gap-3 bg-[var(--card-bg)] px-4 py-2 rounded-[var(--radius-md)] border border-[var(--border-color)]">
               <div className="h-2 w-2 rounded-full bg-[var(--positive)] animate-pulse" />
               <span className="text-small-caps font-bold">Live Feed</span>
               <div className="h-4 w-px bg-[var(--border-color)]" />
               <span className="font-mono text-[12px] font-medium text-white">{data.articles.length} sources</span>
            </div>
         )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_360px] gap-6 lg:gap-8">
         {/* Left Column: Feed */}
         <div className="flex flex-col gap-6">
            
            {/* AI Summary */}
            {(data.summary || data.market_summary) && (
               <section className="bg-[var(--accent-bg)] border border-[var(--accent)] border-opacity-30 p-6 rounded-[var(--radius-lg)]">
                  <div className="flex items-center gap-2 mb-3">
                     <Zap size={16} className="text-[var(--accent)]" />
                     <h2 className="text-[12px] font-bold text-[var(--accent)] uppercase tracking-wider">Mythic Synthesis</h2>
                  </div>
                  <p className="text-[14px] leading-relaxed text-white">
                     {data.summary || data.market_summary}
                  </p>
               </section>
            )}

            {/* Article Feed */}
            <section className="surface-card">
               <div className="p-5 border-b border-[var(--border-color)] bg-[#1b1f27]">
                  <h2 className="heading-3">Intelligence Feed</h2>
               </div>
               <div className="flex flex-col divide-y divide-[var(--border-color)]">
                  {data.articles?.slice(0, 20).map((art, i) => (
                     <article key={i} className="p-5 hover:bg-[#1b1f27] transition-colors">
                        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
                           <div className="flex flex-col">
                              <a href={art.url || "#"} target="_blank" rel="noopener noreferrer" className="inline-block group">
                                 <h3 className="text-[15px] font-semibold text-white group-hover:text-[var(--accent)] transition-colors leading-snug">
                                    {art.title || art.headline}
                                 </h3>
                              </a>
                              {art.summary && <p className="mt-2 text-[13px] text-[var(--text-muted)] line-clamp-2 leading-relaxed">{art.summary}</p>}
                              
                              <div className="mt-3 flex items-center gap-3">
                                 {art.source && <span className="surface-badge !py-0.5">{art.source}</span>}
                                 {art.published_at && (
                                    <span className="flex items-center gap-1.5 text-[11px] text-[var(--text-muted)]">
                                       <Calendar size={12} />
                                       {new Date(art.published_at).toLocaleString()}
                                    </span>
                                 )}
                              </div>
                           </div>

                           {(art.sentiment || art.impact) && (
                              <div className="flex flex-col sm:items-end gap-2 shrink-0">
                                 {art.impact && <span className="text-[11px] font-medium text-[var(--text-muted)]">Impact: {art.impact}</span>}
                                 {art.sentiment && (
                                    <span className={`flex items-center gap-1 text-[11px] font-bold uppercase tracking-wider ${getSentimentStyle(art.sentiment)}`}>
                                       {art.sentiment.toLowerCase() === "positive" ? <TrendingUp size={12} /> : art.sentiment.toLowerCase() === "negative" ? <TrendingDown size={12} /> : null}
                                       {art.sentiment}
                                    </span>
                                 )}
                              </div>
                           )}
                        </div>
                     </article>
                  ))}
                  {(!data.articles || data.articles.length === 0) && (
                     <div className="p-12 text-center text-[13px] text-[var(--text-muted)]">
                        No articles acquired in the latest sweep.
                     </div>
                  )}
               </div>
            </section>
         </div>

         {/* Right Column: Key Themes & Analysis */}
         <div className="flex flex-col gap-6">
            
            {/* Key Themes */}
            {(data.key_themes?.length > 0 || data.themes?.length > 0) && (
               <section className="surface-card flex flex-col">
                  <div className="p-5 border-b border-[var(--border-color)] flex items-center gap-2 bg-[#1b1f27]">
                     <Target size={16} className="text-[var(--warning)]" />
                     <h2 className="heading-3">Key Themes</h2>
                  </div>
                  <div className="p-5 flex flex-wrap gap-2">
                     {(data.key_themes || data.themes).map((theme, i) => (
                        <span key={i} className="px-3 py-1.5 bg-[#1e232b] border border-[var(--border-color)] text-[12px] font-medium text-white rounded-[var(--radius-full)] whitespace-nowrap">
                           {theme}
                        </span>
                     ))}
                  </div>
               </section>
            )}

            {/* Sentiment Dist */}
            {(data.sentiment_distribution || data.overall_sentiment) && (
               <section className="surface-card flex flex-col">
                  <div className="p-5 border-b border-[var(--border-color)] flex items-center gap-2 bg-[#1b1f27]">
                     <Activity size={16} className="text-[var(--positive)]" />
                     <h2 className="heading-3">Market Sentiment</h2>
                  </div>
                  <div className="p-5 flex flex-col gap-5">
                     {data.overall_sentiment && (
                        <div className="flex flex-col items-center justify-center p-4 bg-[#1e232b] rounded-[var(--radius-md)] border border-[var(--border-color)]">
                           <span className="text-[10px] uppercase text-[var(--text-muted)] mb-1 font-bold tracking-wider">Overall Posture</span>
                           <span className={`text-lg font-bold uppercase tracking-widest ${getSentimentStyle(data.overall_sentiment)}`}>
                              {data.overall_sentiment}
                           </span>
                        </div>
                     )}
                     
                     {data.sentiment_distribution && (
                        <div className="flex flex-col gap-3">
                           {Object.entries(data.sentiment_distribution).map(([k, v]) => (
                              <div key={k} className="flex justify-between items-center text-[12px]">
                                 <span className="font-medium text-[var(--text-muted)] uppercase tracking-wider">{k}</span>
                                 <span className="font-mono text-white font-semibold">{v}</span>
                              </div>
                           ))}
                        </div>
                     )}
                  </div>
               </section>
            )}
         </div>
      </div>
    </div>
  );
}
