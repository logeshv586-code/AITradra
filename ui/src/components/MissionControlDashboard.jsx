import React, { useState, useEffect, useMemo } from 'react';
import './MissionControlDashboard.css';
import {
  TrendingUp,
  ShieldAlert,
  Activity,
  Terminal,
  Search,
  Zap,
  BarChart3,
  Cpu,
  Layers,
  RefreshCw,
  ArrowUpRight,
  ArrowDownRight,
  Wifi,
  Clock,
  Target,
  Gauge,
  CircuitBoard,
  Box,
  Signal,
  Flame,
  Eye,
  ChevronRight,
  Sparkles,
} from 'lucide-react';
import { API_BASE } from '../api_config';
import DeepResearchSuggestions from './DeepResearchSuggestions';

// ═══════════════════════════════════════════════════════════════════════════════
//  MOCK DATA (Fallback when API is offline)
// ═══════════════════════════════════════════════════════════════════════════════

const MOCK_AGENTS = [
  { id: 'orchestrator', name: 'Mythic Orchestrator', status: 'active', load: 42, health: 98, lastTask: 'ReAct Synthesis Loop' },
  { id: 'risk', name: 'Risk Specialist', status: 'active', load: 15, health: 100, lastTask: 'Portfolio VaR(95%)' },
  { id: 'macro', name: 'Macro Specialist', status: 'idle', load: 5, health: 92, lastTask: 'Sector Rotation Scan' },
  { id: 'tech', name: 'Technical Specialist', status: 'active', load: 88, health: 95, lastTask: 'Momentum Detection' },
  { id: 'critique', name: 'Critique Agent', status: 'active', load: 65, health: 89, lastTask: 'Confidence Calibration' },
  { id: 'newsIntel', name: 'News Intelligence', status: 'warning', load: 10, health: 65, lastTask: 'API Rate Limited' },
];

const MOCK_TICKERS = [
  { symbol: 'RELIANCE', price: '2,845.30', change: '+1.2%', trend: 'up', sector: 'Energy' },
  { symbol: 'TCS', price: '3,922.15', change: '-0.8%', trend: 'down', sector: 'IT' },
  { symbol: 'HDFCBANK', price: '1,672.40', change: '+2.1%', trend: 'up', sector: 'Banking' },
  { symbol: 'INFY', price: '1,545.80', change: '+0.5%', trend: 'up', sector: 'IT' },
  { symbol: 'ICICIBANK', price: '1,298.55', change: '-1.3%', trend: 'down', sector: 'Banking' },
];

const MOCK_TERMINAL_LOGS = [
  { sender: 'SYSTEM', text: 'Axiom V4.2 Mythic Pipeline initialized. 16 agents online.', time: '10:00:12', type: 'system' },
  { sender: 'ORCHESTRATOR', text: 'Fan-out dispatch → 5 specialists acquired targets.', time: '10:02:34', type: 'info' },
  { sender: 'TECH_SPEC', text: 'Bullish divergence detected: RELIANCE 4H MACD crossover.', time: '10:05:18', type: 'signal' },
  { sender: 'RISK_SPEC', text: 'Exposure alert: Banking sector weight exceeds 35% threshold.', time: '10:08:41', type: 'warning' },
  { sender: 'CRITIQUE', text: 'Calibration pass complete. Confidence adjusted: 0.87 → 0.92.', time: '10:12:07', type: 'info' },
  { sender: 'MACRO_SPEC', text: 'RBI policy neutral. No rate action expected this quarter.', time: '10:15:22', type: 'info' },
];

// ═══════════════════════════════════════════════════════════════════════════════
//  SHARED SUB-COMPONENTS
// ═══════════════════════════════════════════════════════════════════════════════

