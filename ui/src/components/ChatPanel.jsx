import React, { useState, useRef, useEffect } from "react";
import { ChevronRight, Zap } from "lucide-react";
import { T } from "../theme";

export default function ChatPanel({ messages, onSend, stock }) {
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const endRef = useRef(null);
  useEffect(() => { endRef.current?.scrollIntoView({ behavior:'smooth' }); }, [messages]);

  const handleSend = async (msg = input) => {
    const q = msg.trim();
    if (!q) return;
    setInput('');
    onSend(q, null);
    setLoading(true);
    setTimeout(() => {
      let rep = "Analysis complete. The requested data has been integrated into the current working memory context.";
      if(q.toLowerCase().includes('risk')) rep = "Portfolio VaR remains elevated. Consider hedging high-beta tech exposure given the recent macro shifts.";
      if(q.toLowerCase().includes('nvda') || q.toLowerCase().includes('nvidia')) rep = "NVDA analysis: Blackwell GPU demand exceeds supply. Datacenter AI capex cycle shows strong momentum. LSTM+XGBoost ensemble signals STRONG BUY with 82% confidence. Key risk: valuation premium at 62x PE.";
      if(q.toLowerCase().includes('health') || q.toLowerCase().includes('agent')) rep = "Agent Matrix Status:\n• DataAgent: Active (99.9% acc)\n• NewsAgent: Learning (84.2% acc)\n• TrendAgent: Active (78.5% acc)\n• RiskAgent: Active (92.1% acc)\n• MLAgent: Retraining (68.4% acc) ⚠️\n• SynthesisAgent: Active (88.8% acc)\n\nSelf-improvement engine is optimizing MLAgent prompts.";
      if(q.toLowerCase().includes('scan') || q.toLowerCase().includes('market')) rep = "Global Market Scan:\n▲ NVDA +4.8% — AI chip demand surge\n▲ AAPL +2.3% — Services growth\n▲ SAP +1.2% — Enterprise cloud\n▲ BABA +1.4% — Recovery momentum\n▼ TSLA -1.8% — Delivery concerns\n▼ BHP -0.5% — Commodity pressure";
      onSend(null, rep);
      setLoading(false);
    }, 1200);
  };

  const chips = ['Analyze NVDA','Agent Health','Market Scan'];

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-black/60 backdrop-blur-xl border-l border-white/10 shadow-[-20px_0_50px_rgba(0,0,0,0.5)]">
      <div className="px-4 py-3 flex items-center gap-2 flex-shrink-0 border-b border-white/5 bg-white/[0.02]">
        <Zap size={14} style={{ color: T.warn, filter:`drop-shadow(0 0 5px ${T.warn})` }} />
        <span className="text-[10px] font-bold uppercase tracking-widest text-slate-300">Axiom OS Copilot</span>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4" style={{ minHeight: 0 }}>
        {messages.map((m, i) => (
          <div key={i} className={`flex flex-col ${m.role === 'user' ? 'items-end' : 'items-start'}`}>
            {m.tag && <span className="text-[9px] font-mono mb-1 ml-1 tracking-wider" style={{ color: T.aiLight }}>{m.tag}</span>}
            <div className="text-xs px-4 py-2.5 max-w-[90%] leading-relaxed rounded-2xl shadow-lg backdrop-blur-md whitespace-pre-wrap"
              style={m.role === 'user'
                ? { background:`${T.ai}20`, border:`1px solid ${T.ai}40`, color: T.text, borderBottomRightRadius:4 }
                : { background: 'rgba(255,255,255,0.05)', border:`1px solid rgba(255,255,255,0.1)`, color: T.text, borderBottomLeftRadius:4 }}>
              {m.text}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex items-start">
            <div className="px-4 py-2.5 rounded-2xl text-xs flex gap-1.5 items-center border border-white/10 bg-white/5">
              <div className="w-1.5 h-1.5 rounded-full animate-bounce bg-slate-400"></div>
              <div className="w-1.5 h-1.5 rounded-full animate-bounce bg-slate-400" style={{animationDelay:'0.15s'}}></div>
              <div className="w-1.5 h-1.5 rounded-full animate-bounce bg-slate-400" style={{animationDelay:'0.3s'}}></div>
            </div>
          </div>
        )}
        <div ref={endRef}/>
      </div>

      <div className="p-4 border-t border-white/10 bg-black/40">
        <div className="flex gap-2 overflow-x-auto mb-3 pb-1 no-scrollbar">
          {chips.map(c => (
            <button key={c} onClick={() => handleSend(c)}
              className="whitespace-nowrap px-3 py-1.5 rounded-full text-[10px] font-bold transition-all bg-white/5 border border-white/10 text-slate-400 hover:text-white hover:border-indigo-500 hover:shadow-[0_0_10px_rgba(99,102,241,0.3)]">
              {c}
            </button>
          ))}
        </div>
        <div className="relative flex items-center">
          <input value={input} onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key==='Enter' && handleSend()}
            placeholder="Command Axiom..."
            className="w-full text-xs px-4 py-3 rounded-xl outline-none transition-all bg-black/50 border border-white/10 text-white focus:border-indigo-500 focus:shadow-[0_0_15px_rgba(99,102,241,0.3)] placeholder:text-slate-600" />
          <button onClick={() => handleSend()} className="absolute right-2 p-2 rounded-lg transition-all text-indigo-400 hover:bg-indigo-500/20 hover:text-white">
            <ChevronRight size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}
