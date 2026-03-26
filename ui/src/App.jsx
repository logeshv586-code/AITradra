import React, { useState } from "react";
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

export default function App() {
  const [view, setView] = useState('globe');
  const [activeStock, setActiveStock] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisComplete, setAnalysisComplete] = useState(false);
  const [agentLogs, setAgentLogs] = useState([]);
  const [chatMessages, setChatMessages] = useState([
    { role:'ai', tag:'AXIOM OS', text:'System online. Cognitive engines fully spooled. Select a global node or input a command.' }
  ]);

  const handleSendChat = (userText, aiText) => {
    if (userText) setChatMessages(p => [...p, { role:'user', text:userText }]);
    if (aiText)   setChatMessages(p => [...p, { role:'ai',  tag:'AXIOM', text:aiText }]);
  };

  const handleSelect = (stock) => {
    setActiveStock(stock);
    setView('stock');
    runAnalysis(stock);
  };

  const runAnalysis = async (stock) => {
    setIsAnalyzing(true);
    setAnalysisComplete(false);
    setAgentLogs([]);
    const delay = ms => new Promise(r => setTimeout(r, ms));
    const log = (agent, action, text) =>
      setAgentLogs(p => [...p, { id: Date.now()+Math.random(), agent, action, text }]);

    log('data','OBSERVE',`Fetching 60-day OHLCV for ${stock.id}. Price: $${stock.px}`);
    await delay(700);
    log('data','ACT',`Loaded fundamentals. MktCap: ${stock.mcap}. Sector: ${stock.sector}.`);
    log('news','THINK',`Scanning 12 financial sources for ${stock.id} catalysts...`);
    await delay(900);
    log('news','REFLECT',`Sentiment: ${stock.chg>=0?'Bullish (0.78)':'Bearish (-0.64)'}. Institutional signal detected.`);
    log('trend','PLAN',`Computing RSI, MACD, Bollinger Bands, ATR...`);
    await delay(800);
    log('trend','ACT',`RSI: ${stock.chg>=0?68:34}. MACD: ${stock.chg>=0?'Golden cross':'Death cross'} forming.`);
    log('risk','OBSERVE',`Calculating VaR at 95% confidence. Beta vs S&P500...`);
    await delay(600);
    log('risk','ACT',`VaR=${stock.risk.var} | Beta=${stock.risk.beta} | Volatility=${stock.risk.vol}`);
    log('ml','PLAN',`LSTM (128-unit) + XGBoost (200-tree) ensemble. Feature dim: 42.`);
    await delay(1200);
    log('ml','REFLECT',`Ensemble confidence: ${Math.floor(75+Math.random()*18)}%. Prediction: ${stock.chg>=0?'UP':'DOWN'}.`);
    log('synthesis','THINK',`Running Chain-of-Thought synthesis across all agent outputs...`);
    await delay(1300);
    log('synthesis','ACT',`Final signal: ${stock.chg>=0?'STRONG BUY':'SELL'}. Self-critique passed 4/4 checks.`);

    setIsAnalyzing(false);
    setAnalysisComplete(true);
  };

  const NAV = [
    { id:'globe',       icon: Globe,          label:'Global Map'    },
    { id:'watchlist',   icon: List,           label:'Watchlist'     },
    { id:'agents',      icon: Layers,         label:'Agent Matrix'  },
  ];

  const showSidebar = view === 'stock' || agentLogs.length > 0;

  return (
    <div className="relative flex flex-col h-screen overflow-hidden text-slate-200 font-sans selection:bg-indigo-500/30">
      {/* ── AMBIENT NEON BACKGROUND ── */}
      <div className="fixed inset-0 pointer-events-none z-[-1]">
        <div className="absolute inset-0 bg-[#02040a]" />
        <div className="absolute top-[-20%] left-[-10%] w-[60vw] h-[60vw] rounded-full bg-indigo-600/10 blur-[120px] mix-blend-screen" />
        <div className="absolute bottom-[-20%] right-[-10%] w-[50vw] h-[50vw] rounded-full bg-cyan-600/10 blur-[120px] mix-blend-screen" />
        <div className="absolute inset-0 opacity-[0.15]" style={{ backgroundImage: `url("data:image/svg+xml,%3Csvg width='40' height='40' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M0 40h40V0H0zm39 3v38H1V1h38z' fill='%23ffffff' fill-opacity='0.1' fill-rule='evenodd'/%3E%3C/svg%3E")`, maskImage: 'linear-gradient(to bottom, white 10%, transparent 90%)' }} />
      </div>

      {/* ── TOP BAR ── */}
      <header className="h-14 flex items-center justify-between px-6 flex-shrink-0 z-50 bg-black/40 backdrop-blur-xl border-b border-white/10 shadow-lg">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-3 cursor-pointer group" onClick={() => setView('globe')}>
            <div className="w-8 h-8 rounded-xl flex items-center justify-center bg-indigo-500/20 border border-indigo-500/40 group-hover:shadow-[0_0_15px_rgba(99,102,241,0.4)] transition-all">
              <Activity size={16} className="text-indigo-400" />
            </div>
            <span className="font-bold tracking-[0.2em] text-sm text-white font-mono text-shadow-glow">
              AXIOM<span className="text-indigo-400">.AI</span>
            </span>
          </div>
          <div className="h-5 w-px bg-white/10 mx-2" />
          <span className="text-[10px] px-2.5 py-1 rounded-md bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 font-bold tracking-widest flex items-center gap-1.5 shadow-[0_0_10px_rgba(0,240,255,0.2)]">
            <div className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" /> CLAUDE_FLOW
          </span>
        </div>
      </header>

      {/* ── TICKER STRIP ── */}
      <LiveTickerBar />

      {/* ── BODY ── */}
      <div className="flex-1 flex overflow-hidden">
        {/* LEFT SIDEBAR */}
        <nav className="w-16 flex-shrink-0 flex flex-col items-center pt-6 gap-3 bg-black/40 backdrop-blur-xl border-r border-white/10 z-40 shadow-xl">
          {NAV.map(n => {
            const Icon = n.icon;
            const active = view === n.id || (view === 'stock' && n.id === 'watchlist');
            return (
              <button key={n.id} title={n.label} onClick={() => setView(n.id)}
                className="w-10 h-10 rounded-xl flex items-center justify-center transition-all group relative"
                style={{
                  background: active ? 'rgba(99,102,241,0.2)' : 'transparent',
                  color: active ? T.aiLight : T.muted,
                  border: `1px solid ${active ? 'rgba(99,102,241,0.4)' : 'transparent'}`,
                  boxShadow: active ? '0 0 15px rgba(99,102,241,0.3)' : 'none'
                }}>
                <Icon size={18} className="group-hover:text-indigo-400 transition-colors" />
              </button>
            );
          })}
          <div className="flex-1"/>
          <button className="w-10 h-10 rounded-xl flex items-center justify-center mb-6 text-slate-500 hover:text-white transition-colors" title="Settings">
            <Settings size={18} />
          </button>
        </nav>

        {/* MAIN CONTENT */}
        <main className="flex-1 flex overflow-hidden relative z-10">
          <div className="flex-1 flex flex-col overflow-hidden">
            {view === 'globe'     && <GlobeView onSelect={handleSelect} />}
            {view === 'watchlist' && <WatchlistView onSelect={handleSelect} />}
            {view === 'agents'    && <AgentMatrixView />}
            {view === 'stock' && activeStock && (
              <StockDetailView stock={activeStock} isAnalyzing={isAnalyzing} analysisComplete={analysisComplete} agentLogs={agentLogs} />
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
