import React, { useState, useEffect, useRef } from "react";
import './DeepResearchSuggestions.css';
import { 
  Target, 
  TrendingUp, 
  TrendingDown, 
  Zap, 
  LayoutGrid,
  Shield,
  Search,
  Loader2,
  Sparkles,
  ArrowUpRight,
  ArrowDownRight,
  Minus,
  Send,
  Brain,
  BarChart3,
  Activity,
  Eye,
  ChevronDown,
  ChevronUp,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Gauge,
  RefreshCw
} from "lucide-react";
import { API_BASE } from "../api_config";

// ═══════════════════════════════════════════════════════════════════════════════
//  CONSENSUS NODE CARD — Rich interactive research card
// ═══════════════════════════════════════════════════════════════════════════════

const ConvictionBadge = ({ signal }) => {
  const config = {
    'STRONG BUY':  { bg: 'dr-badge-strong-buy',  icon: ArrowUpRight },
    'STRONG_BUY':  { bg: 'dr-badge-strong-buy',  icon: ArrowUpRight },
    'BUY':         { bg: 'dr-badge-buy',          icon: TrendingUp },
    'HOLD':        { bg: 'dr-badge-hold',         icon: Minus },
    'SELL':        { bg: 'dr-badge-sell',          icon: TrendingDown },
    'STRONG SELL': { bg: 'dr-badge-strong-sell',   icon: ArrowDownRight },
    'STRONG_SELL': { bg: 'dr-badge-strong-sell',   icon: ArrowDownRight },
  };
  const c = config[signal?.toUpperCase()] || config['HOLD'];
  const Icon = c.icon;
  return (
    <div className={`dr-conviction-badge ${c.bg}`}>
      <Icon size={10} />
      <span>{signal || 'HOLD'}</span>
    </div>
  );
};

