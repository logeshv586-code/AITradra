import React, { useEffect, useMemo, useState } from "react";
import { Activity, ArrowDown, ArrowUp, Loader2, Newspaper, RefreshCw, ShieldCheck } from "lucide-react";
import { API_BASE } from "../api_config";

export default function NewsEvidenceView({ onSelect }) {
  const [articles, setArticles] = useState([]);
  const [brief, setBrief] = useState(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("ALL");
  const [error, setError] = useState("");

  const load = async () => {
    setError("");
    try {
      const [newsResponse, briefResponse] = await Promise.all([
        fetch(`${API_BASE}/api/market/news-evidence`),
        fetch(`${API_BASE}/api/customer/daily-brief?limit=10`),
      ]);
      if (newsResponse.ok) setArticles((await newsResponse.json()).articles || []);
      if (briefResponse.ok) setBrief(await briefResponse.json());
      if (!newsResponse.ok && !briefResponse.ok) throw new Error("Market news is temporarily unavailable");
    } catch (e) {
      setError(e.message || "Market news is temporarily unavailable");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    const timer = setInterval(load, 120000);
    return () => clearInterval(timer);
  }, []);

  const openTicker = (ticker) => {
    if (!ticker) return;
    if (onSelect) {
      onSelect(ticker);
      return;
    }
    window.dispatchEvent(new CustomEvent("aitradra:select-ticker", { detail: { ticker } }));
  };

  const filtered = useMemo(
    () => articles.filter((article) => filter === "ALL" || String(article.impact || "LOW").toUpperCase() === filter),
    [articles, filter]
  );

  if (loading) return <div className="h-full flex items-center justify-center gap-3"><Loader2 size={22} className="animate-spin text-[var(--accent)]" /><span className="text-[12px] text-[var(--text-muted)]">Collecting today’s market headlines…</span></div>;

  return (
    <div className="flex-1 overflow-y-auto w-full p-4 md:p-6 lg:p-8 max-w-[1440px] mx-auto animate-fade-in flex flex-col gap-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3"><Newspaper size={22} className="text-[var(--accent)]" /><h1 className="heading-1">What is moving markets</h1></div>
          <p className="text-[13px] text-[var(--text-muted)] mt-2 max-w-2xl">Current headlines and the assets moving around them. Open a stock to see the full “what happened and why” analysis from all agents.</p>
        </div>
        <button onClick={load} className="btn-standard h-9 px-4"><RefreshCw size={13} /> Refresh</button>
      </div>

      {error && <div className="surface-card p-4 text-[12px] text-[var(--negative)]">{error}</div>}

      <section className="surface-card p-5">
        <div className="flex items-start gap-3"><Activity size={17} className="text-[var(--accent)] mt-0.5" /><div><h2 className="heading-3">Market snapshot</h2><p className="text-[12px] text-[var(--text-muted)] mt-2">{brief?.summary || "AITradra is updating the tracked market universe."}</p></div></div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3 mt-5">
          {(brief?.top_movers || []).slice(0, 5).map((row) => {
            const chg = Number(row.chg || 0);
            return (
              <button key={row.ticker} onClick={() => openTicker(row.ticker)} className="text-left rounded-[var(--radius-md)] border border-[var(--border-color)] bg-[#171b22] p-4 hover:border-[var(--accent)] transition-colors">
                <div className="flex items-center justify-between gap-2"><span className="font-semibold text-white text-[12px]">{row.ticker}</span><span className="surface-badge">{row.recommendation || "HOLD"}</span></div>
                <div className="flex items-center gap-1 mt-2 font-mono text-[12px]" style={{ color: chg >= 0 ? "var(--positive)" : "var(--negative)" }}>{chg >= 0 ? <ArrowUp size={12} /> : <ArrowDown size={12} />}{chg >= 0 ? "+" : ""}{chg.toFixed(2)}%</div>
                <div className="text-[9px] text-[var(--text-muted)] mt-2 capitalize">Main signal: {String(row.primary_driver || "technical").replace(/_/g, " ")}</div>
              </button>
            );
          })}
        </div>
      </section>

      <section className="surface-card overflow-hidden">
        <div className="p-5 border-b border-[var(--border-color)] flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div><h2 className="heading-3">Latest verified headlines</h2><p className="text-[10px] text-[var(--text-muted)] mt-1">High-impact items appear first. Open the original source whenever a link is available.</p></div>
          <div className="flex gap-2">{["ALL", "HIGH", "MEDIUM", "LOW"].map((value) => <button key={value} onClick={() => setFilter(value)} className={`px-3 py-1.5 rounded-[var(--radius-sm)] text-[10px] border ${filter === value ? "bg-[var(--accent)] text-white border-[var(--accent)]" : "border-[var(--border-color)] text-[var(--text-muted)]"}`}>{value === "ALL" ? "All" : `${value.toLowerCase()} impact`}</button>)}</div>
        </div>
        <div className="divide-y divide-[var(--border-color)]">
          {filtered.length ? filtered.map((article, index) => (
            <article key={`${article.headline}-${index}`} className="p-5 grid grid-cols-1 md:grid-cols-[1fr_auto] gap-4">
              <div>
                <div className="flex flex-wrap items-center gap-2"><span className={`surface-badge ${article.impact === "HIGH" ? "text-[var(--negative)]" : article.impact === "MEDIUM" ? "text-amber-300" : "text-[var(--text-muted)]"}`}>{String(article.impact || "LOW").toLowerCase()} impact</span><span className="text-[9px] text-[var(--text-muted)]">{article.source || "Market source"}</span></div>
                <h3 className="text-[13px] font-semibold text-white mt-2 leading-relaxed">{article.headline}</h3>
                {article.summary && <p className="text-[11px] text-[var(--text-muted)] leading-relaxed mt-2">{article.summary}</p>}
                {article.published_at && <p className="text-[9px] text-[var(--text-muted)] mt-2">Published: {String(article.published_at)}</p>}
              </div>
              {article.url && <a href={article.url} target="_blank" rel="noreferrer" className="btn-standard h-9 px-4 self-start">Open source</a>}
            </article>
          )) : <div className="p-10 text-center text-[12px] text-[var(--text-muted)]">No headlines match this filter yet.</div>}
        </div>
      </section>

      <div className="surface-card p-4 flex items-start gap-3"><ShieldCheck size={15} className="text-[var(--positive)] shrink-0 mt-0.5" /><p className="text-[11px] text-[var(--text-muted)] leading-relaxed">A headline can explain part of a move without being the only cause. AITradra combines news with price trend, volume, risk and other agent evidence before showing a prediction.</p></div>
    </div>
  );
}
