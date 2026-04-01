import React, { useState, useEffect, useRef } from "react";
import {
  Zap,
  Cpu,
  Sparkles,
  Loader2,
  Send,
  Shield,
  TrendingUp,
  AlertTriangle,
  Globe,
  Microscope,
  ShieldCheck,
  ArrowUpRight,
  User,
} from "lucide-react";

const ConfidenceBar = ({ value, label }) => {
  const pct = Math.round(value * 100);
  const color = pct >= 70 ? "#22c55e" : pct >= 40 ? "#fbbf24" : "#ef4444";

  return (
    <div className="flex items-center gap-2.5">
      <span className="w-16 shrink-0 text-[8px] font-bold uppercase tracking-widest text-slate-500">{label}</span>
      <div className="h-1.5 flex-1 overflow-hidden rounded-full border border-white/[0.03] bg-black/40">
        <div className="h-full rounded-full transition-all duration-700 ease-out" style={{ width: `${pct}%`, background: color }} />
      </div>
      <span className="text-[9px] font-bold font-mono" style={{ color }}>
        {pct}%
      </span>
    </div>
  );
};

const ConsensusSignal = ({ consensus, confidence }) => {
  const signals = {
    BULLISH: { color: "#22c55e", icon: TrendingUp, label: "BULLISH" },
    BEARISH: { color: "#ef4444", icon: AlertTriangle, label: "BEARISH" },
    NEUTRAL: { color: "#fbbf24", icon: Shield, label: "NEUTRAL" },
  };
  const signal = signals[consensus] || signals.NEUTRAL;
  const Icon = signal.icon;

  return (
    <div
      className="flex items-center gap-2 rounded-full px-2.5 py-1"
      style={{ background: `${signal.color}12`, border: `1px solid ${signal.color}28` }}
    >
      <Icon size={10} style={{ color: signal.color }} />
      <span className="text-[9px] font-black tracking-widest" style={{ color: signal.color }}>
        {signal.label}
      </span>
      <span className="text-[8px] font-mono text-slate-500">{Math.round(confidence * 100)}%</span>
    </div>
  );
};

