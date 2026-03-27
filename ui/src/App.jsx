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

const API_BASE = "http://localhost:8000";

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
    { role:'ai', tag:'AXIOM OS', text:'System online. Cognitive engines fully spooled. Live market data streaming. Select a global node or input a command.' }
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
  const handleSendChat = async (userText, aiText, stockOverride = null) => {
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
              ticker: (stockOverride ? stockOverride.id : activeStock?.id) || '',
            }),
          });
          const data = await res.json();
          setChatMessages(p => [...p, { role:'ai', tag:'AXIOM', text: data.response }]);
        } catch (err) {
          setChatMessages(p => [...p, { role:'ai', tag:'AXIOM', text: 'Neural link interrupted. Reconnecting to agent matrix...' }]);
        }
        return;
      }
    }
    if (aiText && aiText !== 'auto-analyze') setChatMessages(p => [...p, { role:'ai', tag:'AXIOM', text: aiText }]);
  };

  const handleSelect = (ticker) => {
    setActiveStock(ticker);
    // Panel opens automatically via state
  };

  const runAnalysis = (stock) => {
    if (wsRef.current) wsRef.current.close();
    
    setIsAnalyzing(true);
    setAnalysisComplete(false);
    setAgentLogs([]);
    
    const ws = new WebSocket(`ws://localhost:8000/ws/analyze/${stock.id}`);
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
    { id:'globe',       icon: Globe,          label:'Global Map'    },
    { id:'watchlist',   icon: List,           label:'Watchlist'     },
    { id:'agents',      icon: Layers,         label:'Agent Matrix'  },
  ];

  const showSidebar = view === 'stock' || agentLogs.length > 0;

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
            <div className="w-9 h-9 rounded-2xl flex items-center justify-center transition-all"
              style={{
                background: 'linear-gradient(135deg, rgba(99,102,241,0.20), rgba(99,102,241,0.08))',
                border: '1px solid rgba(99,102,241,0.25)',
                boxShadow: '3px 3px 8px rgba(0,0,0,0.30), -1px -1px 4px rgba(99,102,241,0.05), inset 1px 1px 2px rgba(255,255,255,0.05), inset -1px -1px 3px rgba(0,0,0,0.20)'
              }}>
              <Activity size={16} className="text-indigo-400" />
            </div>
            <span className="font-bold tracking-[0.2em] text-sm text-white font-mono text-shadow-glow">
              AXIOM<span className="text-indigo-400">.AI</span>
            </span>
          </div>
          <div className="h-5 w-px bg-white/8 mx-2" />
          <div className="clay-badge" style={{ 
            background: 'linear-gradient(135deg, rgba(0,240,255,0.10), rgba(0,240,255,0.04))', 
            borderColor: 'rgba(0,240,255,0.18)',
            color: T.buy 
          }}>
            <div className="w-1.5 h-1.5 rounded-full animate-soft-pulse" style={{ background: T.buy, boxShadow: `0 0 8px ${T.buy}60` }} />
            <span className="text-[10px] font-bold tracking-widest">LIVE_DATA</span>
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
            {view === 'globe'     && <Globe3D onStockSelect={handleSelect} stocks={liveStocks} />}
            {view === 'watchlist' && <WatchlistView onSelect={handleSelect} stocks={liveStocks} marketIndices={marketIndices} loading={stocksLoading} />}
            {view === 'agents'    && <AgentMatrixView agentsStatus={agentsStatus} />}
            {activeStock && (
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
