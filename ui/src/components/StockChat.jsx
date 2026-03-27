import React, { useState } from 'react';

const SUGGESTED_QUESTIONS = [
  "Why did it move today?",
  "Is now a good time to buy?",
  "What is the biggest risk?",
  "What do analysts say?",
];

export default function StockChat({ ticker, context, onClose }) {
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content: `I am the OMNI-DATA agent for ${ticker}. I have synthesized recent market news and sentiment. What would you like to know?`
    }
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSend = async (text = input) => {
    const msg = text.trim();
    if (!msg) return;

    setMessages(prev => [...prev, { role: "user", content: msg }]);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch(`http://localhost:8000/api/chat/stock/${ticker}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: msg })
      });
      const data = await res.json();
      setMessages(prev => [...prev, { role: "assistant", content: data.response }]);
    } catch (err) {
      setMessages(prev => [...prev, { role: "assistant", content: "Signal lost. Reconnecting..." }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed bottom-0 right-0 w-full sm:w-[450px] h-2/3 clay-panel z-[110] border-t border-indigo-500/30 flex flex-col slide-in-bottom">
      <header className="p-4 border-b border-white/5 flex justify-between items-center bg-indigo-500/5">
        <span className="font-mono text-xs font-bold tracking-widest text-indigo-400">🧠 {ticker} AI ANALYST</span>
        <button onClick={onClose} className="text-slate-500 hover:text-white">✕</button>
      </header>
      
      <div className="flex-1 overflow-y-auto p-4 space-y-4 font-mono text-xs">
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[85%] p-3 rounded-2xl ${m.role === 'user' ? 'bg-indigo-600/20 border border-indigo-500/20' : 'bg-white/5 border border-white/10'}`}>
               {m.content}
            </div>
          </div>
        ))}
        {loading && <div className="text-indigo-400 animate-pulse italic">Neural link processing...</div>}
      </div>

      <div className="p-4 border-t border-white/5 bg-black/20">
        <div className="flex gap-2 overflow-x-auto pb-3 no-scrollbar">
           {SUGGESTED_QUESTIONS.map(q => (
             <button 
               key={q} 
               onClick={() => handleSend(q)}
               className="shrink-0 px-3 py-1.5 rounded-full bg-white/5 border border-white/10 text-[10px] text-slate-400 hover:bg-white/10 transition-colors"
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
             placeholder="Ask anything..."
             className="flex-1 bg-white/5 border border-white/10 rounded-xl px-4 py-2 text-xs focus:outline-none focus:border-indigo-500/50"
           />
           <button onClick={() => handleSend()} className="p-2 bg-indigo-600 rounded-xl hover:bg-indigo-500 transition-colors">
             ➔
           </button>
        </div>
      </div>
    </div>
  );
}
