import React, { useState, useEffect } from "react";
import Globe3D from "./components/Globe3D";
import PredictionTableView from "./components/PredictionTableView";
import TrendingStocksView from "./components/TrendingStocksView";
import StockDetailView from "./components/StockDetailView";
import MissionControlDashboard from "./components/MissionControlDashboard";
import ChatPanel from "./components/ChatPanel";
import AgentMatrixView from "./components/AgentMatrixView";
import RiskAnalysisView from "./components/RiskAnalysisView";
import MarketStatusBadges from "./components/MarketStatusBadges";
import LiveTickerBar from "./components/LiveTickerBar";
import NewsEvidenceView from "./components/NewsEvidenceView";
import PortfolioInsightsView from "./components/PortfolioInsightsView";
import VirtualPortfolioView from "./components/VirtualPortfolioView";

import { MessageSquareText, Search, Activity, Cpu, Globe2, Layout, X, Bell, LayoutDashboard, Shield, TrendingUp, Presentation, CheckCircle, Network, Clock, DollarSign } from "lucide-react";
import { API_BASE } from "./api_config";

function SidebarItem({ icon: Icon, label, active, onClick, count }) {
  return (
    <button
      onClick={onClick}
      className={`w-full flex items-center justify-between px-4 py-2.5 rounded-[var(--radius-md)] transition-colors mb-1
        ${active ? 'bg-[var(--accent-bg)] text-[var(--accent)] font-medium' : 'text-[var(--text-muted)] hover:bg-[#1e232b] hover:text-white'}`}
    >
      <div className="flex items-center gap-3">
        <Icon size={16} />
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
  const [globalTime, setGlobalTime] = useState(new Date().toLocaleTimeString());


  // Background loops
  useEffect(() => {
    const fetchSys = async () => {
      try {
        const [a, s] = await Promise.all([
          fetch(`${API_BASE}/api/agents/status`),
          fetch(`${API_BASE}/api/market/trending?limit=4`)
        ]);
        if(a.ok) {
           const sysAgents = await a.json();
           const agentsArray = Array.isArray(sysAgents) ? sysAgents : (sysAgents.agents || sysAgents.data || []);
           setAgentsStatus(agentsArray);
        }
        if(s.ok) {
           const sysData = await s.json();
           const stocksArray = Array.isArray(sysData) ? sysData : (sysData.top_movers || sysData.data || []);
           setLiveStocks(stocksArray);
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

  const handleChat = async (text, ticker = null) => {
    const newMsg = { role: "user", text };
    setChatMessages(prev => [...prev, newMsg]);
    setIsChatOpen(true);
    
    try {
      const payload = { prompt: text, ticker: ticker };
      const res = await fetch(`${API_BASE}/api/agents/chat`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        const data = await res.json();
        setChatMessages(prev => [...prev, { role: "ai", text: data.response || data.output }]);
      }
    } catch (e) {
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
        { id: "Agent Network", icon: Network, count: agentsStatus.length || null },
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

  return (
    <div className="flex h-screen w-full bg-[var(--app-bg)] text-[var(--text-main)] overflow-hidden font-sans">
      
      {/* ── SIDEBAR ── */}
      <aside className="w-[240px] flex-shrink-0 bg-[var(--sidebar-bg)] border-r border-[var(--border-color)] flex flex-col z-20">
        
        {/* Logo Area */}
        <div className="h-16 flex items-center px-6 border-b border-[var(--border-color)]">
           <div className="flex items-center gap-3 w-full">
              <div className="flex h-8 w-8 items-center justify-center rounded-[var(--radius-sm)] bg-[var(--accent)] text-white">
                <Activity size={18} />
              </div>
              <div className="flex flex-col">
                 <h1 className="text-[14px] font-bold tracking-wide text-white leading-tight">AXIOM<span className="text-[var(--accent)]">.AI</span></h1>
                 <span className="text-[9px] font-medium tracking-[0.1em] text-[var(--text-muted)] uppercase">Trading Intelligence</span>
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
              <div className="h-8 w-8 rounded-full bg-[#1e232b] flex items-center justify-center border border-[var(--border-color)] text-[var(--text-muted)]">
                 AX
              </div>
              <div>
                 <p className="text-[13px] font-medium text-white">Operator</p>
                 <p className="text-[10px] text-[var(--text-muted)]">AXIOM PRO</p>
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
                 <span className="text-[11px] font-medium text-[var(--text-muted)] uppercase tracking-wider">System Online</span>
              </div>
           </div>

           {/* Mobile header view */}
           <div className="flex sm:hidden items-center gap-2">
               <h2 className="heading-3">{activeView}</h2>
           </div>

           {/* Right: Actions (Responsive spaced) */}
           <div className="flex items-center gap-3 sm:gap-4 ml-auto">
              {/* Search Bar - Hide on very small screens, show on md+ */}
              <div className="hidden md:flex relative w-48 lg:w-64">
                 <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-muted)]" />
                 <input 
                    type="text" 
                    placeholder="Search tickers..." 
                    className="input-standard pl-9 py-1.5 h-8 placeholder-[var(--text-muted)]"
                 />
                 <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-0.5">
                    <kbd className="px-1.5 py-0.5 text-[9px] font-mono bg-[#252a33] text-[var(--text-muted)] rounded border border-[var(--border-color)]">⌘K</kbd>
                 </div>
              </div>

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
           <LiveTickerBar />
        </div>

        {/* Dynamic View Rendering Area */}
        <section className="flex-1 overflow-hidden relative">
          <div className="absolute inset-0 z-0">
             {activeView === "World Map" && <Globe3D stocks={liveStocks} />}
          </div>

          <div className={`absolute inset-0 z-10 overflow-y-auto no-scrollbar pointer-events-auto transition-opacity duration-300 ${activeView === "World Map" ? "pointer-events-none opacity-0" : "opacity-100 bg-[var(--app-bg)]"}`}>
            {activeView === "Predictions" && <PredictionTableView />}
            {activeView === "Stock Terminal" && <StockDetailView stock={{ id: "AAPL", name: "Apple Inc.", px: 175.24, chg: 1.2 }} />}
            {activeView === "Agent Network" && <AgentMatrixView agents={agentsStatus} />}
            {activeView === "Intelligence" && <TrendingStocksView stocks={liveStocks} />}
            {activeView === "Risk Dynamics" && <RiskAnalysisView />}
            {activeView === "Mission Control" && <MissionControlDashboard agentsStatus={agentsStatus} liveStocks={liveStocks} />}
            {activeView === "Portfolio" && <PortfolioInsightsView />}
            {activeView === "Paper Trading" && <VirtualPortfolioView />}
            {activeView === "News Evidence" && <NewsEvidenceView />}
            {activeView === "AI Expert Chat" && <ChatPanel messages={chatMessages} onSend={handleChat} fullView={true} />}
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
               <ChatPanel messages={chatMessages} onSend={(t) => handleChat(t)} />
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
