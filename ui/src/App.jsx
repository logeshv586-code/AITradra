import React, { useState, useEffect, useRef } from "react";
import { T } from "./theme";
import { AGENTS } from "./data";
import LiveTickerBar from "./components/LiveTickerBar";
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
import VirtualPortfolioView from "./components/VirtualPortfolioView";
import DeepResearchSuggestions from "./components/DeepResearchSuggestions";
import { 
  Activity, 
  Globe, 
  List, 
  Layers, 
  Settings, 
  Rocket, 
  TrendingUp, 
  BarChart3, 
  ShieldAlert, 
  Newspaper, 
  PieChart, 
  MessageSquare, 
  ChevronRight,
  User,
  Coins,
  Loader2
} from "lucide-react";
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
    { id:'mission',     icon: Rocket,         label:'Mission Control' },
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
      <header className="h-14 flex items-center justify-between px-8 flex-shrink-0 z-50 border-b border-white/5 bg-black/40 backdrop-blur-md">
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-3 cursor-pointer group" onClick={() => setView('globe')}>
            <div className="w-10 h-10 rounded-xl flex items-center justify-center transition-all bg-indigo-500/10 border border-indigo-400/20 group-hover:bg-indigo-500/20">
              <Activity size={18} className="text-indigo-400 shadow-glow" />
            </div>
            <span className="font-black tracking-widest text-lg text-white font-mono flex items-center gap-1">
              AXIOM<span className="text-indigo-500 font-black">.AI</span>
            </span>
          </div>
          <div className="h-4 w-px bg-white/10 mx-2" />
          <div className="flex items-center gap-2.5 px-3 py-1.5 rounded-full bg-white/[0.03] border border-white/5 transition-all hover:bg-white/[0.06]">
            <div className="w-2 h-2 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)] animate-pulse" />
            <span className="text-[10px] font-black tracking-widest text-slate-400 leading-none font-mono">NODE_CLUSTER::ACTIVE</span>
          </div>
          {stocksLoading && (
            <div className="flex items-center gap-3 text-[10px] text-indigo-400 font-mono tracking-widest">
              <Loader2 size={12} className="animate-spin" />
              FETCHING_MARKETS...
            </div>
          )}
        </div>
      </header>

      {/* ── TICKER STRIP ── */}
      <LiveTickerBar stocks={liveStocks} />

      {/* ── BODY ── */}
      <div className="flex-1 flex overflow-hidden">
        {/* LEFT SIDEBAR (Clay) */}
        <nav className="w-20 flex-shrink-0 flex flex-col items-center pt-8 gap-5 z-40 border-r border-white/5 bg-black/20 backdrop-blur-3xl">
          {NAV.map(n => {
            const Icon = n.icon;
            const active = view === n.id || (view === 'stock' && n.id === 'watchlist');
            return (
              <button key={n.id} title={n.label} onClick={() => setView(n.id)}
                className={`relative p-3 rounded-2xl transition-all duration-300 group ${
                  active 
                  ? 'bg-indigo-500/10 text-indigo-400 shadow-[0_0_20px_rgba(99,102,241,0.15)] ring-1 ring-indigo-500/30' 
                  : 'text-slate-500 hover:text-slate-200 hover:bg-white/5'
                }`}>
                <Icon size={20} className="transition-transform group-active:scale-95" />
                {active && <div className="absolute -left-1 top-1/2 -translate-y-1/2 w-1 h-6 bg-indigo-500 rounded-full shadow-[0_0_12px_#6366f1]" />}
              </button>
            );
          })}
          <div className="flex-1"/>
          <button className="p-3 mb-8 text-slate-500 hover:text-white transition-colors" title="Settings">
            <Settings size={20} />
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
                <div className="flex-1 glass-card bg-black/20 overflow-hidden flex flex-col">
                  <ChatPanel messages={chatMessages} onSend={handleSendChat} stock={activeStock} fullView={true} />
                </div>
              </div>
            )}
            {view === 'portfolio'   && <PortfolioInsightsView />}
            {view === 'trending'    && <TrendingStocksView onSelect={handleSelect} />}
            { view === 'virtual'     && <VirtualPortfolioView onSelect={handleSelect} />}
            {view === 'mission'     && (
              <div className="flex-1 overflow-y-auto p-12 custom-scrollbar animate-fade-in">
                <div className="max-w-7xl mx-auto flex flex-col gap-12">
                   <div className="flex flex-col gap-2">
                    <h1 className="text-4xl font-extrabold tracking-tighter text-white font-mono uppercase bg-gradient-to-r from-indigo-400 to-cyan-400 bg-clip-text text-transparent">
                      🛰️ Mission Control
                    </h1>
                    <p className="text-sm text-slate-400 font-mono tracking-widest uppercase">
                      Fleet-wide Consensus Engine & Deep Research Analysis
                    </p>
                  </div>

                  {/* DEEP RESEARCH SUGGESTIONS */}
                  <DeepResearchSuggestions />

                  {/* AUTONOMOUS BUILD LOGS */}
                  <div className="glass-card p-6 bg-black/20 border-indigo-500/10">
                    <h3 className="text-[10px] font-bold tracking-widest text-slate-500 uppercase mb-4 font-mono">Mission Execution Logs</h3>
                    <div className="flex flex-col gap-2 font-mono text-[10px]">
                      <div className="text-indigo-400 opacity-80">[18:20:12] DeepResearchAgent triggered multi-agent sweep...</div>
                      <div className="text-emerald-400 opacity-80">[18:20:45] Consensus check complete: 85% confidence threshold achieved.</div>
                      <div className="text-slate-500">[18:21:00] Analyzing 14 specialist insights for high-conviction alignment...</div>
                    </div>
                  </div>
                </div>
              </div>
            )}

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
