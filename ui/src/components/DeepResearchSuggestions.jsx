import React, { useEffect, useState } from 'react';
import {
  ArrowRight,
  Lightbulb,
  Loader2,
  Radar,
  RefreshCw,
} from 'lucide-react';
import { API_BASE } from '../api_config';

function timeAgo(value) {
  if (!value) {
    return 'now';
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return 'recent';
  }

  const deltaMs = Date.now() - parsed.getTime();
  const deltaMinutes = Math.max(Math.floor(deltaMs / 60000), 0);

  if (deltaMinutes < 1) {
    return 'now';
  }
  if (deltaMinutes < 60) {
    return `${deltaMinutes}m ago`;
  }
  if (deltaMinutes < 1440) {
    return `${Math.floor(deltaMinutes / 60)}h ago`;
  }
  return `${Math.floor(deltaMinutes / 1440)}d ago`;
}

function typeTone(type) {
  switch (String(type || '').toUpperCase()) {
    case 'MACRO':
      return 'text-cyan-300 border-cyan-500/20 bg-cyan-500/10';
    case 'CATALYST':
      return 'text-amber-300 border-amber-500/20 bg-amber-500/10';
    case 'FLOW':
      return 'text-emerald-300 border-emerald-500/20 bg-emerald-500/10';
    case 'QUANTIC':
      return 'text-indigo-300 border-indigo-500/20 bg-indigo-500/10';
    default:
      return 'text-slate-300 border-white/[0.1] bg-white/[0.04]';
  }
}

function signalTone(signal) {
  switch (String(signal || '').toUpperCase()) {
    case 'BUY':
      return 'text-emerald-300';
    case 'SELL':
    case 'AVOID':
      return 'text-red-300';
    default:
      return 'text-amber-200';
  }
}

export default function DeepResearchSuggestions() {
  const [suggestions, setSuggestions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    const abortController = new AbortController();

    const loadSuggestions = async (isRefresh = false) => {
      try {
        if (isRefresh) {
          setRefreshing(true);
        } else {
          setLoading(true);
        }

        setError('');
        const response = await fetch(`${API_BASE}/api/intel/suggestions?limit=6`, {
          signal: abortController.signal,
        });
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        const payload = await response.json();
        setSuggestions(Array.isArray(payload?.suggestions) ? payload.suggestions : []);
      } catch (fetchError) {
        if (fetchError?.name !== 'AbortError') {
          setError('Research feed temporarily unavailable.');
        }
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    };

    loadSuggestions();

    const refreshId = setInterval(() => loadSuggestions(true), 45000);
    return () => {
      clearInterval(refreshId);
      abortController.abort();
    };
  }, []);

  return (
    <div className="flex flex-col h-full bg-[var(--card-bg)]">
      <div className="px-5 py-4 border-b border-[var(--border-color)] bg-[#1b1f27] flex items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-xl border border-indigo-500/20 bg-indigo-500/10 flex items-center justify-center">
            <Radar size={16} className="text-indigo-300" />
          </div>
          <div>
            <h3 className="text-[12px] font-semibold text-white">Live Research Vectors</h3>
            <p className="text-[10px] text-[var(--text-muted)]">
              Dynamic suggestions synthesized from backend intelligence and stored research signals.
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={async () => {
            try {
              setRefreshing(true);
              setError('');
              const response = await fetch(`${API_BASE}/api/intel/suggestions?limit=6`);
              if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
              }
              const payload = await response.json();
              setSuggestions(Array.isArray(payload?.suggestions) ? payload.suggestions : []);
            } catch {
              setError('Research feed temporarily unavailable.');
            } finally {
              setRefreshing(false);
            }
          }}
          className="h-9 w-9 rounded-xl border border-white/[0.08] bg-white/[0.03] hover:bg-white/[0.06] text-slate-400 hover:text-white transition-colors flex items-center justify-center"
          aria-label="Refresh research vectors"
        >
          <RefreshCw size={14} className={refreshing ? 'animate-spin' : ''} />
        </button>
      </div>

      <div className="p-5 flex flex-col gap-4">
        {loading ? (
          <div className="flex flex-col items-center justify-center gap-3 py-12 text-center">
            <Loader2 size={18} className="text-indigo-300 animate-spin" />
            <p className="text-[11px] text-[var(--text-muted)] uppercase tracking-[0.2em]">
              Synchronizing swarm vectors
            </p>
          </div>
        ) : error ? (
          <div className="rounded-[var(--radius-md)] border border-red-500/15 bg-red-500/[0.04] px-4 py-5">
            <p className="text-[12px] text-red-200">{error}</p>
          </div>
        ) : suggestions.length === 0 ? (
          <div className="rounded-[var(--radius-md)] border border-dashed border-[var(--border-color)] px-4 py-6 text-center">
            <p className="text-[12px] text-[var(--text-muted)]">
              No research vectors are queued yet. The intelligence layer is waiting for the next scan cycle.
            </p>
          </div>
        ) : (
          suggestions.map((suggestion, index) => (
            <div
              key={suggestion.id || `${suggestion.ticker}-${index}`}
              className="flex gap-4 p-4 bg-[#1e232b] rounded-[var(--radius-md)] border border-[var(--border-color)] hover:border-slate-500 transition-colors group"
            >
              <div className="shrink-0 mt-1">
                <Lightbulb size={20} className="text-[var(--accent)]" />
              </div>

              <div className="flex-1 flex flex-col gap-3 min-w-0">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                      <h4 className="text-[14px] font-semibold text-white group-hover:text-[var(--accent)] transition-colors">
                        {suggestion.title}
                      </h4>
                      <span
                        className={`text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded border ${typeTone(suggestion.type)}`}
                      >
                        {suggestion.type || 'RESEARCH'}
                      </span>
                    </div>
                    <p className="text-[12px] text-[var(--text-muted)] leading-relaxed">
                      {suggestion.desc}
                    </p>
                  </div>

                  <div className="shrink-0 text-right">
                    <div className="text-[16px] font-mono font-bold text-white">
                      {Number.isFinite(Number(suggestion.score))
                        ? `${Math.round(Number(suggestion.score))}`
                        : '--'}
                    </div>
                    <div className="text-[9px] text-slate-500 uppercase tracking-widest">
                      Score
                    </div>
                  </div>
                </div>

                <div className="flex items-center justify-between gap-3 flex-wrap">
                  <div className="flex items-center gap-2 flex-wrap">
                    {suggestion.ticker && (
                      <span className="text-[10px] font-bold text-white uppercase tracking-wider">
                        {suggestion.ticker}
                      </span>
                    )}
                    {suggestion.signal && (
                      <span className={`text-[10px] font-bold uppercase tracking-wider ${signalTone(suggestion.signal)}`}>
                        {suggestion.signal}
                      </span>
                    )}
                    {suggestion.updated_at && (
                      <span className="text-[10px] text-slate-500 uppercase tracking-wider">
                        {timeAgo(suggestion.updated_at)}
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-2 text-[11px] font-medium text-[var(--text-muted)] group-hover:text-white transition-colors">
                    Execute Query <ArrowRight size={12} />
                  </div>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
