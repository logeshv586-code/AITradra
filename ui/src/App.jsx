import React, { useState, useEffect, useRef } from "react";
import LiveTickerBar from "./components/LiveTickerBar";
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
import MissionControlDashboard from "./components/MissionControlDashboard";
import {
  Activity,
  Globe,
  Layers,
  Settings,
  Rocket,
  TrendingUp,
  BarChart3,
  ShieldAlert,
  Newspaper,
  PieChart,
  MessageSquare,
  User,
  Coins,
  Menu,
  X,
  Layout,
} from "lucide-react";
import { API_BASE } from "./api_config";

const NavButton = ({ item, active, onClick }) => {
  const Icon = item.icon;
  const label = item.shortLabel || item.label;

  return (
    <button
      onClick={onClick}
      title={item.label}
      className={`relative w-full overflow-hidden rounded-[20px] px-1.5 py-2.5 transition-all duration-300 group ${
        active
          ? "border border-indigo-400/25 bg-[linear-gradient(180deg,rgba(99,102,241,0.18),rgba(99,102,241,0.05))] text-white shadow-[0_12px_24px_rgba(0,0,0,0.24),inset_0_1px_0_rgba(255,255,255,0.06)]"
          : "border border-transparent text-slate-500 hover:border-white/[0.08] hover:bg-white/[0.04] hover:text-slate-100"
      }`}
    >
      <div className="absolute inset-x-2.5 top-0 h-px bg-gradient-to-r from-transparent via-white/25 to-transparent opacity-0 transition-opacity duration-300 group-hover:opacity-100" />

      <div className="flex flex-col items-center gap-2">
        <div
          className={`flex h-9 w-9 items-center justify-center rounded-[14px] border transition-all duration-300 ${
            active
              ? "border-indigo-400/30 bg-indigo-500/15 text-indigo-300 shadow-[0_0_20px_rgba(99,102,241,0.2)]"
              : "border-white/[0.08] bg-black/20 group-hover:border-white/[0.18] group-hover:bg-white/[0.08]"
          }`}
        >
          <Icon
            size={16}
            className={`transition-transform duration-300 ${active ? "scale-110" : "group-hover:scale-105"}`}
          />
        </div>

        <div className="flex flex-col items-center gap-0.5">
          <span
            className={`text-[8px] font-black uppercase tracking-[0.16em] transition-all duration-300 ${
              active ? "text-white" : "opacity-70 group-hover:opacity-100"
            }`}
          >
            {label}
          </span>
          <span
            className={`text-[7px] font-mono uppercase tracking-[0.15em] transition-colors duration-300 ${
              active ? "text-indigo-200/70" : "text-slate-600 group-hover:text-slate-400"
            }`}
          >
            {item.kicker}
          </span>
        </div>
      </div>

      {active && (
        <div className="absolute inset-x-4 bottom-1 h-0.5 rounded-full bg-indigo-400 shadow-[0_0_18px_rgba(99,102,241,0.75)]" />
      )}
    </button>
  );
};