/** Glass-card wrapper with optional header. */
const DashCard = ({ children, title, icon: Icon, action, className = '', noPad = false }) => (
  <div className={`mc-card ${className}`}>
    {(title || Icon) && (
      <div className="mc-card-header">
        <div className="mc-card-title-group">
          {Icon && (
            <div className="mc-card-icon">
              <Icon size={14} />
            </div>
          )}
          <h3 className="mc-card-title">{title}</h3>
        </div>
        {action || (
          <div className="mc-card-dots">
            <span /><span /><span />
          </div>
        )}
      </div>
    )}
    <div className={noPad ? 'mc-card-body-raw' : 'mc-card-body'}>
      {children}
    </div>
  </div>
);

/** Top-level statistic tile. */
const StatTile = ({ label, value, change, icon: Icon, accentClass = 'mc-accent-indigo' }) => (
  <div className={`mc-stat-tile ${accentClass}`}>
    <div className="mc-stat-icon-wrap">
      <Icon size={20} />
    </div>
    <div className="mc-stat-content">
      <span className="mc-stat-label">{label}</span>
      <div className="mc-stat-row">
        <span className="mc-stat-value">{value}</span>
        {change && (
          <span className={`mc-stat-change ${change.startsWith('+') || change.startsWith('-') ? (change.startsWith('+') ? 'positive' : 'negative') : 'neutral'}`}>
            {change}
          </span>
        )}
      </div>
    </div>
  </div>
);

