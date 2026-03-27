import React, { useState, useRef, useEffect } from "react";
import { ChevronRight, Zap, Terminal, Cpu, Sparkles, Loader2 } from "lucide-react";
import { T } from "../theme";

const API_BASE = "http://localhost:8000";

export default function ChatPanel({ messages, onSend, stock }) {
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const endRef = useRef(null);
  useEffect(() => { endRef.current?.scrollIntoView({ behavior:'smooth' }); }, [messages]);

  const handleSend = async (msg = input) => {
    const q = msg.trim();
    if (!q) return;
    setInput('');
    setLoading(true);

    // Send user message immediately, then call LLM
    onSend(q, null);

    try {
      const res = await fetch(`${API_BASE}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: q,
          ticker: stock?.id || '',
        }),
      });
      const data = await res.json();
      onSend(null, data.response);
    } catch (err) {
      onSend(null, 'Neural link interrupted. LLM service unavailable — falling back to rule-based analysis engine.');
    }
    setLoading(false);
  };

  const chips = [
    { label: `Analyze ${stock?.id || 'NVDA'}`, icon: Sparkles },
    { label: 'Agent Health', icon: Cpu },
    { label: 'Market Scan', icon: Terminal },
  ];

  return (
    <div className="flex-1 flex flex-col overflow-hidden" style={{ 
      borderLeft: '1px solid rgba(255,255,255,0.04)',
      background: 'rgba(10, 14, 26, 0.60)',
      backdropFilter: 'blur(20px)',
    }}>
      {/* Header */}
      <div className="px-4 py-3 flex items-center justify-between flex-shrink-0 border-b border-white/5 bg-gradient-to-b from-white/[0.03] to-transparent">
        <div className="flex items-center gap-2.5">
          <div className="p-1.5 rounded-lg" style={{
            background: `linear-gradient(135deg, ${T.warn}15, ${T.warn}08)`,
            border: '1px solid rgba(251, 191, 36, 0.15)',
          }}>
            <Zap size={12} style={{ color: T.warn, filter:`drop-shadow(0 0 4px ${T.warn}50)` }} />
          </div>
          <div>
            <span className="text-[10px] font-black uppercase tracking-[0.15em] text-white block">Axiom OS Copilot</span>
            <span className="text-[8px] font-mono text-slate-500 tracking-wider">AXIOM_V2 // LLM_POWERED</span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" style={{ boxShadow: '0 0 6px rgba(52, 211, 153, 0.5)' }} />
          <span className="text-[8px] font-black text-emerald-400 uppercase tracking-widest">ONLINE</span>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 no-scrollbar" style={{ minHeight: 0 }}>
        {messages.map((m, i) => (
          <div key={i} className={`flex flex-col ${m.role === 'user' ? 'items-end' : 'items-start'} animate-fade-in`}>
            {m.tag && (
              <div className="flex items-center gap-1.5 mb-1.5 ml-1">
                <div className="w-1 h-1 rounded-full bg-indigo-500 animate-pulse" />
                <span className="text-[8px] font-mono font-black tracking-[0.15em] text-indigo-400 uppercase">{m.tag}</span>
              </div>
            )}
            <div className={`max-w-[90%] text-[11px] leading-relaxed whitespace-pre-wrap rounded-2xl px-4 py-3 ${
              m.role === 'user'
                ? 'bg-indigo-600/20 border border-indigo-500/20 text-slate-200 rounded-br-md'
                : 'bg-black/30 border border-white/5 text-slate-300 rounded-bl-md'
            }`}>
              {m.text}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex items-start">
            <div className="bg-black/30 border border-white/5 rounded-2xl rounded-bl-md px-4 py-3 flex gap-2 items-center">
              <Loader2 size={12} className="text-indigo-400 animate-spin" />
              <span className="text-[9px] font-mono text-slate-500 animate-pulse">LLM reasoning...</span>
            </div>
          </div>
        )}
        <div ref={endRef}/>
      </div>

      {/* Input Area */}
      <div className="p-3 border-t border-white/5 bg-black/20">
        <div className="flex gap-2 overflow-x-auto mb-3 pb-1 no-scrollbar">
          {chips.map(c => {
            const Icon = c.icon;
            return (
              <button key={c.label} onClick={() => handleSend(c.label)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-[9px] font-black uppercase tracking-wider text-slate-400 border border-white/5 hover:border-indigo-500/30 hover:text-indigo-300 hover:bg-indigo-500/5 transition-all whitespace-nowrap">
                <Icon size={10} />
                {c.label}
              </button>
            );
          })}
        </div>
        <div className="relative flex items-center">
          <div className="absolute left-3 top-1/2 -translate-y-1/2">
            <Terminal size={12} className="text-slate-600" />
          </div>
          <input value={input} onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key==='Enter' && handleSend()}
            placeholder="Command Axiom..."
            className="clay-input pl-9 pr-12 text-xs" />
          <button onClick={() => handleSend()} 
            className="absolute right-2 p-2 rounded-xl transition-all text-indigo-400 hover:text-white hover:bg-indigo-500/10">
            <ChevronRight size={14} />
          </button>
        </div>
      </div>
    </div>
  );
}