export default function App() {
  const [view, setView] = useState("globe");
  const [activeStock, setActiveStock] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisComplete, setAnalysisComplete] = useState(false);
  const [agentLogs, setAgentLogs] = useState([]);
  const [marketIndices, setMarketIndices] = useState([]);
  const [agentsStatus, setAgentsStatus] = useState([]);
  const [liveStocks, setLiveStocks] = useState([]);
  const [stocksLoading, setStocksLoading] = useState(true);

  const [isMobile, setIsMobile] = useState(false);
  const [showAnalytics, setShowAnalytics] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const [chatMessages, setChatMessages] = useState([
    {
      role: "ai",
      tag: "AXIOM MYTHIC",
      text: "System online. Mythic Orchestrator active - 5 specialist agents + critique layer ready. Live market data streaming. Select a node or ask a question.",
    },
  ]);
  const wsRef = useRef(null);

  useEffect(() => {
    const handleResize = () => setIsMobile(window.innerWidth < 1024);
    handleResize();
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [watchlistRes, indicesRes, agentsRes] = await Promise.all([
          fetch(`${API_BASE}/api/market/watchlist`),
          fetch(`${API_BASE}/api/market/indices`),
          fetch(`${API_BASE}/api/agents/status`),
        ]);
        const watchlistData = await watchlistRes.json();
        const indicesData = await indicesRes.json();
        const agentsData = await agentsRes.json();
        if (watchlistData.stocks) setLiveStocks(watchlistData.stocks);
        setMarketIndices(indicesData.indices || []);
        setAgentsStatus(agentsData.agents || []);
        setStocksLoading(false);
      } catch (err) {
        console.error("Live data fetch failed:", err);
        setStocksLoading(false);
      }
    };
    fetchData();
    const interval = setInterval(fetchData, 60000);
    return () => clearInterval(interval);
  }, []);

  const handleSendChat = async (userText, aiText, mythicData = null) => {
    if (userText) {
      setChatMessages((prev) => [...prev, { role: "user", text: userText }]);
      if (!aiText) {
        try {
          const res = await fetch(`${API_BASE}/api/chat`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: userText, ticker: activeStock?.id || "" }),
          });
          const data = await res.json();
          setChatMessages((prev) => [
            ...prev,
            {
              role: "ai",
              tag: "AXIOM MYTHIC",
              text: data.response,
              mythicData: {
                consensus: data.consensus,
                confidence: data.confidence,
                specialist_outputs: data.specialist_outputs,
                critique: data.critique,
                pipeline_ms: data.pipeline_ms,
              },
            },
          ]);
        } catch (err) {
          setChatMessages((prev) => [...prev, { role: "ai", tag: "AXIOM", text: "Neural link interrupted..." }]);
        }
        return;
      }
    }

    if (aiText && aiText !== "auto-analyze") {
      const message = { role: "ai", tag: "AXIOM MYTHIC", text: aiText };
      if (mythicData) message.mythicData = mythicData;
      setChatMessages((prev) => [...prev, message]);
    }
  };

  const handleSelect = (ticker) => {
    const stockId = typeof ticker === "string" ? ticker : ticker.id;
    const found = liveStocks.find((stock) => stock.id === stockId);
    setActiveStock(found || { id: stockId });
  };

  const changeView = (nextView) => {
    setView(nextView);
    if (isMobile) setMobileMenuOpen(false);
  };

  const NAV = [
    { id: "globe", icon: Globe, label: "Map", kicker: "World" },
    { id: "predictions", icon: BarChart3, label: "Predict", kicker: "Signal" },
    { id: "stock_detail", icon: Layout, label: "Terminal", kicker: "Desk" },
    { id: "news", icon: Newspaper, label: "Intelligence", shortLabel: "Intel", kicker: "Flow" },
    { id: "agents", icon: Layers, label: "Synergy", kicker: "Mesh" },
    { id: "risk", icon: ShieldAlert, label: "Risk", kicker: "Guard" },
    { id: "chat", icon: MessageSquare, label: "Expert", kicker: "Chat" },
    { id: "portfolio", icon: PieChart, label: "Assets", kicker: "Book" },
    { id: "trending", icon: TrendingUp, label: "Trending", kicker: "Pulse" },
    { id: "virtual", icon: Coins, label: "Simulator", shortLabel: "Sim", kicker: "Paper" },
    { id: "mission", icon: Rocket, label: "Missions", kicker: "Ops" },
  ];

  const navGroups = [
    { title: "Core", items: NAV.slice(0, 3) },
    { title: "Intelligence", items: NAV.slice(3, 7) },
    { title: "Portfolio", items: NAV.slice(7, 11) },
  ];

  const showSidebar = Boolean(activeStock || agentLogs.length > 0);
  const activeNav = NAV.find((item) => item.id === view) || NAV[0];
  const ActiveNavIcon = activeNav.icon;
  const immersiveView = view === "globe";
  const liveAssetCount = liveStocks.length || marketIndices.length || 0;

  return (
    <div
      ref={wsRef}
      className="relative flex h-screen flex-col overflow-hidden font-sans text-slate-200 institutional-bg selection:bg-indigo-500/30"
    >
      <header className="z-50 flex h-[64px] items-center justify-between border-b border-white/[0.08] bg-[#05070d]/85 px-4 backdrop-blur-2xl md:px-6 lg:px-7">
        <div className="flex items-center gap-3 md:gap-5">
          <button
            className="rounded-2xl border border-white/[0.08] bg-white/[0.03] p-2.5 text-slate-400 transition hover:bg-white/[0.06] hover:text-white lg:hidden"
            onClick={() => setMobileMenuOpen((open) => !open)}
          >
            {mobileMenuOpen ? <X size={18} /> : <Menu size={18} />}
          </button>

          <div className="flex cursor-pointer items-center gap-3 group" onClick={() => changeView("globe")}>
            <div className="flex h-10 w-10 items-center justify-center rounded-2xl border border-indigo-400/20 bg-indigo-500/10 transition-all group-hover:bg-indigo-500/20">
              <Activity size={16} className="text-indigo-400" />
            </div>
            <div className="leading-none">
              <span className="block text-sm font-black tracking-[0.2em] text-white md:text-base">
                AXIOM<span className="text-indigo-400">.AI</span>
              </span>
              <span className="mt-1 block text-[9px] font-mono uppercase tracking-[0.28em] text-slate-500">
                Institutional Workspace
              </span>
            </div>
          </div>

          {!isMobile && (
            <div className="status-badge">
              <div className="h-1.5 w-1.5 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)] animate-pulse" />
              <span>SYNERGY_V4.2</span>
            </div>
          )}

          {!isMobile && (
            <div className="hidden xl:flex items-center gap-3 rounded-[20px] border border-white/[0.08] bg-white/[0.03] px-3.5 py-2.5 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]">
              <div className="flex h-10 w-10 items-center justify-center rounded-2xl border border-white/[0.08] bg-black/20 text-indigo-300">
                <ActiveNavIcon size={16} />
              </div>
              <div className="leading-none">
                <span className="block text-[9px] font-black uppercase tracking-[0.26em] text-slate-500">Workspace</span>
                <span className="mt-1 block text-sm font-semibold text-white">{activeNav.label}</span>
              </div>
            </div>
          )}
        </div>

        <div className="flex items-center gap-3 md:gap-4">
          {!isMobile && (
            <div className="hidden md:flex items-center gap-3 rounded-[20px] border border-white/[0.08] bg-white/[0.03] px-3.5 py-2.5">
              <div className="h-1.5 w-1.5 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.4)]" />
              <span className="text-[9px] font-black uppercase tracking-[0.22em] text-slate-400">
                {stocksLoading ? "Syncing desk" : `${liveAssetCount} live assets`}
              </span>
            </div>
          )}

          <button
            className={`flex items-center gap-2 rounded-[20px] border px-3.5 py-2.5 transition-all ${
              showAnalytics
                ? "border-indigo-500/35 bg-indigo-500/15 text-indigo-300 shadow-[0_0_18px_rgba(99,102,241,0.18)]"
                : "border-white/10 bg-white/[0.03] text-slate-400 hover:border-white/20 hover:bg-white/[0.06] hover:text-white"
            }`}
            onClick={() => setShowAnalytics((open) => !open)}
            title="Toggle Mythic Control"
          >
            <MessageSquare size={16} />
            <span className="hidden text-[10px] font-black uppercase tracking-[0.18em] md:inline">Console</span>
          </button>

          <div className="flex h-10 w-10 items-center justify-center overflow-hidden rounded-full border border-white/10 bg-slate-800/90 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]">
            <User size={14} className="text-slate-400" />
          </div>
        </div>
      </header>

      <LiveTickerBar stocks={liveStocks} />

      <div className="relative flex flex-1 overflow-hidden">
        {isMobile && mobileMenuOpen && (
          <button
            className="absolute inset-0 z-50 bg-black/50 backdrop-blur-sm lg:hidden"
            onClick={() => setMobileMenuOpen(false)}
            aria-label="Close navigation"
          />
        )}

        <nav
          className={`absolute lg:relative z-[60] flex h-full w-[96px] shrink-0 flex-col items-center border-r border-white/[0.08] bg-[#0a0d13]/92 py-3 backdrop-blur-3xl transition-transform duration-300 lg:z-40 lg:bg-[#090d12]/72 ${
            isMobile ? (mobileMenuOpen ? "translate-x-0" : "-translate-x-full") : "translate-x-0"
          }`}
        >
          <div className="w-full px-2">
            <div className="flex h-9 items-center justify-center rounded-[18px] border border-white/[0.08] bg-white/[0.03] shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]">
              <span className="text-[8px] font-black uppercase tracking-[0.28em] text-slate-400">Desk</span>
            </div>
          </div>

          <div className="flex-1 w-full overflow-y-auto px-2 py-3 space-y-3 no-scrollbar">
            {navGroups.map((group) => (
              <div key={group.title} className="nav-cluster">
                <span className="nav-cluster-label">{group.title}</span>
                <div className="space-y-1">
                  {group.items.map((item) => (
                    <NavButton key={item.id} item={item} active={view === item.id} onClick={() => changeView(item.id)} />
                  ))}
                </div>
              </div>
            ))}
          </div>

          <div className="w-full border-t border-white/[0.08] px-2 pt-3">
            <div className="nav-cluster gap-2 py-2">
              <button
                title="Settings"
                className="flex flex-col items-center gap-1.5 rounded-[18px] border border-white/[0.08] bg-white/[0.03] px-1.5 py-2.5 text-slate-500 transition hover:border-white/[0.16] hover:bg-white/[0.06] hover:text-white"
              >
                <div className="flex h-9 w-9 items-center justify-center rounded-[14px] border border-white/[0.08] bg-black/20">
                  <Settings size={16} />
                </div>
                <span className="text-[8px] font-black uppercase tracking-[0.16em]">Config</span>
              </button>
              <div className="flex items-center justify-center rounded-[18px] border border-indigo-500/10 bg-indigo-500/5 px-2 py-2 text-[7px] font-mono uppercase tracking-[0.18em] text-indigo-300/65">
                Stable
              </div>
            </div>
          </div>
        </nav>

        <main
          className={`relative z-10 flex min-w-0 flex-1 flex-col overflow-hidden transition-all duration-300 ${
            immersiveView ? "bg-[#0B0F14]/40" : "workspace-canvas"
          } ${!isMobile && showAnalytics ? "lg:border-r border-white/[0.08]" : ""}`}
        >
          <div className="relative flex flex-1 flex-col overflow-hidden">
            {view === "globe" && <Globe3D onStockSelect={handleSelect} stocks={liveStocks} />}
            {view === "predictions" && <PredictionTableView onSelect={handleSelect} />}
            {view === "stock_detail" &&
              (activeStock ? (
                <StockDetailView
                  stock={activeStock}
                  isAnalyzing={isAnalyzing}
                  analysisComplete={analysisComplete}
                  agentLogs={agentLogs}
                />
              ) : (
                <div className="flex flex-1 items-center justify-center px-6 py-10 animate-fade-in">
                  <div className="surface-card-soft max-w-md p-8 text-center">
                    <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl border border-indigo-400/20 bg-indigo-500/10">
                      <Layout size={22} className="text-indigo-400" />
                    </div>
                    <p className="text-[10px] font-black uppercase tracking-[0.28em] text-slate-500">Terminal standby</p>
                    <p className="mt-3 text-sm leading-relaxed text-slate-400">
                      Select a symbol from the globe, watchlists, or analytics views to open the stock desk.
                    </p>
                  </div>
                </div>
              ))}
            {view === "news" && <NewsEvidenceView />}
            {view === "agents" && <AgentMatrixView agentsStatus={agentsStatus} />}
            {view === "risk" && <RiskAnalysisView onSelect={handleSelect} />}
            {view === "chat" && (
              <div className="flex flex-1 flex-col p-4 md:p-6 xl:p-8 animate-fade-in">
                <ChatPanel messages={chatMessages} onSend={handleSendChat} stock={activeStock} fullView={true} />
              </div>
            )}
            {view === "portfolio" && <PortfolioInsightsView />}
            {view === "trending" && <TrendingStocksView onSelect={handleSelect} />}
            {view === "virtual" && <VirtualPortfolioView onSelect={handleSelect} />}
            {view === "mission" && (
              <div className="flex flex-1 flex-col overflow-hidden animate-fade-in">
                <MissionControlDashboard />
              </div>
            )}

            {activeStock && view !== "stock_detail" && (
              <StockDetailPanel ticker={activeStock} onClose={() => setActiveStock(null)} />
            )}
          </div>
        </main>

        <aside
          className={`absolute right-0 z-50 flex h-full flex-col overflow-hidden border-l border-white/[0.08] bg-[#070a10]/95 backdrop-blur-3xl transition-all duration-300 lg:relative lg:z-20 lg:bg-[#0b0f14]/60 ${
            isMobile ? (showAnalytics ? "translate-x-0 w-full" : "translate-x-full w-0") : showAnalytics ? "w-[400px]" : "w-0 opacity-0"
          }`}
        >
          <div className="flex h-16 items-center justify-between border-b border-white/[0.08] bg-white/[0.02] px-5 shrink-0">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-2xl border border-indigo-400/20 bg-indigo-500/10">
                <MessageSquare size={16} className="text-indigo-400" />
              </div>
              <div className="leading-none">
                <span className="block text-[9px] font-black uppercase tracking-[0.24em] text-slate-500">
                  Analytics Workspace
                </span>
                <span className="mt-1 block text-sm font-semibold text-white">Mythic Console</span>
              </div>
            </div>

            <div className="flex items-center gap-2">
              {!isMobile && (
                <div className="hidden items-center gap-2 rounded-full border border-white/[0.08] bg-white/[0.03] px-2.5 py-1 md:flex">
                  <div className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                  <span className="text-[8px] font-black uppercase tracking-[0.2em] text-slate-400">Desk online</span>
                </div>
              )}
              <button
                className="p-2 text-slate-500 transition hover:text-white lg:hidden"
                onClick={() => setShowAnalytics(false)}
              >
                <X size={18} />
              </button>
            </div>
          </div>

          {showSidebar && (
            <div className="h-[34%] border-b border-white/[0.08] bg-gradient-to-b from-white/[0.03] to-transparent p-3 shrink-0">
              <div className="surface-card h-full bg-black/20">
                <AgentStreamPanel logs={agentLogs} isAnalyzing={isAnalyzing} />
              </div>
            </div>
          )}

          <div className="flex-1 min-h-0 p-3 md:p-4">
            <ChatPanel messages={chatMessages} onSend={handleSendChat} stock={activeStock} />
          </div>
        </aside>
      </div>

      {!showAnalytics && isMobile && (
        <button
          onClick={() => setShowAnalytics(true)}
          className="absolute bottom-6 right-6 z-50 flex h-12 w-12 items-center justify-center rounded-full bg-indigo-600 text-white shadow-2xl lg:hidden"
        >
          <MessageSquare size={20} />
        </button>
      )}
    </div>
  );
}