/** Single agent row with health + load bar. */
const AgentRow = ({ agent }) => {
  const statusMap = {
    active: { dot: 'mc-dot-active', label: 'ONLINE' },
    warning: { dot: 'mc-dot-warning', label: 'DEGRADED' },
    idle: { dot: 'mc-dot-idle', label: 'STANDBY' },
  };
  const s = statusMap[agent.status] || statusMap.idle;

  return (
    <div className="mc-agent-row">
      <div className="mc-agent-left">
        <div className={`mc-agent-dot ${s.dot}`} />
        <div className="mc-agent-info">
          <span className="mc-agent-name">{agent.name}</span>
          <span className="mc-agent-task">{agent.lastTask}</span>
        </div>
      </div>
      <div className="mc-agent-right">
        <span className="mc-agent-hp">{agent.health}%</span>
        <div className="mc-agent-bar-bg">
          <div
            className="mc-agent-bar-fill"
            style={{ width: `${agent.load}%` }}
          />
        </div>
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
//  MAIN DASHBOARD VIEW
// ═══════════════════════════════════════════════════════════════════════════════

export default function MissionControlDashboard({ agentsStatus = [], liveStocks = [] }) {
  const [agents, setAgents] = useState(MOCK_AGENTS);
  const [tickers, setTickers] = useState(MOCK_TICKERS);
  const [logs, setLogs] = useState(MOCK_TERMINAL_LOGS);
  const [currentTime, setCurrentTime] = useState(new Date());
  const [activeSection, setActiveSection] = useState('overview'); // overview | research

  // Clock tick
  useEffect(() => {
    const t = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  // Sync internal state with props from App.jsx
  useEffect(() => {
    if (agentsStatus && agentsStatus.length) {
      setAgents(agentsStatus.map(a => ({
        id: a.id || a.name,
        name: a.name,
        status: a.status === 'Active' ? 'active' : a.status === 'Standby' ? 'idle' : 'warning',
        load: a.load || Math.round(Math.random() * 40 + 10),
        health: a.acc || 100,
        lastTask: a.desc || 'Processing ReAct loop...',
      })));
    }
  }, [agentsStatus]);

  useEffect(() => {
    if (liveStocks && liveStocks.length) {
      // Map to MissionControl specific format if needed
      setTickers(liveStocks.slice(0, 5).map(s => ({
        symbol: s.id || s.name,
        price: s.px ? s.px.toLocaleString() : '0.00',
        change: s.chg > 0 ? `+${s.chg}%` : `${s.chg}%`,
        trend: s.chg >= 0 ? 'up' : 'down',
        sector: s.sector || 'Global'
      })));
    }
  }, [liveStocks]);

  // Simulated chart bars with slight randomization for realism
  const chartBars = useMemo(() => {
    const base = [38, 52, 45, 58, 72, 64, 78, 86, 82, 95, 91, 105, 100, 115, 110, 125, 132, 128, 142, 150, 145, 138, 152, 160];
    return base.map(v => v + Math.round((Math.random() - 0.5) * 8));
  }, []);
  const maxBar = Math.max(...chartBars);

  return (
    <div className="mc-root custom-scrollbar">

      {/* ═══ PAGE HEADER ═══ */}
      <div className="mc-page-header">
        <div className="mc-page-header-left">
          <h1 className="mc-page-title">Mission Control</h1>
          <p className="mc-page-subtitle">Consensus_Sweep // Neural_Fleet_v4.2</p>
        </div>
        <div className="mc-page-header-right">
          <div className="mc-header-clock">
            <Clock size={12} />
            <span>{currentTime.toLocaleTimeString()}</span>
          </div>
          <div className="mc-header-status-pill">
            <div className="mc-live-dot" />
            <span>LIVE ENGINE</span>
          </div>
        </div>
      </div>

      {/* ═══ SECTION TOGGLE ═══ */}
      <div className="mc-section-toggle">
        <button
          className={`mc-toggle-btn ${activeSection === 'overview' ? 'active' : ''}`}
          onClick={() => setActiveSection('overview')}
        >
          <Gauge size={13} />
          System Overview
        </button>
        <button
          className={`mc-toggle-btn ${activeSection === 'research' ? 'active' : ''}`}
          onClick={() => setActiveSection('research')}
        >
          <Target size={13} />
          Deep Research
        </button>
      </div>

      {/* ═══════ OVERVIEW SECTION ═══════ */}
      {activeSection === 'overview' && (
        <div className="mc-content animate-fade-in">

          {/* ── TOP STAT TILES ── */}
          <div className="mc-stats-grid">
            <StatTile label="Total AUM" value="₹12,84,500" change="+12.5%" icon={BarChart3} accentClass="mc-accent-indigo" />
            <StatTile label="Active Agents" value={`${agents.filter(a => a.status === 'active').length} / ${agents.length}`} change="Stable" icon={Cpu} accentClass="mc-accent-green" />
            <StatTile label="Risk Exposure" value="Medium" change="0.42 β" icon={ShieldAlert} accentClass="mc-accent-amber" />
            <StatTile label="Pipeline Latency" value="14ms" change="-2ms" icon={Zap} accentClass="mc-accent-violet" />
          </div>

          {/* ── MAIN 12-COL GRID ── */}
          <div className="mc-main-grid">

            {/* LEFT COLUMN (8/12) */}
            <div className="mc-col-primary">

              {/* Alpha Forecast Chart */}
              <DashCard title="Alpha Forecast Engine" icon={TrendingUp}>
                <div className="mc-chart-wrap">
                  <div className="mc-chart-bars">
                    {chartBars.map((h, i) => (
                      <div
                        key={i}
                        className="mc-bar"
                        style={{
                          height: `${(h / maxBar) * 100}%`,
                          animationDelay: `${i * 40}ms`,
                        }}
                      />
                    ))}
                  </div>
                  <div className="mc-chart-x-axis">
                    <span>09:15</span><span>10:30</span><span>11:45</span><span>13:00</span><span>14:15</span><span>15:30</span>
                  </div>
                </div>
              </DashCard>

              {/* Two-column sub-grid */}
              <div className="mc-sub-grid">

                {/* Terminal Logs */}
                <DashCard title="Axiom Terminal" icon={Terminal}>
                  <div className="mc-terminal">
                    {logs.map((msg, i) => (
                      <div key={i} className={`mc-log-line mc-log-${msg.type}`}>
                        <span className="mc-log-time">[{msg.time}]</span>
                        <span className="mc-log-sender">{msg.sender}</span>
                        <span className="mc-log-text">{msg.text}</span>
                      </div>
                    ))}
                    <div className="mc-log-cursor">
                      <span className="mc-cursor-blink">▌</span>
                      <span className="mc-cursor-text">Listening for agent updates...</span>
                    </div>
                  </div>
                </DashCard>

                {/* Risk Analysis */}
                <DashCard title="Risk Analysis" icon={ShieldAlert}>
                  <div className="mc-risk-stack">
                    <RiskBar label="Portfolio Volatility" value="Low (1.2%)" pct={15} color="emerald" />
                    <RiskBar label="Correlation Strength" value="Medium (0.65)" pct={65} color="amber" />
                    <RiskBar label="Drawdown Probability" value="8%" pct={8} color="emerald" />
                    <RiskBar label="Sharpe Ratio" value="1.84" pct={72} color="indigo" />
                    <RiskBar label="Beta Exposure" value="0.42" pct={42} color="amber" />
                  </div>
                </DashCard>
              </div>
            </div>

            {/* RIGHT COLUMN (4/12) */}
            <div className="mc-col-secondary">

              {/* Agent Health Matrix */}
              <DashCard title="Agent Health Matrix" icon={Layers} action={
                <button className="mc-refresh-btn" title="Refresh agents">
                  <RefreshCw size={12} />
                </button>
              }>
                <div className="mc-agents-list">
                  {agents.map(agent => (
                    <AgentRow key={agent.id} agent={agent} />
                  ))}
                </div>
              </DashCard>

              {/* Trending Tickers */}
              <DashCard title="Market Pulse" icon={Signal}>
                <div className="mc-tickers-list">
                  {tickers.map(ticker => (
                    <div key={ticker.symbol} className="mc-ticker-row">
                      <div className="mc-ticker-left">
                        <div className={`mc-ticker-arrow ${ticker.trend}`}>
                          {ticker.trend === 'up'
                            ? <ArrowUpRight size={14} />
                            : <ArrowDownRight size={14} />
                          }
                        </div>
                        <div className="mc-ticker-info">
                          <span className="mc-ticker-symbol">{ticker.symbol}</span>
                          <span className="mc-ticker-sector">{ticker.sector}</span>
                        </div>
                      </div>
                      <div className="mc-ticker-right">
                        <span className="mc-ticker-price">₹{ticker.price}</span>
                        <span className={`mc-ticker-change ${ticker.trend}`}>{ticker.change}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </DashCard>
            </div>
          </div>
        </div>
      )}

      {/* ═══════ RESEARCH SECTION ═══════ */}
      {activeSection === 'research' && (
        <div className="mc-content animate-fade-in">
          <DeepResearchSuggestions />
        </div>
      )}

      {/* ═══ FOOTER STATUS BAR ═══ */}
      <div className="mc-footer">
        <div className="mc-footer-left">
          <span className="mc-footer-item">
            <div className="mc-footer-dot online" /> DB: CONNECTED
          </span>
          <span className="mc-footer-item">
            <div className="mc-footer-dot online" /> LLM: STREAMING
          </span>
          <span className="mc-footer-item">
            <div className="mc-footer-dot online" /> SCHEDULER: ACTIVE
          </span>
        </div>
        <span className="mc-footer-build">AXIOM v4.2 // BUILD_7741</span>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
//  HELPER COMPONENTS
// ═══════════════════════════════════════════════════════════════════════════════

function RiskBar({ label, value, pct, color }) {
  const colorMap = {
    emerald: 'mc-riskbar-emerald',
    amber: 'mc-riskbar-amber',
    indigo: 'mc-riskbar-indigo',
    red: 'mc-riskbar-red',
  };
  return (
    <div className="mc-risk-item">
      <div className="mc-risk-meta">
        <span className="mc-risk-label">{label}</span>
        <span className={`mc-risk-value ${colorMap[color] || ''}`}>{value}</span>
      </div>
      <div className="mc-risk-track">
        <div className={`mc-risk-fill ${colorMap[color] || ''}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}
