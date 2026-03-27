import React, { useState, useRef, useEffect } from "react";
import { Zap, Cpu, Sparkles, Loader2, Send } from "lucide-react";

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
    onSend(q, null);
    try {
      const res = await fetch(`${API_BASE}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: q, ticker: stock?.id || '' }),
      });
      const data = await res.json();
      onSend(null, data.response);
    } catch (err) {
      onSend(null, 'Neural link interrupted. Reconnecting...');
    }
    setLoading(false);
  };

  // Render clean text with emoji section headers highlighted
  const renderCleanText = (text) => {
    const lines = text.split('\n');
    return lines.map((line, i) => {
      const trimmed = line.trim();
      if (!trimmed) return <div key={i} className="h-2" />;
      
      // Main title (🧠 OMNI-DATA)
      if (trimmed.startsWith('🧠')) {
        return <div key={i} className="text-[13px] font-black text-transparent bg-clip-text bg-gradient-to-r from-indigo-300 to-cyan-300 tracking-wide uppercase pb-1 border-b border-white/10 mb-1">{trimmed}</div>;
      }
      // Section headers (📊 📈 ⚠️ 🎯 📌)
      if (/^[📊📈⚠️🎯📌🔄💰🚀]/.test(trimmed)) {
        return <div key={i} className="text-[11px] font-bold text-cyan-400 tracking-wide mt-2 mb-0.5">{trimmed}</div>;
      }
      // Country flag + stock picks
      if (/^[🇺🇸🇮🇳🇬🇧🇯🇵🇩🇪🇫🇷🇨🇳🇰🇷🇧🇷🇭🇰🇸🇬🇦🇺]/.test(trimmed)) {
        return <div key={i} className="text-[11px] font-bold text-white mt-1.5">{trimmed}</div>;
      }
      // Sector/Strength/Outlook labels
      if (/^(Sector:|Strength:|Outlook:)/i.test(trimmed)) {
        const [label, ...rest] = trimmed.split(':');
        return (
          <div key={i} className="text-[10px] pl-3 leading-snug">
            <span className="text-indigo-400/70 font-bold">{label}:</span>
            <span className="text-slate-400"> {rest.join(':')}</span>
          </div>
        );
      }
      // Confidence line
      if (/^(👉|Confidence:)/i.test(trimmed)) {
        return <div key={i} className="text-[11px] font-bold text-emerald-400 mt-1 pt-1 border-t border-white/5">{trimmed}</div>;
      }
      // Bullet points
      if (trimmed.startsWith('•') || trimmed.startsWith('-')) {
        return <div key={i} className="text-[10px] text-slate-400 pl-2 leading-snug">{trimmed}</div>;
      }
      // Normal text
      return <div key={i} className="text-[11px] text-slate-300 leading-relaxed">{trimmed}</div>;
    });
  };

  return (
    <div className="flex-1 flex flex-col relative overflow-hidden" style={{ 
      background: 'linear-gradient(180deg, rgba(8,11,20,0.95) 0%, rgba(5,7,15,0.98) 100%)', 
      borderLeft: '1px solid rgba(99,102,241,0.1)',
    }}>

      {/* Compact Header */}
      <div className="h-10 border-b border-white/5 flex items-center justify-between px-3 bg-black/30 shrink-0">
        <div className="flex items-center gap-2">
          <div className="w-5 h-5 rounded-md bg-indigo-500/15 border border-indigo-400/20 flex items-center justify-center">
            <Sparkles size={10} className="text-indigo-400" />
          </div>
          <span className="text-[10px] font-bold text-white/80 tracking-widest uppercase">Omni-Data</span>
          <span className="text-[8px] text-cyan-400/60 font-mono">LIVE</span>
        </div>
        <div className="w-1.5 h-1.5 rounded-full bg-green-500 shadow-[0_0_6px_#22c55e]" />
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-3 py-2 space-y-2 flex flex-col no-scrollbar relative">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center gap-3 opacity-40">
            <Cpu size={32} className="text-indigo-400" />
            <div className="text-center">
              <p className="text-xs font-bold text-white/60 tracking-wider uppercase">Neural Matrix Ready</p>
              <p className="text-[8px] font-mono text-indigo-300/40 tracking-widest mt-1">AWAITING DIRECTIVES</p>
            </div>
          </div>
        ) : (
          messages.map((m, i) => (
            <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[92%] relative ${
                m.role === 'user' 
                  ? 'rounded-lg rounded-tr-sm bg-indigo-600/80 text-white px-3 py-2' 
                  : 'rounded-lg rounded-tl-sm bg-white/[0.03] border border-white/5 text-slate-300 px-3 py-2.5'
              }`}>
                {/* Tag */}
                <div className={`text-[7px] font-mono font-bold tracking-widest uppercase mb-1 ${m.role === 'user' ? 'text-indigo-200/50' : 'text-indigo-400/50'}`}>
                  {m.role === 'user' ? 'YOU' : 'OMNI-DATA'}
                </div>

                {/* Render clean text with section formatting */}
                {m.role === 'ai' ? (
                  <div>{renderCleanText(m.text)}</div>
                ) : (
                  <div className="text-[11px] leading-relaxed whitespace-pre-wrap">{m.text}</div>
                )}

                {/* Telemetry Footer */}
                {m.role === 'ai' && (
                  <div className="mt-1.5 pt-1 border-t border-white/[0.03] flex items-center justify-between">
                    <div className="flex items-center gap-1">
                      <Zap size={8} className="text-cyan-400/50" />
                      <span className="text-[7px] font-mono text-slate-600 tracking-widest uppercase">Synthesized Output</span>
                    </div>
                    <span className="text-[8px] font-mono font-bold text-cyan-400/50">OMNI-DATA v3.1</span>
                  </div>
                )}
              </div>
            </div>
          ))
        )}
        {loading && (
          <div className="flex items-start pl-1">
            <div className="bg-indigo-500/5 border border-indigo-500/15 rounded-lg px-3 py-2 flex gap-2 items-center">
              <Loader2 size={10} className="text-cyan-400 animate-spin" />
              <span className="text-[9px] font-mono text-indigo-300/60 font-bold tracking-widest uppercase">Synthesizing...</span>
            </div>
          </div>
        )}
        <div ref={endRef} className="h-1" />
      </div>

      {/* Compact Input */}
      <div className="px-3 py-2 bg-black/50 border-t border-white/5 shrink-0">
        <form onSubmit={(e) => { e.preventDefault(); handleSend(); }} className="flex items-center gap-2 p-1.5 pl-3 bg-white/[0.03] border border-white/5 rounded-xl">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask Omni-Data..."
            className="flex-1 bg-transparent border-none outline-none text-white text-[11px] placeholder:text-slate-600"
            disabled={loading}
            autoFocus
          />
          <button
            type="submit"
            disabled={!input.trim() || loading}
            className="p-2 rounded-lg bg-indigo-600 text-white hover:bg-indigo-500 disabled:opacity-20 transition-colors"
          >
            {loading ? (
              <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : (
              <Send size={12} />
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
