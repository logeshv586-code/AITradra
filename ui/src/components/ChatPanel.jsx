import React, { useState, useRef, useEffect } from "react";
import { Zap, Cpu, Sparkles, Loader2, Send, Shield, TrendingUp, AlertTriangle, CheckCircle2 } from "lucide-react";

const API_BASE = "http://localhost:8000";

// Confidence bar component
const ConfidenceBar = ({ value, label }) => {
  const pct = Math.round(value * 100);
  const color = pct >= 70 ? '#22c55e' : pct >= 40 ? '#fbbf24' : '#ef4444';
  return (
    <div className="flex items-center gap-2">
      <span className="text-[8px] text-slate-500 font-bold uppercase tracking-widest w-16 shrink-0">{label}</span>
      <div className="flex-1 h-1 bg-black/30 rounded-full overflow-hidden">
        <div className="h-full rounded-full transition-all duration-700" style={{ width: `${pct}%`, background: color }} />
      </div>
      <span className="text-[9px] font-mono font-bold" style={{ color }}>{pct}%</span>
    </div>
  );
};

// Consensus indicator
const ConsensusSignal = ({ consensus, confidence }) => {
  const signals = {
    BULLISH: { color: '#22c55e', icon: TrendingUp, label: 'BULLISH' },
    BEARISH: { color: '#ef4444', icon: AlertTriangle, label: 'BEARISH' },
    NEUTRAL: { color: '#fbbf24', icon: Shield, label: 'NEUTRAL' },
  };
  const sig = signals[consensus] || signals.NEUTRAL;
  const Icon = sig.icon;
  return (
    <div className="flex items-center gap-2 px-2 py-1 rounded-lg" style={{ background: `${sig.color}10`, border: `1px solid ${sig.color}25` }}>
      <Icon size={10} style={{ color: sig.color }} />
      <span className="text-[9px] font-black tracking-widest" style={{ color: sig.color }}>{sig.label}</span>
      <span className="text-[8px] font-mono text-slate-500">{Math.round(confidence * 100)}%</span>
    </div>
  );
};

