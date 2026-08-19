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
import AskBar from "./components/AskBar";

import {
  MessageSquareText,
  Activity,
  Cpu,
  Globe2,
  Layout,
  X,
  Bell,
  LayoutDashboard,
  Shield,
  TrendingUp,
  Presentation,
  Network,
  Clock,
  DollarSign,
  Loader2,
  RefreshCw,
} from "lucide-react";
import { API_BASE } from "./api_config";

const CRYPTO_ALIASES = {
  BITCOIN: "BTC-USD",
  BTC: "BTC-USD",
  ETHEREUM: "ETH-USD",
  ETH: "ETH-USD",
  SOLANA: "SOL-USD",
  SOL: "SOL-USD",
};

const BROAD_MARKET_PATTERN = /\b(market pulse|market today|today'?s market|global market|overall market|macro|top opportunities|top stocks|top crypto|gainers|losers|breakout candidates|what is moving the market)\b/i;
const CONTEXTUAL_ASSET_PATTERN = /\b(this stock|this crypto|this asset|selected stock|selected asset|current stock|current asset|should i buy it|should i sell it)\b/i;

function LazyFallback() {
  return (
    <div className="h-full flex flex-col items-center justify-center gap-4 bg-[var(--app-bg)] w-full animate-fade-in">
      <Loader2 size={24} className="text-[var(--accent)] animate-spin" />
      <span className="text-[12px] font-medium text-[var(--text-muted)]">Loading market tools…</span>
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
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-[var(--app-bg)] text-white flex items-center justify-center p-6">
          <div className="surface-card max-w-md w-full p-8 text-center">
            <Shield size={28} className="mx-auto text-[var(--accent)] mb-4" />
            <h1 className="heading-2">This screen needs a refresh</h1>
            <p className="text-[13px] text-[var(--text-muted)] mt-3 leading-relaxed">
              Your market data is safe. Refresh the app to reconnect this view.
            </p>
            <button
              onClick={() => window.location.reload()}
              className="btn-primary mt-6 mx-auto"
            >
              <RefreshCw size={14} /> Refresh app
            </button>
          </div>
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
  const [selectedTicker, setSelectedTicker] = useState(null);
  const [intelligenceStatus, setIntelligenceStatus] = useState(null);
  const [globalTime, setGlobalTime] = useState(new Date().toLocaleTimeString());

  useEffect(() => {
    const fetchSys = async () => {
      try {
        const [agentsResponse, watchlistResponse, globeResponse, intelligenceResponse] = await Promise.all([
          fetch(`${API_BASE}/api/agents/status`),
          fetch(`${API_BASE}/api/market/watchlist`),
          fetch(`${API_BASE}/api/market/globe-data`),
          fetch(`${API_BASE}/api/intelligence/status`),
        ]);

        if (agentsResponse.ok) {
          const sysAgents = await agentsResponse.json();
          const agentsArray = Array.isArray(sysAgents)
            ? sysAgents
            : sysAgents.agents || sysAgents.data || [];
          setAgentsStatus(agentsArray);
        }

        let hasWatchlistPayload = false;
        if (watchlistResponse.ok) {
          const sysData = await watchlistResponse.json();
          const stocksArray = Array.isArray(sysData)
            ? sysData
            : sysData.stocks || sysData.data || [];
          if (stocksArray.length > 0) {
            hasWatchlistPayload = true;
            setLiveStocks(stocksArray);
            setSelectedTicker((previous) => {
              if (previous) return previous;
              const first = stocksArray[0].id || stocksArray[0].ticker;
              return first ? String(first).toUpperCase() : null;
            });
          }
        }

        if (!hasWatchlistPayload && globeResponse.ok) {
          const globeData = await globeResponse.json();
          const globeStocks = Array.isArray(globeData)
            ? globeData
            : globeData.value || globeData.data || [];
          setLiveStocks(globeStocks);
        }

        if (intelligenceResponse.ok) {
          setIntelligenceStatus(await intelligenceResponse.json());
        }
      } catch (error) {
        console.error("Live data fetch failed:", error);
      }
    };

    fetchSys();
    const statusTimer = setInterval(fetchSys, 15000);
    const timeTimer = setInterval(
      () => setGlobalTime(new Date().toLocaleTimeString()),
      1000
    );
    return () => {
      clearInterval(statusTimer);
      clearInterval(timeTimer);
    };
  }, []);

  const handleStockSelect = (ticker) => {
    if (!ticker) {
      if (liveStocks[0]) {
        const fallback = liveStocks[0].id || liveStocks[0].ticker;
        if (fallback) {
          setSelectedTicker(String(fallback).toUpperCase());
          setActiveView("Stock Terminal");
        }
      }
      return;
    }
    setSelectedTicker(String(ticker).toUpperCase());
    setActiveView("Stock Terminal");
  };

  const findExplicitTicker = (text) => {
    const upper = String(text || "").toUpperCase();
    const cashtag = upper.match(/\$([A-Z]{1,10}(?:\.[A-Z]{1,3})?)/);
    if (cashtag) return cashtag[1];

    for (const [alias, ticker] of Object.entries(CRYPTO_ALIASES)) {
      if (new RegExp(`\\b${alias}\\b`, "i").test(upper)) return ticker;
    }

    const known = liveStocks
      .map((stock) => String(stock.id || stock.ticker || "").toUpperCase())
      .filter(Boolean)
      .sort((a, b) => b.length - a.length);
    return known.find((ticker) => {
      const escaped = ticker.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      return new RegExp(`(^|[^A-Z0-9.])${escaped}([^A-Z0-9.]|$)`, "i").test(upper);
    }) || "";
  };

  const resolveChatTicker = (text, requestedTicker = null) => {
    const explicit = findExplicitTicker(text);
    if (explicit) return explicit;
    if (BROAD_MARKET_PATTERN.test(text)) return "";
    if (requestedTicker) return String(requestedTicker).toUpperCase();
    if (selectedTicker && (activeView === "Stock Terminal" || CONTEXTUAL_ASSET_PATTERN.test(text))) {
      return selectedTicker;
    }
    return "";
  };

  const chooseResearchMode = (text) =>
    /\b(deep|detailed|compare|comparison|full analysis|why exactly|bull.*bear|risk analysis)\b/i.test(text)
      ? "DEEP"
      : "QUICK";

  const handleChat = async (text, ticker = null) => {
    const cleanText = String(text || "").trim();
    if (!cleanText) return;

    const contextTicker = resolveChatTicker(cleanText, ticker);
    const researchMode = chooseResearchMode(cleanText);
    const history = chatMessages.slice(-8).map((message) => ({
      role: message.role === "ai" ? "assistant" : "user",
      content: message.text,
    }));

    setChatMessages((previous) => [...previous, { role: "user", text: cleanText }]);
    setIsChatOpen(true);

    try {
      const response = await fetch(`${API_BASE}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: cleanText,
          ticker: contextTicker,
          research_mode: researchMode,
          history,
        }),
      });

      if (!response.ok) {
        throw new Error(`Market assistant returned ${response.status}`);
      }

      const data = await response.json();
      const answer = data.response || data.output;
      if (!answer) throw new Error("No answer was returned");

      setChatMessages((previous) => [
        ...previous,
        {
          role: "ai",
          text: answer,
          sources: Array.isArray(data.sources_used) ? data.sources_used : [],
          priceData: data.price_data || null,
          meta: {
            confidence: data.confidence,
            pipelineMs: data.pipeline_ms,
            source: data.source,
            contextTicker: data.ticker || contextTicker || null,
            researchMode: data.research_mode || researchMode,
          },
        },
      ]);
    } catch (error) {
      setChatMessages((previous) => [
        ...previous,
        {
          role: "ai",
          text:
            "I couldn’t complete that market check right now. Your question is still here—please retry after the data connection recovers.",
          meta: {
            error: "Market data or AI service temporarily unavailable",
            contextTicker: contextTicker || null,
          },
        },
      ]);
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
        { id: "Network Pulse", icon: Activity, count: "LIVE" },
      ]
    }
  ];

  const marketIntelligenceOnline = Boolean(intelligenceStatus);

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

        {/* Intelligence Pulse Footer */}
        <div className="mt-auto p-4 border-t border-[var(--border-color)] space-y-3">
           <div className="flex flex-col gap-1 px-1">
              <div className="flex justify-between text-[9px] font-bold uppercase text-[var(--text-muted)] tracking-widest">
                 <span>Inference Load</span>
                 <span className="text-white">{(intelligenceStatus?.agents || 27) * 4}%</span>
              </div>
              <div className="h-1 w-full bg-[#0c0e12] rounded-full overflow-hidden">
                 <div className="h-full bg-[var(--accent)] w-[65%] animate-pulse" />
              </div>
           </div>
           
           <div className="flex items-center gap-3 px-2 py-2 rounded-[var(--radius-md)] hover:bg-[#1e232b] cursor-pointer transition border border-transparent hover:border-[var(--border-color)]">
              <div className="h-8 w-8 rounded-full bg-[var(--accent)] flex items-center justify-center text-white bg-opacity-20 border border-[var(--accent)] font-semibold text-[11px]">
                 AIT
              </div>
              <div className="min-w-0">
                 <p className="text-[13px] font-medium text-white truncate">Operator</p>
                 <p className="text-[10px] text-[var(--text-muted)] font-mono tracking-wider">NETWORK V4.0</p>
              </div>
           </div>
        </div>
      </aside>

      {/* ── MAIN CONTENT AREA ── */}
      <main className="flex-1 flex flex-col min-w-0 relative">
        <header className="h-16 flex-shrink-0 flex items-center justify-between px-6 border-b border-[var(--border-color)] bg-[var(--app-bg)] z-10">
          <div className="flex items-center gap-4 hidden sm:flex">
            <h2 className="heading-2">{activeView}</h2>
            <div className="h-4 w-px bg-[var(--border-color)]" />
            <div className="flex items-center gap-2">
              <div
                className={`h-2 w-2 rounded-full ${
                  marketIntelligenceOnline ? "bg-[var(--positive)]" : "bg-amber-400"
                }`}
              />
              <span className="text-[11px] font-medium text-[var(--text-muted)] uppercase tracking-wider">
                {marketIntelligenceOnline ? "Market intelligence online" : "Connecting market intelligence"}
              </span>
            </div>
          </div>

          <div className="flex sm:hidden items-center gap-2">
            <h2 className="heading-3">{activeView}</h2>
          </div>

          <div className="flex items-center gap-3 sm:gap-4 ml-auto flex-1 justify-center max-w-xl">
            <AskBar onAsk={(text) => handleChat(text)} />
          </div>

          <div className="flex items-center gap-3 sm:gap-4 ml-auto">
            <div className="hidden lg:flex items-center gap-2 text-[var(--text-muted)]">
              <Clock size={14} />
              <span className="text-[12px] font-mono">{globalTime}</span>
            </div>
            <div className="hidden sm:block h-4 w-px bg-[var(--border-color)]" />
            <button
              className="h-8 w-8 flex items-center justify-center rounded-[var(--radius-md)] text-[var(--text-muted)] hover:bg-[#1e232b] hover:text-white transition"
              aria-label="Notifications"
            >
              <Bell size={16} />
            </button>
            <button
              onClick={() => setIsChatOpen(!isChatOpen)}
              className={`btn-standard h-8 px-3 ${
                isChatOpen ? "bg-[#1e232b] text-white border-slate-600" : ""
              }`}
            >
              <MessageSquareText size={14} />
              <span className="hidden sm:inline">AI Chat</span>
            </button>
          </div>
        </header>

        <div className="flex-shrink-0 bg-[#0c0e12] border-b border-[var(--border-color)] w-full overflow-hidden">
          <Suspense fallback={null}>
            <LiveTickerBar stocks={liveStocks} onSelect={handleStockSelect} />
          </Suspense>
        </div>

        <section className="flex-1 overflow-hidden relative">
          <div className="absolute inset-0 z-0">
            <Suspense fallback={<LazyFallback />}>
              {activeView === "World Map" && (
                <Globe3D stocks={liveStocks} onStockSelect={handleStockSelect} />
              )}
            </Suspense>
          </div>

          <div
            className={`absolute inset-0 z-10 overflow-y-auto no-scrollbar pointer-events-auto transition-opacity duration-300 ${
              activeView === "World Map"
                ? "pointer-events-none opacity-0"
                : "opacity-100 bg-[var(--app-bg)]"
            }`}
          >
            <Suspense fallback={<LazyFallback />}>
              {activeView === "Predictions" && <PredictionTableView onSelect={handleStockSelect} />}
              {activeView === "Stock Terminal" && <StockDetailView ticker={selectedTicker} />}
              {activeView === "Agent Network" && <AgentMatrixView agents={agentsStatus} />}
              {activeView === "Intelligence" && (
                <TrendingStocksView stocks={liveStocks} onSelect={handleStockSelect} />
              )}
              {activeView === "Intelligence Status" && <IntelligenceStatusView />}
              {activeView === "Risk Dynamics" && <RiskAnalysisView />}
              {activeView === "Mission Control" && (
                <MissionControlDashboard agentsStatus={agentsStatus} />
              )}
              {activeView === "Portfolio" && <PortfolioInsightsView />}
              {activeView === "Paper Trading" && <VirtualPortfolioView />}
              {activeView === "News Evidence" && <NewsEvidenceView />}
              {activeView === "Network Pulse" && <IntelligenceStatusView />}
              {activeView === "AI Expert Chat" && (
                <ChatPanel
                  messages={chatMessages}
                  onSend={(text) => handleChat(text)}
                  fullView={true}
                  intelligenceStatus={intelligenceStatus}
                />
              )}
            </Suspense>
          </div>
        </section>
      </main>

      {isChatOpen && activeView !== "AI Expert Chat" && (
        <>
          <div className="drawer-overlay" onClick={() => setIsChatOpen(false)} />
          <div className="drawer-panel flex flex-col">
            <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--border-color)] bg-[var(--card-bg)]">
              <div className="flex items-center gap-2">
                <div className="h-2 w-2 rounded-full bg-[var(--accent)]" />
                <h3 className="heading-3">AITradra Assistant</h3>
              </div>
              <button
                onClick={() => setIsChatOpen(false)}
                className="text-[var(--text-muted)] hover:text-white transition"
                aria-label="Close chat"
              >
                <X size={18} />
              </button>
            </div>
            <div className="flex-1 overflow-hidden">
              <Suspense fallback={<LazyFallback />}>
                <ChatPanel
                  messages={chatMessages}
                  onSend={(text) => handleChat(text)}
                  intelligenceStatus={intelligenceStatus}
                />
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
