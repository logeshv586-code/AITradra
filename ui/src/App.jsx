import React, { useState, useEffect, useRef } from "react";
import { Activity, Globe, List, Layers, Settings } from "lucide-react";
import { T } from "./theme";
import { AGENTS } from "./data";
import LiveTickerBar from "./components/LiveTickerBar";
import GlobeView from "./components/GlobeView";
import WatchlistView from "./components/WatchlistView";
import AgentMatrixView from "./components/AgentMatrixView";
import StockDetailView from "./components/StockDetailView";
import AgentStreamPanel from "./components/AgentStreamPanel";
import ChatPanel from "./components/ChatPanel";
import Globe3D from "./components/Globe3D";
import StockDetailPanel from "./components/StockDetailPanel";
import PredictionTableView from "./components/PredictionTableView";
import NewsEvidenceView from "./components/NewsEvidenceView";
import PortfolioInsightsView from "./components/PortfolioInsightsView";
import TrendingStocksView from "./components/TrendingStocksView";
import RiskAnalysisView from "./components/RiskAnalysisView";
import { 
  TrendingUp, 
  BarChart3, 
  ShieldAlert, 
  Newspaper, 
  PieChart, 
  MessageSquare, 
  ChevronRight,
  User,
  Coins
} from "lucide-react";
import VirtualPortfolioView from "./components/VirtualPortfolioView";
import DiagnosticView from "./components/DiagnosticView";
import { Activity as Pulse } from "lucide-react";
import { API_BASE, WS_BASE } from "./api_config";