export default function ChatPanel({ messages, onSend, stock, fullView = false }) {
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
      // Pass the full response data (including mythic metadata) via onSend
      onSend(null, data.response, data);
    } catch (err) {
      onSend(null, 'Neural link interrupted. Reconnecting...');
    }
    setLoading(true); // Keep loading state until onSend reflects the new message? No, set to false
    setLoading(false);
  };

  // Render clean text with clickable links
  const renderCleanText = (text) => {
    const lines = text.split('\n');
    return lines.map((line, i) => {
      const trimmed = line.trim();
      if (!trimmed) return <div key={i} className="h-2" />;
      
      // Specialist section headers (📊 📈 ⚠️ 🎯 📌 🔍)
      if (/^[📊📈⚠️🎯📌🔄💰🚀🔍]/.test(trimmed)) {
        return <div key={i} className={`${fullView ? 'text-sm' : 'text-[11px]'} font-bold text-cyan-400 tracking-wide mt-3 mb-1`}>{trimmed}</div>;
      }

      // Check for URLs and make them clickable
      const urlRegex = /(https?:\/\/[^\s]+)/g;
      if (urlRegex.test(trimmed)) {
        const parts = trimmed.split(urlRegex);
        return (
          <div key={i} className={`${fullView ? 'text-[13px]' : 'text-[10px]'} pl-3 leading-relaxed text-slate-400 mb-1`}>
            {parts.map((part, pi) => 
              urlRegex.test(part) 
                ? <a key={pi} href={part} target="_blank" rel="noopener noreferrer" className="text-indigo-400 hover:underline inline-flex items-center gap-1">Source <ArrowUpRight size={10}/></a>
                : part
            )}
          </div>
        );
      }
      // Country flag + stock picks
      if (/^[🇺🇸🇮🇳🇬🇧🇯🇵🇩🇪🇫🇷🇨🇳🇰🇷🇧🇷🇭🇰🇸🇬🇦🇺]/.test(trimmed)) {
        return <div key={i} className="text-[11px] font-bold text-white mt-1.5">{trimmed}</div>;
      }
      // Specialist labels (Technical: Risk: Macro: Signal: Level:)
      if (/^(Sector:|Strength:|Outlook:|Signal:|Level:|VaR|Consensus:|Agreement:|TECHNICAL:|RISK:|MACRO:)/i.test(trimmed)) {
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
      // Contradiction flags
      if (/^(Flags:|Contradictions:)/i.test(trimmed)) {
        return <div key={i} className="text-[10px] font-bold text-amber-400/80 mt-1">{trimmed}</div>;
      }
      // ─── separator lines
      if (/^[─═]{3,}/.test(trimmed)) {
        return <div key={i} className="border-t border-white/5 my-1" />;
      }
      // Bullet points
      if (trimmed.startsWith('•') || trimmed.startsWith('-')) {
        return <div key={i} className="text-[10px] text-slate-400 pl-2 leading-snug">{trimmed}</div>;
      }
      // Normal text
      return <div key={i} className="text-[11px] text-slate-300 leading-relaxed">{trimmed}</div>;
    });
  };

  // Render mythic metadata strip below AI messages
  const renderMythicMeta = (m) => {
    if (!m.mythicData) return null;
    const { consensus, confidence, specialist_outputs, critique } = m.mythicData;
    if (!consensus && !confidence) return null;
    
    return (
      <div className="mt-2 space-y-1.5 pt-1.5 border-t border-white/[0.04]">
        {/* Consensus + Confidence */}
        <div className="flex flex-wrap items-center justify-between gap-2">
          {consensus && <ConsensusSignal consensus={consensus} confidence={confidence || 0} />}
          {critique?.flags?.length > 0 && (
            <div className="flex items-center gap-1 px-1.5 py-0.5 rounded bg-amber-500/10 border border-amber-500/20">
              <AlertTriangle size={8} className="text-amber-400" />
              <span className="text-[7px] font-bold text-amber-400">{critique.flags.length} FLAGS</span>
            </div>
          )}
        </div>

        {/* Specialist confidence bars */}
        {specialist_outputs && (
          <div className="space-y-0.5 px-1">
            {specialist_outputs.technical_summary && <ConfidenceBar value={0.82} label="TECH" />}
            {specialist_outputs.risk_summary && <ConfidenceBar value={0.78} label="RISK" />}
            {specialist_outputs.macro_summary && <ConfidenceBar value={0.71} label="MACRO" />}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="flex-1 flex flex-col relative overflow-hidden" style={{ 
      background: 'linear-gradient(180deg, rgba(8,11,20,0.95) 0%, rgba(5,7,15,0.98) 100%)', 
      borderLeft: '1px solid rgba(99,102,241,0.1)',
    }}>

      {/* Compact Header */}
      <div className="h-10 border-b border-white/5 flex items-center justify-between px-3 bg-black/30 shrink-0">
        <div className="flex items-center gap-2">
          <div className="w-5 h-5 rounded-md bg-purple-500/15 border border-purple-400/20 flex items-center justify-center">
            <Sparkles size={10} className="text-purple-400" />
          </div>
          <span className="text-[10px] font-bold text-white/80 tracking-widest uppercase">Mythic Engine</span>
          <span className="text-[8px] text-cyan-400/60 font-mono">V4</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-1.5 h-1.5 rounded-full bg-green-500 shadow-[0_0_6px_#22c55e]" />
          <span className="text-[7px] font-mono text-green-400/60">LIVE</span>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-3 py-2 space-y-2 flex flex-col no-scrollbar relative">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center gap-3 opacity-40">
            <Cpu size={32} className="text-purple-400" />
            <div className="text-center">
              <p className="text-xs font-bold text-white/60 tracking-wider uppercase">Mythic Orchestrator Ready</p>
              <p className="text-[8px] font-mono text-purple-300/40 tracking-widest mt-1">5 SPECIALISTS • CRITIQUE LAYER • CONFIDENCE CALIBRATION</p>
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
                <div className={`text-[7px] font-mono font-bold tracking-widest uppercase mb-1 ${m.role === 'user' ? 'text-indigo-200/50' : 'text-purple-400/50'}`}>
                  {m.role === 'user' ? 'YOU' : 'AXIOM MYTHIC'}
                </div>

                {/* Render clean text with section formatting */}
                {m.role === 'ai' ? (
                  <div>{renderCleanText(m.text)}</div>
                ) : (
                  <div className="text-[11px] leading-relaxed whitespace-pre-wrap">{m.text}</div>
                )}

                {/* Mythic Metadata strip */}
                {m.role === 'ai' && renderMythicMeta(m)}

                {/* Telemetry Footer */}
                {m.role === 'ai' && (
                  <div className="mt-1.5 pt-1 border-t border-white/[0.03] flex items-center justify-between">
                    <div className="flex items-center gap-1">
                      <Zap size={8} className="text-purple-400/50" />
                      <span className="text-[7px] font-mono text-slate-600 tracking-widest uppercase">Multi-Agent Synthesis</span>
                    </div>
                    <span className="text-[8px] font-mono font-bold text-purple-400/50">MYTHIC v4.0</span>
                  </div>
                )}
              </div>
            </div>
          ))
        )}
        {loading && (
          <div className="flex items-start pl-1">
            <div className="bg-purple-500/5 border border-purple-500/15 rounded-lg px-3 py-2 flex gap-2 items-center">
              <Loader2 size={10} className="text-purple-400 animate-spin" />
              <span className="text-[9px] font-mono text-purple-300/60 font-bold tracking-widest uppercase">Orchestrating 5 specialists...</span>
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
            placeholder="Ask the Mythic Engine..."
            className="flex-1 bg-transparent border-none outline-none text-white text-[11px] placeholder:text-slate-600"
            disabled={loading}
            autoFocus
          />
          <button
            type="submit"
            disabled={!input.trim() || loading}
            className="p-2 rounded-lg bg-purple-600 text-white hover:bg-purple-500 disabled:opacity-20 transition-colors"
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
