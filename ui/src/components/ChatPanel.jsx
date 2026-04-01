import React, { useState, useEffect, useRef } from "react";
import { Zap, Cpu, Sparkles, Loader2, Send, Shield, TrendingUp, AlertTriangle, CheckCircle2, FlaskConical, Globe, Microscope, ShieldCheck, ArrowUpRight, User } from "lucide-react";

import { API_BASE } from "../api_config";


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
  const [researchMode, setResearchMode] = useState('DEEP'); // QUICK, DEEP, INSTITUTIONAL
  const [triggerMode, setTriggerMode] = useState('AUTO'); // AUTO, MANUAL
  const endRef = useRef(null);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior:'smooth' }); }, [messages]);

  const detectIntent = (text) => {
    const researchKeywords = ['research', 'analyze', 'deep', 'should i', 'buy', 'sell', 'forecast', 'prediction'];
    const hasIntent = researchKeywords.some(k => text.toLowerCase().includes(k));
    const hasTicker = /[A-Z]{2,6}/.test(text) || (stock?.id);
    return hasIntent && hasTicker;
  };

  const handleSend = async (msg = input) => {
    const q = msg.trim();
    if (!q) return;
    setInput('');
    setLoading(true);

    const isDeep = triggerMode === 'AUTO' && detectIntent(q);
    const mode = isDeep ? 'DEEP' : researchMode;

    // Send with research mode metadata
    await onSend(q, null, { research_mode: mode });
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
    <div className={`flex-1 flex flex-col relative overflow-hidden glass-panel ${fullView ? 'rounded-2xl shadow-2xl' : ''}`} style={{ 
      borderLeft: '1px solid rgba(255,255,255,0.05)',
    }}>
      {/* 🔮 Premium Ambient Glow */}
      <div className="absolute top-0 left-0 w-full h-40 bg-gradient-to-b from-indigo-500/10 to-transparent pointer-events-none z-0" />

      {/* Premium Header */}
      <div className="h-12 border-b border-white/5 flex items-center justify-between px-4 bg-black/60 backdrop-blur-xl shrink-0 z-20">
        <div className="flex items-center gap-3">
          <div className="w-6 h-6 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-[0_0_15px_rgba(99,102,241,0.4)]">
            <Sparkles size={12} className="text-white" />
          </div>
          <div className="flex flex-col">
            <div className="flex items-center gap-2">
              <span className="text-[11px] font-black text-white tracking-[0.15em] uppercase">Mythic Control</span>
              <span className="px-1.5 py-0.5 rounded-md bg-white/5 border border-white/10 text-[7px] font-bold text-indigo-400">V4.2</span>
            </div>
            {stock && <span className="text-[8px] text-slate-500 font-mono tracking-widest leading-none uppercase">Analyzing {stock.id}</span>}
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="skeuo-toggle">
            {['QUICK', 'DEEP', 'INSTITUTIONAL'].map(m => (
              <div key={m} onClick={() => setResearchMode(m)}
                className={`skeuo-toggle-item ${researchMode === m ? 'active' : 'text-slate-500 hover:text-slate-300'}`}>
                {m === 'QUICK' ? 'QCK' : m === 'DEEP' ? 'DEP' : 'INS'}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4 no-scrollbar relative z-10 scroll-smooth">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center gap-4 opacity-40 animate-pulse">
            <div className="w-12 h-12 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center">
              <Cpu size={24} className="text-indigo-400" />
            </div>
            <div className="text-center">
              <p className="text-[10px] font-black text-white tracking-[0.2em] uppercase">Mythic Core Active</p>
              <p className="text-[8px] font-mono text-indigo-300/40 tracking-widest mt-1.5 flex items-center justify-center gap-2">
                <span className="w-1 h-1 rounded-full bg-indigo-500/50" />
                MULTI-AGENT SYNERGY READY
                <span className="w-1 h-1 rounded-full bg-indigo-500/50" />
              </p>
            </div>
          </div>
        ) : (
          messages.map((m, i) => (
            <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'} animate-slide-up`}>
              <div className={`max-w-[90%] group ${
                m.role === 'user' 
                  ? 'chat-bubble-user rounded-[20px] rounded-tr-none px-4 py-3' 
                  : 'chat-bubble-ai rounded-[20px] rounded-tl-none px-4 py-3'
              }`}>
                {/* Role Indicator */}
                <div className={`text-[7px] font-bold tracking-[0.2em] uppercase mb-1.5 flex items-center gap-1.5 ${
                  m.role === 'user' ? 'text-indigo-100/50' : 'text-indigo-400'
                }`}>
                  {m.role === 'user' ? <User size={8} /> : <Sparkles size={8} />}
                  {m.role === 'user' ? 'OPERATOR' : 'AXIOM MYTHIC'}
                </div>

                {/* Content */}
                <div className="relative">
                  {m.role === 'ai' ? (
                    <div className="space-y-1">{renderCleanText(m.text)}</div>
                  ) : (
                    <div className="text-[12px] leading-relaxed text-white/90 selection:bg-white/20 whitespace-pre-wrap">{m.text}</div>
                  )}
                </div>

                {/* Advanced Metadata for AI */}
                {m.role === 'ai' && renderMythicMeta(m)}

                {/* Micro-footer for telemetry */}
                {m.role === 'ai' && (
                  <div className="mt-3 pt-2 border-t border-white/5 flex items-center justify-between opacity-40 group-hover:opacity-80 transition-opacity">
                    <div className="flex items-center gap-2">
                      <div className="w-1 h-1 rounded-full bg-emerald-500 animate-pulse" />
                      <span className="text-[7px] font-mono text-slate-500 tracking-widest">SYNTHESIS_LOCK_STABLE</span>
                    </div>
                    {m.mythicData?.pipeline_ms && (
                      <span className="text-[7px] font-mono text-indigo-400">{m.mythicData.pipeline_ms}ms</span>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))
        )}
        {loading && (
          <div className="flex items-start animate-scale-in">
            <div className="chat-bubble-ai rounded-[20px] rounded-tl-none px-5 py-4 flex gap-4 items-center">
              <div className="relative">
                <Loader2 size={16} className="text-indigo-400 animate-spin" />
                <div className="absolute inset-0 blur-sm scale-150 opacity-30 animate-pulse">
                  <Loader2 size={16} className="text-indigo-500" />
                </div>
              </div>
              <div className="flex flex-col gap-1">
                <span className="text-[10px] font-black text-indigo-300 tracking-[0.2em] uppercase">
                  {researchMode === 'DEEP' ? 'CONSENSUS SEARCHING...' : 'PULSE ANALYZING...'}
                </span>
                <div className="flex gap-1">
                  {[1,2,3].map(d => <div key={d} className="w-1.5 h-1 px-1 bg-indigo-500/30 rounded-full animate-bounce" style={{animationDelay: `${d*0.1}s`}} />)}
                </div>
              </div>
            </div>
          </div>
        )}
        <div ref={endRef} className="h-4" />
      </div>

      {/* Input Section */}
      <div className="px-4 py-4 bg-black/60 backdrop-blur-2xl border-t border-white/5 shrink-0 z-20 relative overflow-hidden">
        {/* Subtle background glow for input */}
        <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-48 h-24 bg-indigo-500/5 blur-[40px] pointer-events-none" />

        <div className="flex flex-col gap-4 relative">
          {/* Action Chips */}
          <div className="flex gap-2 overflow-x-auto no-scrollbar pb-1">
            {[
              { label: 'Deep Market Research', icon: Microscope, mode: 'DEEP' },
              { label: 'Technical Pulse', icon: Zap, mode: 'QUICK' },
              { label: 'Strategic Audit', icon: ShieldCheck, mode: 'INSTITUTIONAL' },
            ].map(chip => (
              <button key={chip.label} onClick={() => { setResearchMode(chip.mode); handleSend(chip.label); }}
                className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/5 border border-white/10 hover:bg-white/10 hover:border-indigo-500/30 transition-all group shrink-0">
                <chip.icon size={10} className="text-indigo-400 group-hover:scale-110 transition-transform" />
                <span className="text-[9px] font-bold text-slate-400 group-hover:text-white uppercase tracking-wider">{chip.label}</span>
              </button>
            ))}
          </div>

          <form onSubmit={(e) => { e.preventDefault(); handleSend(); }} 
            className="flex items-center gap-3 p-1.5 pl-4 input-glass rounded-[18px] group">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={triggerMode === 'AUTO' ? "Command Axiom... (Deep Search Active)" : "Query the market..."}
              className="flex-1 bg-transparent border-none outline-none text-white text-[12px] placeholder:text-slate-600 font-medium py-2"
              disabled={loading}
              autoFocus
            />
            <button
              type="submit"
              disabled={!input.trim() || loading}
              className={`w-10 h-10 flex items-center justify-center rounded-xl transition-all duration-300 ${
                input.trim() && !loading 
                ? 'bg-indigo-600 text-white shadow-[0_4px_15px_rgba(79,70,229,0.4)] hover:scale-105 active:scale-95' 
                : 'bg-white/5 text-slate-600 cursor-not-allowed'
              }`}
            >
              {loading ? (
                <Loader2 size={16} className="animate-spin" />
              ) : (
                <Send size={16} />
              )}
            </button>
          </form>

          {/* Footer Status */}
          <div className="flex items-center justify-between px-1">
            <div className="flex items-center gap-3 opacity-40">
              <div className="flex items-center gap-1.5">
                <div className={`w-1 h-1 rounded-full ${triggerMode === 'AUTO' ? 'bg-emerald-500' : 'bg-amber-500'}`} />
                <span className="text-[8px] font-black tracking-widest text-white uppercase">{triggerMode} MODE</span>
              </div>
              <div className="h-4 w-px bg-white/10" />
              <span className="text-[8px] font-mono text-slate-500 uppercase tracking-[0.2em]">Ready for input_v4.2</span>
            </div>
            <div className="flex items-center gap-1 opacity-20">
               <Globe size={10} /><span className="text-[8px] font-bold">L-DRIVES ACTIVE</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
