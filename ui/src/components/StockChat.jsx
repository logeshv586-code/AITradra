import React, { useState, useEffect, useRef } from 'react';

const SUGGESTED_QUESTIONS = {
  stock: [
    "Why did it move today?",
    "Is now a good time to buy?",
    "What is the biggest risk?",
    "What's the 52-week high and low?",
    "Compare with sector peers",
  ],
  crypto: [
    "What's driving the price today?",
    "What's the market sentiment?",
    "Is this a good entry point?",
  ]
};

export default function StockChat({ ticker, context, onClose }) {
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [initializing, setInitializing] = useState(true);
  const messagesEndRef = useRef(null);
  const isCrypto = ticker?.includes('-USD');

  // Create a new session when the component mounts (stock clicked on globe)
  useEffect(() => {
    const createSession = async () => {
      try {
        const res = await fetch(`http://localhost:8000/api/chat/stock/${ticker}/session`, {
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
          content: `🧠 AXIOM MYTHIC ready for ${ticker}. Ask me anything about this stock — I'll use multi-agent specialists and local AI to answer.`,
          timestamp: new Date().toISOString(),
        }]);
      } finally {
        setInitializing(false);
      }
    };
    createSession();
  }, [ticker]);

  // Auto-scroll to bottom when new messages arrive
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
      // Use session endpoint if we have a session, otherwise use basic endpoint
      const url = sessionId
        ? `http://localhost:8000/api/chat/stock/${ticker}/session/${sessionId}`
        : `http://localhost:8000/api/chat/stock/${ticker}`;

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
    } catch (err) {
      setMessages(prev => [...prev, {
        role: "assistant",
        content: "⚠️ Connection interrupted. The AI model may be loading — please retry in a moment.",
        timestamp: new Date().toISOString(),
      }]);
    } finally {
      setLoading(false);
    }
  };

  // Render message content with basic markdown-like formatting
  const renderContent = (content) => {
    if (!content) return null;
    // Convert **bold** to <strong>, URLs to links
    const parts = content.split(/(\*\*[^*]+\*\*|https?:\/\/[^\s]+)/g);
    return parts.map((part, i) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        return <strong key={i} className="text-indigo-300">{part.slice(2, -2)}</strong>;
      }
      if (part.match(/^https?:\/\//)) {
        return (
          <a key={i} href={part} target="_blank" rel="noopener noreferrer"
             className="text-indigo-400 hover:text-indigo-300 underline break-all">
            🔗 {part.length > 50 ? part.substring(0, 50) + '...' : part}
          </a>
        );
      }
      return <span key={i}>{part}</span>;
    });
  };

  const questions = isCrypto ? SUGGESTED_QUESTIONS.crypto : SUGGESTED_QUESTIONS.stock;

  return (
    <div className="fixed bottom-0 right-0 w-full sm:w-[450px] h-2/3 clay-panel z-[110] border-t border-indigo-500/30 flex flex-col slide-in-bottom">
      <header className="p-4 border-b border-white/5 flex justify-between items-center bg-indigo-500/5">
        <div className="flex items-center gap-2">
          <span className="font-mono text-xs font-bold tracking-widest text-indigo-400">
            🧠 AXIOM MYTHIC — {ticker}
          </span>
          {sessionId && (
            <span className="text-[8px] px-2 py-0.5 rounded-full bg-green-500/20 text-green-400 border border-green-500/20">
              MYTHIC SESSION
            </span>
          )}
        </div>
        <button onClick={onClose} className="text-slate-500 hover:text-white">✕</button>
      </header>

      <div className="flex-1 overflow-y-auto p-4 space-y-4 font-mono text-xs">
        {initializing && (
          <div className="text-indigo-400 animate-pulse text-center py-4">
            ⚡ Initializing AI session for {ticker}...
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[85%] p-3 rounded-2xl whitespace-pre-wrap leading-relaxed ${
              m.role === 'user'
                ? 'bg-indigo-600/20 border border-indigo-500/20'
                : 'bg-white/5 border border-white/10'
            }`}>
              {renderContent(m.content)}
              {m.sources && m.sources.length > 0 && (
                <div className="mt-2 pt-2 border-t border-white/5 text-[9px] text-slate-500">
                  Sources: {m.sources.join(', ')}
                </div>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-white/5 border border-white/10 p-3 rounded-2xl">
              <div className="flex items-center gap-2 text-indigo-400">
                <span className="animate-pulse">●</span>
                <span className="animate-pulse" style={{ animationDelay: '0.2s' }}>●</span>
                <span className="animate-pulse" style={{ animationDelay: '0.4s' }}>●</span>
                <span className="ml-2 text-slate-500 italic">AI is thinking...</span>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="p-4 border-t border-white/5 bg-black/20">
        <div className="flex gap-2 overflow-x-auto pb-3 no-scrollbar">
          {questions.map(q => (
            <button
              key={q}
              onClick={() => handleSend(q)}
              disabled={loading}
              className="shrink-0 px-3 py-1.5 rounded-full bg-white/5 border border-white/10 text-[10px] text-slate-400 hover:bg-white/10 transition-colors disabled:opacity-50"
            >
              {q}
            </button>
          ))}
        </div>
        <div className="flex gap-2">
          <input
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSend()}
            placeholder={`Ask anything about ${ticker}...`}
            disabled={loading}
            className="flex-1 bg-white/5 border border-white/10 rounded-xl px-4 py-2 text-xs focus:outline-none focus:border-indigo-500/50 disabled:opacity-50"
          />
          <button
            onClick={() => handleSend()}
            disabled={loading}
            className="p-2 bg-indigo-600 rounded-xl hover:bg-indigo-500 transition-colors disabled:opacity-50"
          >
            ➔
          </button>
        </div>
      </div>
    </div>
  );
}