export default function App() {
  const [view, setView] = useState('globe');
  const [activeStock, setActiveStock] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisComplete, setAnalysisComplete] = useState(false);
  const [agentLogs, setAgentLogs] = useState([]);
  const [marketIndices, setMarketIndices] = useState([]);
  const [agentsStatus, setAgentsStatus] = useState([]);
  const [liveStocks, setLiveStocks] = useState([]);
  const [stocksLoading, setStocksLoading] = useState(true);
  const [chatMessages, setChatMessages] = useState([
    { role:'ai', tag:'AXIOM MYTHIC', text:'System online. Mythic Orchestrator active — 5 specialist agents + critique layer ready. Live market data streaming. Select a node or ask a question.' }
  ]);
  const wsRef = useRef(null);

  // ─── FETCH LIVE WATCHLIST + INDICES ─────────────────────────────────────────
  useEffect(() => {
    const fetchLiveData = async () => {
      try {
        const [watchlistRes, indicesRes, agentsRes] = await Promise.all([
          fetch(`${API_BASE}/api/market/watchlist`),
          fetch(`${API_BASE}/api/market/indices`),
          fetch(`${API_BASE}/api/agents/status`)
        ]);
        
        const watchlistData = await watchlistRes.json();
        const indicesData = await indicesRes.json();
        const agentsData = await agentsRes.json();

        if (watchlistData.stocks && watchlistData.stocks.length > 0) {
          setLiveStocks(watchlistData.stocks);
        }
        setMarketIndices(indicesData.indices || []);
        setAgentsStatus(agentsData.agents || []);
        setStocksLoading(false);
      } catch (err) {
        console.error("Failed to fetch live data:", err);
        setStocksLoading(false);
      }
    };

    fetchLiveData();
    // Refresh every 60s (aligned with backend cache TTL)
    const interval = setInterval(fetchLiveData, 60000);
    return () => clearInterval(interval);
  }, []);

  // ─── CHAT (LLM-POWERED) ───────────────────────────────────────────────────
  const handleSendChat = async (userText, aiText, mythicData = null) => {
    if (userText) {
      setChatMessages(p => [...p, { role:'user', text: userText }]);
      
      // If no AI text provided, call the LLM endpoint
      if (!aiText) {
        try {
          const res = await fetch(`${API_BASE}/api/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              message: userText,
              ticker: (activeStock?.id) || '',
            }),
          });
          const data = await res.json();
          setChatMessages(p => [...p, { 
            role:'ai', tag:'AXIOM MYTHIC', text: data.response,
            mythicData: {
              consensus: data.consensus,
              confidence: data.confidence,
              specialist_outputs: data.specialist_outputs,
              critique: data.critique,
              pipeline_ms: data.pipeline_ms,
            }
          }]);
        } catch (err) {
          setChatMessages(p => [...p, { role:'ai', tag:'AXIOM', text: 'Neural link interrupted. Reconnecting to mythic orchestrator...' }]);
        }
        return;
      }
    }
    if (aiText && aiText !== 'auto-analyze') {
      const msg = { role:'ai', tag:'AXIOM MYTHIC', text: aiText };
      if (mythicData) {
        msg.mythicData = {
          consensus: mythicData.consensus,
          confidence: mythicData.confidence,
          specialist_outputs: mythicData.specialist_outputs,
          critique: mythicData.critique,
        };
      }
      setChatMessages(p => [...p, msg]);
    }
  };

  const handleSelect = (ticker) => {
    // Look up the full stock object from liveStocks
    const stockId = typeof ticker === 'string' ? ticker : ticker.id;
    const found = liveStocks.find(s => s.id === stockId);
    if (found) {
      setActiveStock(found);
      // Optionally switch to detail view, or just keep panel open
      // setView('stock_detail'); 
    } else {
      setActiveStock({ id: stockId });
    }
    // Panel opens automatically via state if activeStock is set
  };

  const runAnalysis = (stock) => {
    if (wsRef.current) wsRef.current.close();
    
    setIsAnalyzing(true);
    setAnalysisComplete(false);
    setAgentLogs([]);
    
    const ws = new WebSocket(`${WS_BASE}/ws/analyze/${stock.id}`);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.type === 'connected') {
        setAgentLogs(p => [...p, { id: 'conn', agent: 'data', action: 'D-NETWORK', text: `Uplink established for ${msg.ticker} (v${msg.version})` }]);
      } else if (msg.type === 'agent_start' || msg.type === 'agent_complete') {
        const agentKey = msg.agent.replace('Agent', '').toLowerCase();
        setAgentLogs(p => [...p, { 
          id: Date.now() + Math.random(), 
          agent: agentKey, 
          action: msg.type === 'agent_start' ? 'THINK' : 'ACT', 
          text: msg.output 
        }]);
      } else if (msg.type === 'analysis_complete') {
        const analysis = msg.result.analysis || {};
        const confidence = analysis.confidence || 0.82;
        const signal = analysis.signal || (confidence > 0.7 ? 'STRONG BUY' : 'HOLD');
        
        setIsAnalyzing(false);
        setAnalysisComplete(true);
        
        // Update activeStock with live analysis result
        setActiveStock(prev => ({
          ...prev,
          analysis_result: analysis,
          px: msg.result.ticker === prev.id ? (msg.result.agent_data?.DataAgent?.fundamentals?.current_price || prev.px) : prev.px
        }));

        handleSendChat(null, `Analysis complete for ${stock.id}. Confidence: ${(confidence * 100).toFixed(1)}%. Signal: ${signal}.`);
      } else if (msg.type === 'error') {
        console.error("WS Analysis Error:", msg.message);
        setIsAnalyzing(false);
      }
    };

    ws.onclose = () => {
      setIsAnalyzing(false);
      wsRef.current = null;
    };
  };

  const NAV = [
    { id:'globe',       icon: Globe,          label:'Global Market'   },
    { id:'predictions', icon: BarChart3,      label:'Prediction Table'},
    { id:'stock_detail',icon: ChevronRight,   label:'Stock Detail'    },
    { id:'news',        icon: Newspaper,      label:'News & Evidence' },
    { id:'agents',      icon: Layers,         label:'AI Analysis'     },
    { id:'risk',        icon: ShieldAlert,    label:'Risk Analysis'   },
    { id:'chat',        icon: MessageSquare,  label:'AI Chat'         },
    { id:'portfolio',   icon: PieChart,       label:'Portfolio'       },
    { id:'trending',    icon: TrendingUp,     label:'Trending Stocks' },
    { id:'virtual',     icon: Coins,          label:'Virtual Portfolio'},
    { id:'diagnostics', icon: Pulse,          label:'System Diagnostics'},
  ];

  const showSidebar = (view === 'globe' || view === 'predictions' || view === 'watchlist') && (activeStock || agentLogs.length > 0);

  return (
    <div className="relative flex flex-col h-screen overflow-hidden text-slate-200 font-sans selection:bg-indigo-500/30">
      {/* ── AMBIENT CLAY-COMPATIBLE BACKGROUND ── */}
      <div className="fixed inset-0 pointer-events-none z-[-1]">
        <div className="absolute inset-0" style={{ background: 'linear-gradient(135deg, #0a0e1a 0%, #0d1225 40%, #0a0e1a 100%)' }} />
        <div className="absolute top-[-25%] left-[-15%] w-[55vw] h-[55vw] rounded-full blur-[150px] mix-blend-screen" style={{ background: 'radial-gradient(circle, rgba(99,102,241,0.06) 0%, transparent 70%)' }} />
        <div className="absolute bottom-[-25%] right-[-15%] w-[45vw] h-[45vw] rounded-full blur-[150px] mix-blend-screen" style={{ background: 'radial-gradient(circle, rgba(0,240,255,0.05) 0%, transparent 70%)' }} />
        <div className="absolute top-[40%] left-[50%] w-[30vw] h-[30vw] rounded-full blur-[120px] mix-blend-screen" style={{ background: 'radial-gradient(circle, rgba(168,85,247,0.04) 0%, transparent 70%)' }} />
      </div>

      {/* ── TOP BAR (Clay Header) ── */}
      <header className="clay-header h-14 flex items-center justify-between px-6 flex-shrink-0 z-50">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-3 cursor-pointer group" onClick={() => setView('globe')}>
            <div className="w-9 h-9 rounded-2xl flex items-center justify-center transition-all bg-indigo-500/10 border border-indigo-400/20 shadow-lg">
              <Activity size={16} className="text-indigo-400" />
            </div>
            <span className="font-bold tracking-[0.2em] text-sm text-white font-mono text-shadow-glow">
              AXIOM<span className="text-indigo-400">.AI</span>
            </span>
          </div>
          <div className="h-5 w-px bg-white/20 mx-4" />
          <div className="clay-badge" style={{ 
            background: 'linear-gradient(135deg, rgba(0,240,255,0.10), rgba(0,240,255,0.04))', 
            borderColor: 'rgba(0,240,255,0.18)',
            color: T.buy 
          }}>
            <div className="w-1.5 h-1.5 rounded-full animate-soft-pulse" style={{ background: T.buy, boxShadow: `0 0 8px ${T.buy}60` }} />
            <span className="text-[10px] font-bold tracking-widest leading-none">LIVE_DATA</span>
          </div>
          {stocksLoading && (
            <div className="flex items-center gap-2 text-[9px] text-cyan-400 font-mono animate-pulse">
              <div className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-ping" />
              FETCHING MARKETS...
            </div>
          )}
        </div>
      </header>

      {/* ── TICKER STRIP ── */}
      <LiveTickerBar stocks={liveStocks} />

      {/* ── BODY ── */}
      <div className="flex-1 flex overflow-hidden">
        {/* LEFT SIDEBAR (Clay) */}
        <nav className="clay-sidebar w-16 flex-shrink-0 flex flex-col items-center pt-6 gap-3 z-40">
          {NAV.map(n => {
            const Icon = n.icon;
            const active = view === n.id || (view === 'stock' && n.id === 'watchlist');
            return (
              <button key={n.id} title={n.label} onClick={() => setView(n.id)}
                className={`clay-nav-btn group relative ${active ? 'active' : ''}`}>
                <Icon size={18} className={`transition-colors ${active ? 'text-indigo-400' : 'text-slate-500 group-hover:text-indigo-400'}`} />
              </button>
            );
          })}
          <div className="flex-1"/>
          <button className="clay-nav-btn mb-6 text-slate-500 hover:text-white" title="Settings">
            <Settings size={18} />
          </button>
        </nav>

        {/* MAIN CONTENT */}
        <main className="flex-1 flex overflow-hidden relative z-10">
          <div className="flex-1 flex flex-col overflow-hidden">
            {view === 'globe'       && <Globe3D onStockSelect={handleSelect} stocks={liveStocks} />}
            {view === 'predictions' && <PredictionTableView onSelect={handleSelect} />}
            {view === 'stock_detail'&& (
              activeStock ? (
                <StockDetailView 
                  stock={activeStock} 
                  isAnalyzing={isAnalyzing} 
                  analysisComplete={analysisComplete} 
                  agentLogs={agentLogs} 
                />
              ) : (
                <div className="flex-1 flex items-center justify-center text-slate-500 font-mono text-xs uppercase tracking-widest">
                  Select a stock to view detailed intelligence matrix
                </div>
              )
            )}
            {view === 'news'        && <NewsEvidenceView />}
            {view === 'agents'      && <AgentMatrixView agentsStatus={agentsStatus} />}
            {view === 'risk'        && <RiskAnalysisView onSelect={handleSelect} />}
            {view === 'chat'        && (
              <div className="flex-1 flex flex-col p-8 animate-fade-in">
                <div className="flex-1 clay-card bg-black/40 overflow-hidden flex flex-col">
                  <ChatPanel messages={chatMessages} onSend={handleSendChat} stock={activeStock} fullView={true} />
                </div>
              </div>
            )}
            {view === 'portfolio'   && <PortfolioInsightsView />}
            {view === 'trending'    && <TrendingStocksView onSelect={handleSelect} />}
            {view === 'virtual'     && <VirtualPortfolioView onSelect={handleSelect} />}
            {view === 'diagnostics' && <DiagnosticView />}

            {activeStock && view !== 'stock_detail' && (
              <StockDetailPanel ticker={activeStock} onClose={() => setActiveStock(null)} />
            )}
          </div>

          {/* RIGHT SIDEBAR */}
          <aside className="w-80 flex-shrink-0 flex flex-col overflow-hidden z-20">
            {showSidebar && <AgentStreamPanel logs={agentLogs} isAnalyzing={isAnalyzing} />}
            <ChatPanel messages={chatMessages} onSend={handleSendChat} stock={activeStock} />
          </aside>
        </main>
      </div>
    </div>
  );
}
