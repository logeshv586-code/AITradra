import React, { useState, useEffect, Suspense, lazy } from "react";

// Lazy-loaded view components — each gets its own async chunk
const Globe3D = lazy(() => import("./components/Globe3D"));
const PredictionTableView = lazy(() => import("./components/PredictionTableView"));
const TrendingStocksView = lazy(() => import("./components/TrendingStocksView"));
const StockDetailView = lazy(() => import("./components/StockDetailView"));
const MissionControlDashboard = lazy(() => import("./components/MissionControlDashboard"));
const ChatPanel = lazy(() => import("./components/ChatPanel"));
const AgentMatrixView = lazy(() => import("./components/AgentMatrixView"));
const RiskAnalysisView = lazy(() => import("./components/RiskAnalysisView"));
const LiveTickerBar = lazy(() => import("./components/LiveTickerBar"));
const NewsEvidenceView = lazy(() => import("./components/NewsEvidenceView"));
const PortfolioInsightsView = lazy(() => import("./components/PortfolioInsightsView"));
const VirtualPortfolioView = lazy(() => import("./components/VirtualPortfolioView"));
const IntelligenceStatusView = lazy(() => import("./components/IntelligenceStatusView"));
import Logo from "./components/Logo";

import { MessageSquareText, Search, Activity, Cpu, Globe2, Layout, X, Bell, LayoutDashboard, Shield, TrendingUp, Presentation, Network, Clock, DollarSign, Loader2 } from "lucide-react";
import { API_BASE } from "./api_config";

function LazyFallback() {
  return (
    <div className="h-full flex flex-col items-center justify-center gap-4 bg-[var(--app-bg)] w-full animate-fade-in">
      <Loader2 size={24} className="text-[var(--accent)] animate-spin" />
      <span className="text-[12px] font-medium text-[var(--text-muted)]">Loading module...</span>
    </div>
  );
}


function SidebarItem({ icon, label, active, onClick, count }) {
  const ItemIcon = icon;
  return (
    <button
      onClick={onClick}
      className={`w-full flex items-center justify-between px-4 py-2.5 rounded-[var(--radius-md)] transition-colors mb-1
        ${active ? 'bg-[var(--accent-bg)] text-[var(--accent)] font-medium' : 'text-[var(--text-muted)] hover:bg-[#1e232b] hover:text-white'}`}
    >
      <div className="flex items-center gap-3">
        <ItemIcon size={16} />
        <span className="text-[13px]">{label}</span>
      </div>
      {count && (
         <span className={`text-[10px] px-2 py-0.5 rounded-[var(--radius-sm)] ${active ? "bg-[var(--accent)] text-white" : "bg-[#252a33] text-[var(--text-muted)]"}`}>
            {count}
         </span>
      )}
    </button>
  );
}

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="p-10 bg-black text-red-500 font-mono text-xs">
          <h1>React Error:</h1>
          <pre>{this.state.error?.toString()}</pre>
          <pre>{this.state.error?.stack}</pre>
        </div>
      );
    }
    return this.props.children;
  }
}

