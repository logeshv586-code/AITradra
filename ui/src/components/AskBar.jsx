import React, { useState, useRef, useEffect } from 'react';
import { Search, Brain, Send, X, Loader2, MessageSquare, Sparkles } from 'lucide-react';
import { API_BASE } from '../api_config';

export default function AskBar({ onResult }) {
  const [query, setQuery] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamedResponse, setStreamedResponse] = useState('');
  const [showModal, setShowModal] = useState(false);
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [streamedResponse]);

  const handleAsk = async (e) => {
    if (e) e.preventDefault();
    if (!query.trim() || isStreaming) return;

    setIsStreaming(true);
    setStreamedResponse('');
    setShowModal(true);

    try {
      const response = await fetch(`${API_BASE}/api/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: query }),
      });

      if (!response.ok) throw new Error('Network error');

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        
        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const token = line.replace('data: ', '').replace('\\n', '\n');
            if (token === '[DONE]') {
                setIsStreaming(false);
                break;
            }
            if (token.startsWith('[ERROR]')) {
                setStreamedResponse(p => p + '\n' + token);
                setIsStreaming(false);
                break;
            }
            setStreamedResponse(prev => prev + token);
          }
        }
      }
    } catch (err) {
      setStreamedResponse(`[CONNECTION ERROR]: ${err.message}`);
      setIsStreaming(false);
    }
  };

  return (
    <div className="relative w-full max-w-2xl mx-auto">
      <form onSubmit={handleAsk} className="relative group">
        <div className={`absolute inset-0 bg-indigo-500/10 rounded-xl blur-md transition-opacity duration-500 ${isStreaming ? 'opacity-100' : 'opacity-0'}`} />
        
        <div className="relative flex items-center bg-[#13171f] border border-white/[0.08] rounded-xl overflow-hidden focus-within:border-indigo-500/50 transition-all shadow-2xl">
          <div className="pl-4 text-slate-500">
            {isStreaming ? <Brain size={18} className="text-indigo-400 animate-pulse" /> : <Search size={18} />}
          </div>
          
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask AITradra anything... (e.g. Why is BTC surging?)"
            className="flex-1 bg-transparent border-none outline-none py-3.5 px-4 text-[14px] text-white placeholder-slate-600 font-medium"
          />
          
          <div className="pr-2 flex items-center gap-2">
            {!isStreaming && query && (
               <button 
                 type="button" 
                 onClick={() => setQuery('')}
                 className="p-1.5 rounded-md hover:bg-white/5 text-slate-500 transition-colors"
                >
                 <X size={14} />
               </button>
            )}
            <button
              type="submit"
              disabled={!query.trim() || isStreaming}
              className={`p-2 rounded-lg transition-all ${
                query.trim() && !isStreaming 
                  ? 'bg-indigo-600 text-white hover:bg-indigo-500 shadow-lg shadow-indigo-500/20' 
                  : 'text-slate-700 bg-white/[0.02]'
              }`}
            >
              <Send size={16} />
            </button>
          </div>
        </div>
      </form>

      {/* RAG Results Modal */}
      {showModal && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/80 backdrop-blur-sm" onClick={() => !isStreaming && setShowModal(false)} />
          
          <div className="relative w-full max-w-3xl max-h-[80vh] bg-[#0c0e12] border border-white/[0.1] rounded-2xl shadow-2xl flex flex-col overflow-hidden animate-in fade-in zoom-in duration-200">
            {/* Modal Header */}
            <div className="px-6 py-4 border-b border-white/[0.06] flex items-center justify-between bg-white/[0.02]">
              <div className="flex items-center gap-3">
                <div className="h-8 w-8 rounded-lg bg-indigo-500/20 flex items-center justify-center border border-indigo-500/30">
                  <Brain size={18} className="text-indigo-400" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-white uppercase tracking-wider">AITradra_Knowledge_Base</h3>
                  <div className="flex items-center gap-2">
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
                    <span className="text-[10px] text-slate-500 font-mono">NEURAL_RAG_FLOW_ACTIVE</span>
                  </div>
                </div>
              </div>
              <button 
                onClick={() => setShowModal(false)}
                className="p-2 rounded-full hover:bg-white/5 text-slate-500 transition-colors"
              >
                <X size={20} />
              </button>
            </div>

            {/* Modal Content */}
            <div 
              ref={scrollRef}
              className="flex-1 overflow-y-auto p-8 text-[15px] leading-relaxed text-slate-200 font-medium selection:bg-indigo-500/30 no-scrollbar"
            >
              <div className="flex items-start gap-4 mb-6 opacity-40">
                <MessageSquare size={16} className="mt-1" />
                <p className="italic">"{query}"</p>
              </div>

              <div className="space-y-4">
                <div className="flex items-center gap-2 text-indigo-400">
                   <Sparkles size={16} />
                   <span className="text-[11px] font-bold uppercase tracking-[0.2em]">Synthesis_Result</span>
                </div>
                <div className="p-1">
                   {streamedResponse || (
                     <div className="flex items-center gap-3 text-slate-600">
                        <Loader2 size={16} className="animate-spin" />
                        <span className="text-sm italic">Accessing Qdrant index and Hydrating Market Context...</span>
                     </div>
                   )}
                </div>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="px-6 py-4 border-t border-white/[0.06] bg-black/40 flex justify-between items-center text-[10px] text-slate-600 font-mono">
               <span>AXIOM_V4.0_CORE</span>
               <div className="flex gap-4">
                  <span>LATENCY: {isStreaming ? 'MEASURING' : 'READY'}</span>
                  <span className="text-emerald-500/60">SOURCE: MIXED_RAG</span>
               </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