const GaugeBar = ({ label, value, max = 100, color = 'indigo' }) => {
  const pct = Math.min(100, Math.max(0, (value / max) * 100));
  return (
    <div className="dr-gauge">
      <div className="dr-gauge-header">
        <span className="dr-gauge-label">{label}</span>
        <span className={`dr-gauge-value dr-color-${color}`}>{typeof value === 'number' ? value.toFixed(1) : value}</span>
      </div>
      <div className="dr-gauge-track">
        <div className={`dr-gauge-fill dr-fill-${color}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
};

const ConsensusNodeCard = ({ suggestion, onActivate, index }) => {
  const [expanded, setExpanded] = useState(false);
  const breakdown = suggestion.breakdown || {};
  const score = suggestion.score || 0;
  const scorePct = Math.round(score * 100);

  // Derive conviction color
  const getConvictionClass = () => {
    if (scorePct >= 85) return 'dr-node-emerald';
    if (scorePct >= 70) return 'dr-node-blue';
    if (scorePct >= 50) return 'dr-node-amber';
    return 'dr-node-red';
  };

  return (
    <div className={`dr-node-card ${getConvictionClass()}`} style={{ animationDelay: `${index * 80}ms` }}>
      {/* Header */}
      <div className="dr-node-header">
        <div className="dr-node-identity">
          <div className="dr-node-avatar">
            {suggestion.ticker?.[0] || '?'}
          </div>
          <div className="dr-node-meta">
            <span className="dr-node-ticker">{suggestion.ticker}</span>
            <span className="dr-node-score-label">CONSENSUS: {scorePct}%</span>
          </div>
        </div>
        <ConvictionBadge signal={suggestion.signal} />
      </div>

      {/* Score Ring */}
      <div className="dr-score-ring-wrap">
        <svg className="dr-score-ring" viewBox="0 0 36 36">
          <path className="dr-ring-bg" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
          <path className="dr-ring-fill" strokeDasharray={`${scorePct}, 100`} d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
        </svg>
        <span className="dr-score-text">{scorePct}%</span>
      </div>

      {/* Reasoning */}
      <p className="dr-node-reasoning">"{suggestion.reasoning}"</p>

      {/* Metric Grid */}
      <div className="dr-metrics-grid">
        <div className="dr-metric-cell">
          <span className="dr-metric-label">1M PERF</span>
          <span className={`dr-metric-value ${(suggestion.perf_1m || 0) >= 0 ? 'dr-color-emerald' : 'dr-color-red'}`}>
            {(suggestion.perf_1m || 0) >= 0 ? '+' : ''}{suggestion.perf_1m || 0}%
          </span>
        </div>
        <div className="dr-metric-cell">
          <span className="dr-metric-label">RSI</span>
          <span className="dr-metric-value dr-color-indigo">{suggestion.rsi || '—'}</span>
        </div>
        <div className="dr-metric-cell">
          <span className="dr-metric-label">P/E</span>
          <span className="dr-metric-value dr-color-slate">{suggestion.pe_ratio || '—'}</span>
        </div>
        <div className="dr-metric-cell">
          <span className="dr-metric-label">MOMENTUM</span>
          <span className={`dr-metric-value ${(suggestion.momentum_score || 0) >= 0.6 ? 'dr-color-emerald' : 'dr-color-amber'}`}>
            {suggestion.momentum_score ? (suggestion.momentum_score * 100).toFixed(0) + '%' : '—'}
          </span>
        </div>
      </div>

      {/* Agent Breakdown (expandable) */}
      <button className="dr-expand-btn" onClick={() => setExpanded(!expanded)}>
        <Eye size={11} />
        {expanded ? 'HIDE AGENT LOGS' : 'VIEW AGENT CONSENSUS'}
        {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
      </button>

      {expanded && (
        <div className="dr-breakdown animate-fade-in">
          {Object.keys(breakdown).length > 0 ? (
            Object.entries(breakdown).slice(0, 5).map(([key, val]) => (
              <div key={key} className="dr-breakdown-row">
                <div className="dr-breakdown-header">
                  <span className="dr-breakdown-agent">{key}</span>
                  <span className={`dr-breakdown-signal ${val.signal === 'BULLISH' ? 'dr-color-emerald' : val.signal === 'BEARISH' ? 'dr-color-red' : 'dr-color-slate'}`}>
                    {val.signal}
                  </span>
                </div>
                <p className="dr-breakdown-reason">{val.reason}</p>
              </div>
            ))
          ) : (
            <div className="dr-breakdown-empty">
              <Brain size={14} />
              <span>Agent consensus data pending synthesis...</span>
            </div>
          )}
        </div>
      )}

      {/* Action */}
      <button className="dr-activate-btn" onClick={() => onActivate(suggestion.ticker)}>
        <Zap size={13} fill="white" />
        ACTIVATE MISSION
      </button>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
//  NEURAL QUERY INPUT
// ═══════════════════════════════════════════════════════════════════════════════

const NeuralQueryInput = ({ onSubmit, isLoading }) => {
  const [query, setQuery] = useState('');
  const inputRef = useRef(null);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (query.trim() && !isLoading) {
      onSubmit(query.trim());
      setQuery('');
    }
  };

  return (
    <form className="dr-neural-input-wrap" onSubmit={handleSubmit}>
      <div className="dr-neural-icon">
        <Sparkles size={16} />
      </div>
      <input
        ref={inputRef}
        type="text"
        className="dr-neural-input"
        placeholder="Query the Consensus Fleet — e.g. 'Analyze RELIANCE buy thesis'..."
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        disabled={isLoading}
      />
      <button
        type="submit"
        className={`dr-neural-submit ${isLoading ? 'loading' : ''}`}
        disabled={isLoading || !query.trim()}
      >
        {isLoading ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
      </button>
    </form>
  );
};


// ═══════════════════════════════════════════════════════════════════════════════
//  MAIN EXPORT
// ═══════════════════════════════════════════════════════════════════════════════

export default function DeepResearchSuggestions() {
  const [suggestions, setSuggestions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activating, setActivating] = useState(false);
  const [queryLoading, setQueryLoading] = useState(false);
  const [queryResponse, setQueryResponse] = useState(null);

  const fetchSuggestions = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/mission/suggestions`);
      const data = await res.json();
      setSuggestions(data.suggestions || []);
      setLoading(false);
    } catch (err) {
      console.error("Suggestions fetch failed:", err);
      setLoading(false);
    }
  };

  const handleActivate = async (ticker) => {
    setActivating(true);
    try {
      await fetch(`${API_BASE}/api/mission/activate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ticker, amount: 2000, reasoning: "User approved Mission suggestion." })
      });
    } catch (err) {
      console.error("Activation failed:", err);
    } finally {
      setActivating(false);
    }
  };

  const handleNeuralQuery = async (query) => {
    setQueryLoading(true);
    setQueryResponse(null);
    try {
      const res = await fetch(`${API_BASE}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: query, ticker: '' }),
      });
      const data = await res.json();
      setQueryResponse({
        text: data.response,
        consensus: data.consensus,
        confidence: data.confidence,
        timestamp: new Date().toLocaleTimeString(),
      });
    } catch (err) {
      setQueryResponse({ text: 'Neural link interrupted. Check backend connectivity.', error: true, timestamp: new Date().toLocaleTimeString() });
    } finally {
      setQueryLoading(false);
    }
  };

  useEffect(() => {
    fetchSuggestions();
  }, []);

  if (loading && suggestions.length === 0) return (
    <div className="dr-loading">
      <Loader2 size={24} className="animate-spin" style={{ color: '#6366f1' }} />
      <span>Syncing Consensus Stream...</span>
    </div>
  );

  return (
    <div className="dr-root animate-fade-in">

      {/* Neural Query Section */}
      <div className="dr-section">
        <div className="dr-section-header">
          <div className="dr-section-title-group">
            <Brain size={16} style={{ color: '#818cf8' }} />
            <h2 className="dr-section-title">Neural Intelligence Query</h2>
          </div>
          <div className="dr-section-badge">
            <Activity size={10} />
            <span>14 AGENTS ONLINE</span>
          </div>
        </div>
        <NeuralQueryInput onSubmit={handleNeuralQuery} isLoading={queryLoading} />
        
        {/* Query Response */}
        {queryResponse && (
          <div className={`dr-query-response ${queryResponse.error ? 'error' : ''}`}>
            <div className="dr-response-header">
              <div className="dr-response-tag">
                <Sparkles size={10} />
                AXIOM MYTHIC
              </div>
              <span className="dr-response-time">{queryResponse.timestamp}</span>
            </div>
            <p className="dr-response-text">{queryResponse.text}</p>
            {queryResponse.confidence && (
              <div className="dr-response-confidence">
                <Gauge size={11} />
                <span>Confidence: {(queryResponse.confidence * 100).toFixed(0)}%</span>
                {queryResponse.consensus && <span>• Consensus: {queryResponse.consensus}</span>}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Consensus Clusters */}
      <div className="dr-section">
        <div className="dr-section-header">
          <div className="dr-section-title-group">
            <Target size={16} style={{ color: '#818cf8' }} />
            <h2 className="dr-section-title">High-Conviction Consensus Nodes</h2>
          </div>
          <div className="dr-header-actions">
            <button className="dr-refresh-btn" onClick={fetchSuggestions} title="Refresh">
              <RefreshCw size={12} />
            </button>
            <div className="dr-section-badge synthesized">
              <Shield size={10} />
              <span>SYNTHESIZED</span>
            </div>
          </div>
        </div>

        <div className="dr-nodes-grid">
          {suggestions.map((s, i) => (
            <ConsensusNodeCard key={s.ticker + i} suggestion={s} onActivate={handleActivate} index={i} />
          ))}
          {suggestions.length === 0 && (
            <div className="dr-empty">
              <LayoutGrid size={28} style={{ color: 'rgba(148,163,184,0.15)' }} />
              <div className="dr-empty-text">
                <span className="dr-empty-title">No Consensus Nodes Available</span>
                <span className="dr-empty-sub">Cluster consensus threshold &lt; 85%. Try querying the fleet above.</span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
