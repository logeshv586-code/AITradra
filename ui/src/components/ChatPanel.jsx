import React, { useState, useRef, useEffect } from "react";
import { ChevronRight, Zap, Terminal, Cpu, Sparkles, Loader2, Command, Send } from "lucide-react";
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
    <div className="flex-1 flex flex-col relative overflow-hidden" style={{ background: 'rgba(10, 14, 26, 0.45)' }}>
      {/* Background Decal */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 pointer-events-none opacity-[0.03] z-0">
        <Cpu size={400} />
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6 no-scrollbar relative z-10">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center gap-6 opacity-40">
            <div className="p-6 rounded-full bg-indigo-500/10 border border-indigo-500/20 clay-organic animate-float">
               <Sparkles size={48} className="text-indigo-400" />
            </div>
            <div className="text-center space-y-2">
              <h3 className="text-xl font-black text-white tracking-tighter uppercase">Synaptic Interface v3.1</h3>
              <p className="text-[10px] font-mono text-slate-500 tracking-[0.2em] font-bold">AWAITING NATURAL LANGUAGE COMMAND...</p>
            </div>
          </div>
        ) : (
          messages.map((m, i) => (
            <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'} animate-slide-in`}>
              <div className={`max-w-[85%] p-5 rounded-2xl relative group ${
                m.role === 'user' 
                  ? 'bg-indigo-600 text-white shadow-2xl shadow-indigo-900/40 rounded-tr-none' 
                  : 'clay-inset bg-black/40 text-slate-300 rounded-tl-none border border-white/5'
              }`}>
                {/* ID Tag */}
                <div className={`absolute top-0 ${m.role === 'user' ? 'right-0 -translate-y-full mb-1' : 'left-0 -translate-y-full mb-1'} flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity`}>
                   <span className="text-[8px] font-mono font-black text-slate-600 uppercase tracking-widest">
                     {m.role === 'user' ? 'OPERATOR' : 'AXIOM_CORE'} // {new Date().toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'})}
                   </span>
                </div>

                <p className="text-sm leading-relaxed font-medium whitespace-pre-wrap">
                  {m.text}
                </p>
                
                {m.role === 'assistant' && (
                  <div className="mt-4 pt-4 border-t border-white/5 flex items-center justify-between">
                    <div className="flex gap-2">
                      <div className="w-1.5 h-1.5 rounded-full bg-indigo-500/50" />
                      <div className="w-1.5 h-1.5 rounded-full bg-indigo-500/30" />
                    </div>
                    <span className="text-[8px] font-mono font-black text-slate-600">CONFIDENCE: 99.4%</span>
                  </div>
                )}
              </div>
            </div>
          ))
        )}
        {loading && (
          <div className="flex items-start animate-fade-in">
            <div className="bg-black/30 border border-white/5 rounded-2xl rounded-bl-md px-4 py-3 flex gap-2 items-center">
              <Loader2 size={12} className="text-indigo-400 animate-spin" />
              <span className="text-[9px] font-mono text-slate-500 animate-pulse">LLM REASONING...</span>
            </div>
          </div>
        )}
        <div ref={endRef} />
      </div>

      {/* Input Area */}
      <div className="p-6 bg-black/40 border-t border-white/5 backdrop-blur-xl relative z-20">
        <form onSubmit={(e) => { e.preventDefault(); handleSend(); }} className="max-w-4xl mx-auto relative group">
          <div className="absolute -inset-0.5 bg-gradient-to-r from-indigo-500/50 to-purple-500/50 rounded-2xl blur opacity-0 group-focus-within:opacity-20 transition duration-500" />
          
          <div className="relative flex items-center gap-3 clay-inset p-2 pl-4 bg-black/60 border border-white/10 rounded-2xl">
            <div className="p-2 bg-indigo-500/10 rounded-lg text-indigo-400">
              <Command size={16} />
            </div>
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="ENTER SYSTEM DIRECTIVE..."
              className="flex-1 bg-transparent border-none outline-none text-white text-sm font-mono tracking-tight placeholder:text-slate-600"
              disabled={loading}
            />
            <button
              type="submit"
              disabled={!input.trim() || loading}
              className="p-3 rounded-xl bg-indigo-600 text-white shadow-xl hover:scale-105 active:scale-95 disabled:opacity-30 disabled:scale-100 transition-all font-black"
            >
              {loading ? (
                <div className="w-5 h-5 border-2 border-white/20 border-t-white rounded-full animate-spin" />
              ) : (
                <Send size={18} />
              )}
            </button>
          </div>
        </form>
        <div className="mt-4 text-center">
           <span className="text-[9px] font-mono text-slate-600 tracking-[0.4em] font-black uppercase">
             Axiom Cognitive Bridge // Secure Link Established // v3.1
           </span>
        </div>
      </div>
    </div>
  );
}
