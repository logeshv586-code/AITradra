import React, { useState, useEffect, useRef } from 'react';
import { API_BASE } from '../api_config';
import { Send, X, MessageSquare, Sparkles, Terminal, Globe, ChevronRight, Loader2 } from 'lucide-react';

const SUGGESTED_QUESTIONS = {
  stock: [
    "Why did it move today?",
    "Is now a good time to buy?",
    "What is the biggest risk?",
    "Show me 52-week statistics",
    "Sector peer comparison",
  ],
  crypto: [
    "V4 Market sentiment?",
    "Liquidity flow analysis?",
    "Entry point probability?",
  ]
};

export default function StockChat({ ticker, onClose }) {
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [initializing, setInitializing] = useState(true);
  const messagesEndRef = useRef(null);
  const isCrypto = ticker?.includes('-USD');

  useEffect(() => {
    const createSession = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/chat/stock/${ticker}/session`, {
          method: "POST",
        });
        const data = await res.json();
        setSessionId(data.session_id);
        setMessages([{
          role: "assistant",
          content: data.welcome_message || `🧠 AXIOM MYTHIC Intelligence online for **${ticker}**. I have access to multi-specialist analysis, news, and market intelligence. Ask me anything!`,
          timestamp: new Date().toISOString(),
        }]);
      } catch (err) {
        console.error("Failed to create session:", err);
        setMessages([{
          role: "assistant",
          content: `🧠 AXIOM MYTHIC ready for ${ticker}. Ask me anything about this asset — I'll use multi-agent specialists and local AI to synthesize an answer.`,
          timestamp: new Date().toISOString(),
        }]);
      } finally {
        setInitializing(false);
      }
    };
    createSession();
  }, [ticker]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async (text = input) => {
    const msg = text.trim();
    if (!msg || loading) return;

    const userMsg = { role: "user", content: msg, timestamp: new Date().toISOString() };
    setMessages(prev => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const url = sessionId
        ? `${API_BASE}/api/chat/stock/${ticker}/session/${sessionId}`
        : `${API_BASE}/api/chat/stock/${ticker}`;

      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: msg })
      });
      const data = await res.json();

      setMessages(prev => [...prev, {
        role: "assistant",
        content: data.response,
        timestamp: new Date().toISOString(),
        sources: data.sources_used || [],
      }]);
    } catch {
      setMessages(prev => [...prev, {
        role: "assistant",
        content: "⚠️ Node connection failed. Retransmitting packet...",
        timestamp: new Date().toISOString(),
      }]);
    } finally {
      setLoading(false);
    }
  };

  const renderContent = (content) => {
    if (!content) return null;
    const parts = content.split(/(\*\*[^*]+\*\*|https?:\/\/[^\s]+)/g);
    return parts.map((part, i) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        return <strong key={i} className="text-white font-bold">{part.slice(2, -2)}</strong>;
      }
      if (part.match(/^https?:\/\//)) {
        return (
          <a key={i} href={part} target="_blank" rel="noopener noreferrer"
             className="text-indigo-400 hover:text-indigo-300 underline underline-offset-4 decoration-indigo-500/30 transition-all font-bold">
            {part.length > 40 ? 'SOURCE_LINK' : part}
          </a>
        );
      }
      return <span key={i}>{part}</span>;
    });
  };

  const questions = isCrypto ? SUGGESTED_QUESTIONS.crypto : SUGGESTED_QUESTIONS.stock;

  return (
    <div className="fixed bottom-0 right-0 w-full sm:w-[450px] h-[70vh] glass-panel z-[120] border-t border-l border-white/[0.15] bg-[#0F141B]/95 backdrop-blur-3xl flex flex-col shadow-[-10px_-10px_40px_rgba(0,0,0,0.5)] slide-in-bottom">
      
      {/* Precision Header */}
      <header className="h-14 px-6 border-b border-white/[0.08] flex justify-between items-center bg-white/[0.02]">
        <div className="flex items-center gap-3">
          <Terminal size={14} className="text-indigo-400" />
          <span className="font-bold text-[10px] tracking-[0.25em] text-slate-500 uppercase">
            {ticker} // NEURAL_LINK
          </span>
          {sessionId && (
            <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-indigo-500/10 border border-indigo-500/20">
               <div className="w-1 h-1 rounded-full bg-indigo-500 animate-pulse" />
               <span className="text-[8px] font-bold text-indigo-400 uppercase tracking-widest">ACTIVE_LLM</span>
            </div>
          )}
        </div>
        <button onClick={onClose} className="p-2 rounded-full hover:bg-white/[0.05] text-slate-500 hover:text-white transition-all">
          <X size={18} />
        </button>
      </header>

      {/* Terminal Output */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6 no-scrollbar scrolling-touch">
        {initializing ? (
          <div className="flex flex-col items-center justify-center py-10 gap-4">
             <Loader2 size={20} className="text-indigo-500 animate-spin" />
             <span className="text-[9px] font-bold text-slate-600 uppercase tracking-[0.3em] animate-pulse">Initializing V4 Manifest...</span>
          </div>
        ) : (
          messages.map((m, i) => (
            <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'} animate-fade-in`}>
              <div className={`max-w-[90%] p-4 rounded-2xl text-[12px] leading-relaxed relative ${
                m.role === 'user'
                  ? 'bg-indigo-600/10 border border-indigo-500/20 text-white rounded-tr-none'
                  : 'bg-white/[0.03] border border-white/[0.08] text-slate-300 rounded-tl-none'
              }`}>
                <div className="font-mono">{renderContent(m.content)}</div>
                {m.sources && m.sources.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-white/[0.05] flex flex-wrap gap-2">
                     <span className="text-[8px] font-bold text-slate-600 uppercase tracking-widest block w-full mb-1">Knowledge Sources:</span>
                     {m.sources.map((s, si) => (
                       <span key={si} className="text-[9px] px-2 py-0.5 rounded bg-black/40 border border-white/[0.05] text-indigo-400/80 font-mono italic">
                         #{s}
                       </span>
                     ))}
                  </div>
                )}
              </div>
            </div>
          ))
        )}
        {loading && (
          <div className="flex justify-start animate-fade-in">
            <div className="bg-white/[0.03] border border-white/[0.08] p-4 rounded-2xl rounded-tl-none">
              <div className="flex items-center gap-3 text-indigo-400">
                <div className="flex gap-1">
                  <div className="w-1 h-1 rounded-full bg-current animate-bounce" />
                  <div className="w-1 h-1 rounded-full bg-current animate-bounce [animation-delay:0.2s]" />
                  <div className="w-1 h-1 rounded-full bg-current animate-bounce [animation-delay:0.4s]" />
                </div>
                <span className="text-[10px] font-bold text-slate-600 uppercase tracking-widest italic">AXIOM is synthesizing...</span>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Console */}
      <div className="p-6 border-t border-white/[0.08] bg-white/[0.01]">
        <div className="flex gap-2 overflow-x-auto pb-4 no-scrollbar">
          {questions.map(q => (
            <button
              key={q}
              onClick={() => handleSend(q)}
              disabled={loading}
              className="shrink-0 px-4 py-2 rounded-xl bg-white/[0.03] border border-white/[0.08] text-[9px] font-bold text-slate-500 uppercase tracking-widest hover:bg-white/[0.06] hover:border-white/[0.15] hover:text-white transition-all disabled:opacity-30 flex items-center gap-2 group"
            >
              <ChevronRight size={10} className="text-indigo-500/40 group-hover:text-indigo-400" />
              {q}
            </button>
          ))}
        </div>
        <div className="relative flex items-center">
          <input
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSend()}
            placeholder={`QUANTUM_QUERY :: ${ticker}...`}
            disabled={loading}
            className="w-full h-12 bg-black/40 border border-white/[0.08] rounded-xl px-4 pr-14 text-[12px] text-white font-mono focus:outline-none focus:border-indigo-500/40 transition-all placeholder:text-slate-800 disabled:opacity-30"
          />
          <button
            onClick={() => handleSend()}
            disabled={loading || !input.trim()}
            className="absolute right-2 w-10 h-10 flex items-center justify-center bg-indigo-600 rounded-lg hover:bg-indigo-500 transition-all disabled:opacity-30 shadow-lg shadow-indigo-900/20 group"
          >
            <Send size={16} className="text-white group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
          </button>
        </div>
      </div>
    </div>
  );
}