export default function ChatPanel({ messages, onSend, stock, fullView = false }) {
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [researchMode, setResearchMode] = useState("DEEP");
  const [triggerMode, setTriggerMode] = useState("AUTO");
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const selectedTicker = stock?.id ? String(stock.id).toUpperCase() : null;

  const detectIntent = (text) => {
    const researchKeywords = ["research", "analyze", "deep", "should i", "buy", "sell", "forecast", "prediction"];
    const hasIntent = researchKeywords.some((keyword) => text.toLowerCase().includes(keyword));
    const hasTicker = /[A-Z]{2,6}/.test(text) || stock?.id;
    return hasIntent && hasTicker;
  };

  const handleSend = async (msg = input) => {
    const query = msg.trim();
    if (!query) return;
    setInput("");
    setLoading(true);

    const isDeep = triggerMode === "AUTO" && detectIntent(query);
    const mode = isDeep ? "DEEP" : researchMode;

    await onSend(query, null, { research_mode: mode });
    setLoading(false);
  };

  const renderCleanText = (text) => {
    const lines = text.split("\n");

    return lines.map((line, index) => {
      const trimmed = line.trim();
      if (!trimmed) return <div key={index} className="h-2" />;

      if (/^[^\w\s]/.test(trimmed) && trimmed.length < 64) {
        return (
          <div key={index} className={`${fullView ? "text-sm" : "text-[11px]"} mt-3 mb-1 font-bold tracking-wide text-cyan-400`}>
            {trimmed}
          </div>
        );
      }

      const urlRegex = /(https?:\/\/[^\s]+)/g;
      if (urlRegex.test(trimmed)) {
        const parts = trimmed.split(urlRegex);
        return (
          <div key={index} className={`${fullView ? "text-[13px]" : "text-[10px]"} mb-1 pl-3 leading-relaxed text-slate-400`}>
            {parts.map((part, partIndex) =>
              urlRegex.test(part) ? (
                <a
                  key={partIndex}
                  href={part}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-indigo-400 hover:underline"
                >
                  Source <ArrowUpRight size={10} />
                </a>
              ) : (
                part
              ),
            )}
          </div>
        );
      }

      if (/^(Sector:|Strength:|Outlook:|Signal:|Level:|VaR|Consensus:|Agreement:|TECHNICAL:|RISK:|MACRO:)/i.test(trimmed)) {
        const [label, ...rest] = trimmed.split(":");
        return (
          <div key={index} className="pl-3 text-[10px] leading-snug">
            <span className="font-bold text-indigo-400/70">{label}:</span>
            <span className="text-slate-400"> {rest.join(":")}</span>
          </div>
        );
      }

      if (/^(Confidence:)/i.test(trimmed)) {
        return (
          <div key={index} className="mt-1 border-t border-white/5 pt-1 text-[11px] font-bold text-emerald-400">
            {trimmed}
          </div>
        );
      }

      if (/^(Flags:|Contradictions:)/i.test(trimmed)) {
        return (
          <div key={index} className="mt-1 text-[10px] font-bold text-amber-400/80">
            {trimmed}
          </div>
        );
      }

      if (/^[-=]{3,}/.test(trimmed)) {
        return <div key={index} className="my-1 border-t border-white/5" />;
      }

      if (trimmed.startsWith("•") || trimmed.startsWith("-")) {
        return (
          <div key={index} className="pl-2 text-[10px] leading-snug text-slate-400">
            {trimmed}
          </div>
        );
      }

      return (
        <div key={index} className="text-[11px] leading-relaxed text-slate-300">
          {trimmed}
        </div>
      );
    });
  };

  const renderMythicMeta = (message) => {
    if (!message.mythicData) return null;
    const { consensus, confidence, specialist_outputs, critique } = message.mythicData;
    if (!consensus && !confidence) return null;

    return (
      <div className="mt-3 space-y-2 border-t border-white/[0.05] pt-2.5">
        <div className="flex flex-wrap items-center justify-between gap-2">
          {consensus && <ConsensusSignal consensus={consensus} confidence={confidence || 0} />}
          {critique?.flags?.length > 0 && (
            <div className="flex items-center gap-1 rounded-full border border-amber-500/20 bg-amber-500/10 px-2 py-1">
              <AlertTriangle size={8} className="text-amber-400" />
              <span className="text-[7px] font-bold text-amber-400">{critique.flags.length} FLAGS</span>
            </div>
          )}
        </div>

        {specialist_outputs && (
          <div className="space-y-1 px-1">
            {specialist_outputs.technical_summary && <ConfidenceBar value={0.82} label="TECH" />}
            {specialist_outputs.risk_summary && <ConfidenceBar value={0.78} label="RISK" />}
            {specialist_outputs.macro_summary && <ConfidenceBar value={0.71} label="MACRO" />}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className={`surface-card relative flex flex-1 flex-col overflow-hidden ${fullView ? "" : "h-full"}`}>
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(99,102,241,0.13),transparent_30%),radial-gradient(circle_at_bottom,rgba(16,185,129,0.06),transparent_25%)]" />

      <div className="relative z-10 border-b border-white/[0.08] bg-black/25 px-5 py-4">
        <div className="flex flex-col gap-4">
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-start gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-indigo-400/20 bg-indigo-500/10 shadow-[0_10px_24px_rgba(30,41,59,0.25)]">
                <Sparkles size={18} className="text-indigo-300" />
              </div>
              <div className="space-y-1.5">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-[10px] font-black uppercase tracking-[0.22em] text-white">Mythic Control</span>
                  <span className="surface-badge border-indigo-400/20 bg-indigo-500/10 text-indigo-300">V4.2</span>
                  {selectedTicker && <span className="surface-badge">{selectedTicker}</span>}
                </div>
                <p className="max-w-[32rem] text-[11px] leading-relaxed text-slate-400">
                  Collaborative market workspace for research, signal review, and portfolio follow-up.
                </p>
              </div>
            </div>

            <div className="hidden items-center gap-2 rounded-full border border-white/[0.08] bg-white/[0.03] px-2.5 py-1.5 md:flex">
              <div className="h-1.5 w-1.5 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.45)]" />
              <span className="text-[8px] font-black uppercase tracking-[0.2em] text-slate-400">{messages.length} messages</span>
            </div>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="skeuo-toggle">
              {["QUICK", "DEEP", "INSTITUTIONAL"].map((mode) => (
                <button
                  key={mode}
                  type="button"
                  onClick={() => setResearchMode(mode)}
                  className={`skeuo-toggle-item ${researchMode === mode ? "active" : "text-slate-500 hover:text-slate-300"}`}
                >
                  {mode === "QUICK" ? "QCK" : mode === "DEEP" ? "DEP" : "INS"}
                </button>
              ))}
            </div>

            <div className="flex items-center gap-1.5 rounded-full border border-white/[0.08] bg-white/[0.03] p-1">
              {["AUTO", "MANUAL"].map((mode) => (
                <button
                  key={mode}
                  type="button"
                  onClick={() => setTriggerMode(mode)}
                  className={`rounded-full px-3 py-1 text-[8px] font-black uppercase tracking-[0.2em] transition-all ${
                    triggerMode === mode
                      ? "bg-indigo-500/15 text-indigo-300 shadow-[inset_0_0_0_1px_rgba(99,102,241,0.3)]"
                      : "text-slate-500 hover:text-white"
                  }`}
                >
                  {mode}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="relative z-10 flex-1 space-y-4 overflow-y-auto px-4 py-5 scroll-smooth no-scrollbar md:px-5">
        {messages.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center gap-4 opacity-50">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl border border-indigo-500/20 bg-indigo-500/10">
              <Cpu size={24} className="text-indigo-400" />
            </div>
            <div className="text-center">
              <p className="text-[10px] font-black uppercase tracking-[0.2em] text-white">Mythic Core Active</p>
              <p className="mt-1.5 text-[8px] font-mono uppercase tracking-[0.22em] text-indigo-300/40">
                Multi-agent synergy ready
              </p>
            </div>
          </div>
        ) : (
          messages.map((message, index) => (
            <div
              key={index}
              className={`flex animate-slide-up ${message.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`group max-w-[90%] md:max-w-[84%] ${
                  message.role === "user"
                    ? "chat-bubble-user rounded-[24px] rounded-tr-md px-4 py-3.5"
                    : "chat-bubble-ai rounded-[24px] rounded-tl-md px-4 py-3.5"
                }`}
              >
                <div
                  className={`mb-2 flex items-center gap-1.5 text-[7px] font-bold uppercase tracking-[0.2em] ${
                    message.role === "user" ? "text-indigo-100/60" : "text-indigo-300"
                  }`}
                >
                  {message.role === "user" ? <User size={8} /> : <Sparkles size={8} />}
                  {message.role === "user" ? "Operator" : "Axiom Mythic"}
                </div>

                <div className="relative">
                  {message.role === "ai" ? (
                    <div className="space-y-1">{renderCleanText(message.text)}</div>
                  ) : (
                    <div className="whitespace-pre-wrap text-[12px] leading-relaxed text-white/90">{message.text}</div>
                  )}
                </div>

                {message.role === "ai" && renderMythicMeta(message)}

                {message.role === "ai" && (
                  <div className="mt-3 flex items-center justify-between border-t border-white/5 pt-2 opacity-45 transition-opacity group-hover:opacity-80">
                    <div className="flex items-center gap-2">
                      <div className="h-1 w-1 rounded-full bg-emerald-500 animate-pulse" />
                      <span className="text-[7px] font-mono uppercase tracking-[0.18em] text-slate-500">
                        SYNTHESIS_LOCK_STABLE
                      </span>
                    </div>
                    {message.mythicData?.pipeline_ms && (
                      <span className="text-[7px] font-mono text-indigo-400">{message.mythicData.pipeline_ms}ms</span>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))
        )}

        {loading && (
          <div className="flex items-start animate-scale-in">
            <div className="chat-bubble-ai flex items-center gap-4 rounded-[24px] rounded-tl-md px-5 py-4">
              <div className="relative">
                <Loader2 size={16} className="animate-spin text-indigo-400" />
                <div className="absolute inset-0 scale-150 animate-pulse opacity-30 blur-sm">
                  <Loader2 size={16} className="text-indigo-500" />
                </div>
              </div>
              <div className="flex flex-col gap-1">
                <span className="text-[10px] font-black uppercase tracking-[0.2em] text-indigo-300">
                  {researchMode === "DEEP" ? "Consensus searching..." : "Pulse analyzing..."}
                </span>
                <div className="flex gap-1">
                  {[1, 2, 3].map((dot) => (
                    <div
                      key={dot}
                      className="h-1 w-1.5 rounded-full bg-indigo-500/30 animate-bounce"
                      style={{ animationDelay: `${dot * 0.1}s` }}
                    />
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        <div ref={endRef} className="h-4" />
      </div>

      <div className="relative z-10 border-t border-white/[0.08] bg-black/35 px-4 py-4 md:px-5">
        <div className="pointer-events-none absolute inset-x-10 bottom-0 h-20 bg-gradient-to-r from-transparent via-indigo-500/10 to-transparent blur-3xl" />

        <div className="relative flex flex-col gap-4">
          <div className="flex gap-2 overflow-x-auto pb-1 no-scrollbar">
            {[
              { label: "Deep Market Research", icon: Microscope, mode: "DEEP" },
              { label: "Technical Pulse", icon: Zap, mode: "QUICK" },
              { label: "Strategic Audit", icon: ShieldCheck, mode: "INSTITUTIONAL" },
            ].map((chip) => (
              <button
                key={chip.label}
                type="button"
                onClick={() => {
                  setResearchMode(chip.mode);
                  handleSend(chip.label);
                }}
                className={`group shrink-0 rounded-full border px-3 py-2 transition-all ${
                  researchMode === chip.mode
                    ? "border-indigo-400/30 bg-indigo-500/10 text-white"
                    : "border-white/10 bg-white/5 text-slate-400 hover:border-white/20 hover:bg-white/10 hover:text-white"
                }`}
              >
                <span className="flex items-center gap-2">
                  <chip.icon size={10} className="text-indigo-400 transition-transform group-hover:scale-110" />
                  <span className="text-[9px] font-bold uppercase tracking-[0.16em]">{chip.label}</span>
                </span>
              </button>
            ))}
          </div>

          <form
            onSubmit={(event) => {
              event.preventDefault();
              handleSend();
            }}
            className="input-glass flex items-center gap-3 rounded-[20px] p-1.5 pl-4"
          >
            <input
              value={input}
              onChange={(event) => setInput(event.target.value)}
              placeholder={
                triggerMode === "AUTO" ? "Command Axiom... (deep routing active)" : "Query the market..."
              }
              className="flex-1 border-none bg-transparent py-2 text-[12px] font-medium text-white outline-none placeholder:text-slate-600"
              disabled={loading}
              autoFocus
            />
            <button
              type="submit"
              disabled={!input.trim() || loading}
              className={`flex h-10 w-10 items-center justify-center rounded-2xl transition-all duration-300 ${
                input.trim() && !loading
                  ? "bg-indigo-600 text-white shadow-[0_4px_15px_rgba(79,70,229,0.4)] hover:scale-105 active:scale-95"
                  : "cursor-not-allowed bg-white/5 text-slate-600"
              }`}
            >
              {loading ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
            </button>
          </form>

          <div className="flex flex-wrap items-center justify-between gap-3 px-1">
            <div className="flex flex-wrap items-center gap-3 opacity-60">
              <div className="flex items-center gap-1.5">
                <div className={`h-1 w-1 rounded-full ${triggerMode === "AUTO" ? "bg-emerald-500" : "bg-amber-500"}`} />
                <span className="text-[8px] font-black uppercase tracking-[0.18em] text-white">{triggerMode} mode</span>
              </div>
              <div className="h-4 w-px bg-white/10" />
              <span className="text-[8px] font-mono uppercase tracking-[0.2em] text-slate-500">
                {selectedTicker ? `Focused on ${selectedTicker}` : "Ready for multi-asset input"}
              </span>
            </div>

            <div className="flex items-center gap-1.5 opacity-40">
              <Globe size={10} />
              <span className="text-[8px] font-bold uppercase tracking-[0.16em]">L-drives active</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
