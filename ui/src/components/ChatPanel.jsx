import React, { useState, useRef, useEffect } from "react";
import { MessageSquareText, Send, Loader2, Bot, User, ShieldAlert, Sparkles } from "lucide-react";
import ReactMarkdown from 'react-markdown';

export default function ChatPanel({ messages = [], onSend, fullView = false, intelligenceStatus = null }) {
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const endRef = useRef(null);
  const providerLabel =
    intelligenceStatus?.model_router?.last_provider_used ||
    intelligenceStatus?.model_router?.active_provider ||
    "adaptive";
  const learningLabel = intelligenceStatus?.self_improvement?.loop_running ? "learning loop active" : "telemetry standby";

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim() || loading) return;
    
    const text = input;
    setInput("");
    setLoading(true);
    await onSend(text);
    setLoading(false);
  };

  return (
    <div className={`flex flex-col ${fullView ? 'h-[calc(100vh-140px)] w-full max-w-4xl mx-auto py-6' : 'h-full w-full'}`}>
      
      {/* Messages Area */}
      <div className={`flex-1 overflow-y-auto no-scrollbar p-5 flex flex-col gap-6 ${fullView ? 'bg-[var(--card-bg)] border border-[var(--border-color)] rounded-t-[var(--radius-lg)] shadow-sm' : ''}`}>
        
         {/* Welcome Message */}
         {messages.length === 0 && (
           <div className="flex flex-col items-center justify-center text-center mt-12 opacity-80 animate-fade-in px-4">
              <div className="flex h-16 w-16 items-center justify-center rounded-full bg-[#1e232b] border border-[var(--border-color)] mb-6 shadow-sm">
                 <Sparkles size={28} className="text-[var(--accent)]" />
              </div>
              <h3 className="heading-2 text-white">Ask Mythic AI</h3>
              <p className="mt-3 text-[13px] text-[var(--text-muted)] max-w-[280px] leading-relaxed">
                 Interrogate the underlying intelligence network directly. Queries can range from asset specifics to broader macro views.
              </p>
              
              <div className="flex flex-wrap items-center justify-center gap-2 mt-8 max-w-lg">
                 {["Market pulse for today?", "Analyze NVDA sentiment", "Explain $AAPL recent move", "Top breakout candidates?"].map(p => (
                   <button 
                     key={p} 
                     onClick={() => { setInput(p); }}
                     className="px-3 py-1.5 rounded-full bg-[#1e232b] border border-[var(--border-color)] text-[11px] text-[var(--text-muted)] hover:border-[var(--accent)] hover:text-white transition-all"
                   >
                     {p}
                   </button>
                 ))}
              </div>
           </div>
         )}

        {/* Message Bubbles */}
        {messages.map((m, i) => {
           const isUser = m.role === "user";
           return (
             <div key={i} className={`flex gap-3 animate-fade-in ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
               <div className="shrink-0 pt-1">
                 {isUser ? (
                    <div className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-800 border border-slate-600 text-slate-300">
                       <User size={14} />
                    </div>
                 ) : (
                    <div className="flex h-8 w-8 items-center justify-center rounded-full bg-[var(--accent-bg)] border border-[var(--accent)] border-opacity-30 text-[var(--accent)]">
                       <Bot size={14} />
                    </div>
                 )}
               </div>
               
               <div className={`flex flex-col max-w-[85%] ${isUser ? 'items-end' : 'items-start'}`}>
                  <div className={`px-4 py-3 rounded-[var(--radius-lg)] text-[13px] leading-relaxed shadow-sm
                     ${isUser ? 
                       'bg-[var(--accent)] border border-[var(--accent-hover)] text-white' : 
                       'bg-[#1e232b] border border-[var(--border-color)] text-[var(--text-main)] prose prose-invert prose-sm min-w-[200px] prose-p:leading-relaxed prose-pre:bg-[var(--app-bg)] prose-pre:border prose-pre:border-[var(--border-color)] prose-headings:text-white'
                     }`}
                  >
                     {isUser ? (
                        <span>{m.text}</span>
                     ) : (
                        <ReactMarkdown>{m.text}</ReactMarkdown>
                     )}
                  </div>
                  {m.text === "Connection to Axiom.AI expert system failed." && (
                     <div className="flex items-center gap-1.5 mt-2 text-[10px] text-[var(--negative)]">
                        <ShieldAlert size={12}/> Connection Interrupted
                     </div>
                  )}
               </div>
             </div>
           );
        })}
        {loading && (
           <div className="flex gap-3 animate-fade-in">
              <div className="shrink-0 pt-1">
                 <div className="flex h-8 w-8 items-center justify-center rounded-full bg-[var(--accent-bg)] border border-[var(--accent)] border-opacity-30 text-[var(--accent)]">
                    <Bot size={14} />
                 </div>
              </div>
              <div className="px-4 py-3 rounded-[var(--radius-lg)] bg-[#1e232b] border border-[var(--border-color)] flex items-center justify-center gap-2">
                 <Loader2 size={16} className="text-[var(--accent)] animate-spin" />
                 <span className="text-[12px] font-medium text-[var(--text-muted)]">Synthesizing...</span>
              </div>
           </div>
        )}
        <div ref={endRef} />
      </div>

      {/* Input Area */}
      <div className={`p-4 border-t border-[var(--border-color)] bg-[var(--app-bg)] ${fullView ? 'bg-[var(--card-bg)] border border-[var(--border-color)] border-t-0 rounded-b-[var(--radius-lg)] shadow-sm' : ''}`}>
        <form onSubmit={handleSubmit} className="relative flex items-center">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={loading}
            placeholder="Interrogate intelligence network..."
            className="w-full bg-[#1e232b] border border-[var(--border-color)] rounded-[var(--radius-lg)] pl-4 pr-12 py-3 text-[13px] text-white focus:outline-none focus:border-[var(--accent)] transition-colors shadow-sm disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={!input.trim() || loading}
            className="absolute right-2 top-1/2 -translate-y-1/2 h-8 w-8 flex items-center justify-center rounded-[var(--radius-md)] bg-[var(--accent)] text-white hover:bg-[var(--accent-hover)] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Send size={14} className="ml-0.5" />
          </button>
        </form>
         <div className="mt-3 flex items-center justify-center gap-2">
            <span className="text-[10px] text-[var(--text-muted)] uppercase tracking-wider font-medium">{providerLabel} | {learningLabel}</span>
         </div>
      </div>

    </div>
  );
}