function AppContent() {
  const [activeView, setActiveView] = useState("World Map");
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [chatMessages, setChatMessages] = useState([]);
  const [agentsStatus, setAgentsStatus] = useState([]);
  const [liveStocks, setLiveStocks] = useState([]);
  const [selectedTicker, setSelectedTicker] = useState("AAPL");
  const [intelligenceStatus, setIntelligenceStatus] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [globalTime, setGlobalTime] = useState(new Date().toLocaleTimeString());


  // Background loops
  useEffect(() => {
    const fetchSys = async () => {
      try {
        const [a, s, g, i] = await Promise.all([
          fetch(`${API_BASE}/api/agents/status`),
          fetch(`${API_BASE}/api/market/watchlist`),
          fetch(`${API_BASE}/api/market/globe-data`),
          fetch(`${API_BASE}/api/intelligence/status`)
        ]);
        if(a.ok) {
           const sysAgents = await a.json();
           const agentsArray = Array.isArray(sysAgents) ? sysAgents : (sysAgents.agents || sysAgents.data || []);
           setAgentsStatus(agentsArray);
        }
        let hasWatchlistPayload = false;
        if(s.ok) {
           const sysData = await s.json();
           const stocksArray = Array.isArray(sysData) ? sysData : (sysData.stocks || sysData.data || []);
           if (stocksArray.length > 0) {
             hasWatchlistPayload = true;
             setLiveStocks(stocksArray);
           }
        }
        if(!hasWatchlistPayload && g.ok) {
           const globeData = await g.json();
           const globeStocks = Array.isArray(globeData) ? globeData : (globeData.value || globeData.data || []);
           setLiveStocks(globeStocks);
        }
        if(i.ok) {
           setIntelligenceStatus(await i.json());
        }
      } catch (err) {
        console.error("Live data fetch failed:", err);
      }
    };
    fetchSys();
    const sid = setInterval(fetchSys, 15000);
    const tid = setInterval(() => setGlobalTime(new Date().toLocaleTimeString()), 1000);
    return () => { clearInterval(sid); clearInterval(tid); };
  }, []);

  const handleStockSelect = (ticker) => {
    if (!ticker) return;
    setSelectedTicker(String(ticker).toUpperCase());
    setActiveView("Stock Terminal");
  };

  const handleSearchSubmit = (event) => {
    event.preventDefault();
    const query = searchQuery.trim().toUpperCase();
    if (!query) return;
    const matched = liveStocks.find((stock) => {
      const ticker = String(stock.id || stock.ticker || "").toUpperCase();
      const name = String(stock.name || "").toUpperCase();
      return ticker === query || ticker.startsWith(query) || name.includes(query);
    });
    handleStockSelect(matched?.id || matched?.ticker || query);
    setSearchQuery("");
  };

  const handleChat = async (text, ticker = null) => {
    const newMsg = { role: "user", text };
    setChatMessages(prev => [...prev, newMsg]);
    setIsChatOpen(true);
    
    try {
      const payload = { message: text, ticker: ticker || selectedTicker || "" };
      const res = await fetch(`${API_BASE}/api/chat`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        const data = await res.json();
        setChatMessages(prev => [...prev, { role: "ai", text: data.response || data.output }]);
      }
    } catch {
      setChatMessages(prev => [...prev, { role: "ai", text: "Connection to Axiom.AI expert system failed." }]);
    }
  };

  const navGroups = [
    {
      group: "CORE",
      items: [
        { id: "World Map", icon: Globe2 },
        { id: "Predictions", icon: Activity },
        { id: "Stock Terminal", icon: LayoutDashboard },
      ]
    },
    {
      group: "INTELLIGENCE",
      items: [
        { id: "Intelligence", icon: Presentation },
        { id: "Intelligence Status", icon: Activity },
        { id: "Agent Network", icon: Network, count: agentsStatus.length || null },
        { id: "News Evidence", icon: Layout },
        { id: "Risk Dynamics", icon: Shield },
        { id: "AI Expert Chat", icon: MessageSquareText },
      ]
    },
    {
       group: "PORTFOLIO",
       items: [
          { id: "Portfolio", icon: DollarSign },
          { id: "Paper Trading", icon: TrendingUp },
          { id: "Mission Control", icon: Cpu },
       ]
    }
  ];
  const providerLabel =
    intelligenceStatus?.model_router?.last_provider_used ||
    intelligenceStatus?.model_router?.active_provider ||
    "adaptive";

  return (
    <div className="flex h-screen w-full bg-[var(--app-bg)] text-[var(--text-main)] overflow-hidden font-sans">
      
      {/* ── SIDEBAR ── */}
      <aside className="w-[240px] flex-shrink-0 bg-[var(--sidebar-bg)] border-r border-[var(--border-color)] flex flex-col z-20">
        
        {/* Logo Area */}
        <div className="h-16 flex items-center px-6 border-b border-[var(--border-color)]">
           <div className="flex items-center gap-3 w-full">
              <div className="flex h-9 w-9 items-center justify-center rounded-[var(--radius-sm)] bg-[#0c0e12] border border-[var(--border-color)] shadow-inner">
                <Logo size={24} />
              </div>
              <div className="flex flex-col">
                 <h1 className="text-[15px] font-bold tracking-wide text-white leading-tight flex items-center gap-1">
                   AITradra<span className="text-[var(--accent)] text-[10px]">PRO</span>
                 </h1>
                 <span className="text-[9px] font-medium tracking-[0.1em] text-[var(--text-muted)] uppercase">Market Intelligence</span>
              </div>
           </div>
        </div>

        {/* Navigation Area */}
        <nav className="flex-1 overflow-y-auto no-scrollbar py-4 px-3 space-y-6">
           {navGroups.map((grp) => (
             <div key={grp.group}>
                <h3 className="text-small-caps px-4 mb-2">{grp.group}</h3>
                <div>
                   {grp.items.map(item => (
                      <SidebarItem 
                         key={item.id} 
                         icon={item.icon} 
                         label={item.id} 
                         active={activeView === item.id} 
                         count={item.count}
                         onClick={() => setActiveView(item.id)} 
                      />
                   ))}
                </div>
             </div>
           ))}
        </nav>

        {/* Footer Settings/User Area */}
        <div className="p-4 border-t border-[var(--border-color)]">
           <div className="flex items-center gap-3 px-2 py-2 rounded-[var(--radius-md)] hover:bg-[#1e232b] cursor-pointer transition">
              <div className="h-8 w-8 rounded-full bg-[var(--accent)] flex items-center justify-center text-white bg-opacity-20 border border-[var(--accent)] font-semibold text-[11px]">
                 AIT
              </div>
              <div>
                 <p className="text-[13px] font-medium text-white">Operator</p>
                 <p className="text-[10px] text-[var(--text-muted)] font-mono tracking-wider">AITRADRA PRO</p>
              </div>
           </div>
        </div>
      </aside>

      {/* ── MAIN CONTENT AREA ── */}
      <main className="flex-1 flex flex-col min-w-0 relative">
        
        {/* Top Header */}
        <header className="h-16 flex-shrink-0 flex items-center justify-between px-6 border-b border-[var(--border-color)] bg-[var(--app-bg)] z-10">
           
           {/* Left: View Title & Status */}
           <div className="flex items-center gap-4 hidden sm:flex">
              <h2 className="heading-2">{activeView}</h2>
              <div className="h-4 w-px bg-[var(--border-color)]" />
              <div className="flex items-center gap-2">
                 <div className="h-2 w-2 rounded-full bg-[var(--positive)]" />
                 <span className="text-[11px] font-medium text-[var(--text-muted)] uppercase tracking-wider">{providerLabel} online</span>
              </div>
           </div>

           {/* Mobile header view */}
           <div className="flex sm:hidden items-center gap-2">
               <h2 className="heading-3">{activeView}</h2>
           </div>

           {/* Right: Actions (Responsive spaced) */}
           <div className="flex items-center gap-3 sm:gap-4 ml-auto">
              {/* Search Bar - Hide on very small screens, show on md+ */}
              <form onSubmit={handleSearchSubmit} className="hidden md:flex relative w-48 lg:w-64">
                 <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-muted)]" />
                 <input 
                    type="text" 
                    value={searchQuery}
                    onChange={(event) => setSearchQuery(event.target.value)}
                    placeholder="Search tickers..." 
                    className="input-standard pl-9 py-1.5 h-8 placeholder-[var(--text-muted)]"
                 />
                 <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-0.5">
                    <kbd className="px-1.5 py-0.5 text-[9px] font-mono bg-[#252a33] text-[var(--text-muted)] rounded border border-[var(--border-color)]">⌘K</kbd>
                 </div>
              </form>

              {/* Time - hidden on mobile */}
              <div className="hidden lg:flex items-center gap-2 text-[var(--text-muted)]">
                 <Clock size={14} />
                 <span className="text-[12px] font-mono">{globalTime}</span>
              </div>

              <div className="hidden sm:block h-4 w-px bg-[var(--border-color)]" />

              {/* Notifications */}
              <button className="h-8 w-8 flex items-center justify-center rounded-[var(--radius-md)] text-[var(--text-muted)] hover:bg-[#1e232b] hover:text-white transition">
                 <Bell size={16} />
              </button>

              {/* Chat Toggle Button */}
              <button 
                 onClick={() => setIsChatOpen(!isChatOpen)}
                 className={`btn-standard h-8 px-3 ${isChatOpen ? 'bg-[#1e232b] text-white border-slate-600' : ''}`}
              >
                 <MessageSquareText size={14} />
                 <span className="hidden sm:inline">AI Chat</span>
              </button>
           </div>
        </header>

        {/* Live Ticker Bar (Placed below header, span full width of main) */}
        <div className="flex-shrink-0 bg-[#0c0e12] border-b border-[var(--border-color)] w-full overflow-hidden">
           <Suspense fallback={null}>
             <LiveTickerBar stocks={liveStocks} onSelect={handleStockSelect} />
           </Suspense>
        </div>

        {/* Dynamic View Rendering Area */}
        <section className="flex-1 overflow-hidden relative">
          <div className="absolute inset-0 z-0">
             <Suspense fallback={<LazyFallback />}>
               {activeView === "World Map" && <Globe3D stocks={liveStocks} onStockSelect={handleStockSelect} />}
             </Suspense>
          </div>

          <div className={`absolute inset-0 z-10 overflow-y-auto no-scrollbar pointer-events-auto transition-opacity duration-300 ${activeView === "World Map" ? "pointer-events-none opacity-0" : "opacity-100 bg-[var(--app-bg)]"}`}>
            <Suspense fallback={<LazyFallback />}>
            {activeView === "Predictions" && <PredictionTableView onSelect={handleStockSelect} />}
            {activeView === "Stock Terminal" && <StockDetailView ticker={selectedTicker} />}
            {activeView === "Agent Network" && <AgentMatrixView agents={agentsStatus} />}
            {activeView === "Intelligence" && <TrendingStocksView stocks={liveStocks} onSelect={handleStockSelect} />}
            {activeView === "Intelligence Status" && <IntelligenceStatusView />}
            {activeView === "Risk Dynamics" && <RiskAnalysisView />}
            {activeView === "Mission Control" && <MissionControlDashboard agentsStatus={agentsStatus} />}
            {activeView === "Portfolio" && <PortfolioInsightsView />}
            {activeView === "Paper Trading" && <VirtualPortfolioView />}
            {activeView === "News Evidence" && <NewsEvidenceView />}
            {activeView === "AI Expert Chat" && <ChatPanel messages={chatMessages} onSend={(text) => handleChat(text, selectedTicker)} fullView={true} intelligenceStatus={intelligenceStatus} />}
            </Suspense>
          </div>
        </section>
      </main>

      {/* ── SLIDE OUT CHAT DRAWER ── */}
      {isChatOpen && activeView !== "AI Expert Chat" && (
        <>
          <div className="drawer-overlay" onClick={() => setIsChatOpen(false)} />
          <div className="drawer-panel flex flex-col">
            <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--border-color)] bg-[var(--card-bg)]">
              <div className="flex items-center gap-2">
                 <div className="h-2 w-2 rounded-full bg-[var(--accent)]" />
                 <h3 className="heading-3">MYTHIC Chat</h3>
              </div>
              <button onClick={() => setIsChatOpen(false)} className="text-[var(--text-muted)] hover:text-white transition">
                <X size={18} />
              </button>
            </div>
            <div className="flex-1 overflow-hidden">
              <Suspense fallback={<LazyFallback />}>
                <ChatPanel messages={chatMessages} onSend={(t) => handleChat(t, selectedTicker)} intelligenceStatus={intelligenceStatus} />
              </Suspense>
            </div>
          </div>
        </>
      )}

    </div>
  );
}

export default function App() {
  return (
    <ErrorBoundary>
      <AppContent />
    </ErrorBoundary>
  );
}
