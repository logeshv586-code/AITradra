import React, { useState, useRef, useEffect } from "react";
import {
  Send,
  Loader2,
  Bot,
  User,
  ShieldAlert,
  Sparkles,
  Newspaper,
  Activity,
  ShieldCheck,
} from "lucide-react";
import ReactMarkdown from "react-markdown";

const STARTER_QUESTIONS = [
  "What is moving the market today?",
  "Is NVDA worth watching right now?",
  "Explain AAPL’s recent move in simple terms",
  "What are the main risks in BTC?",
];

export default function ChatPanel({
  messages = [],
  onSend,
  fullView = false,
  intelligenceStatus = null,
}) {
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [localError, setLocalError] = useState("");
  const endRef = useRef(null);

  const knowledgeReady =
    intelligenceStatus?.knowledge || intelligenceStatus?.model_router;

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const handleSubmit = async (event) => {
    event?.preventDefault();
    const text = input.trim();
    if (!text || loading || !onSend) return;

    setInput("");
    setLocalError("");
    setLoading(true);
    try {
      await onSend(text);
    } catch (error) {
      setLocalError(
        error?.message || "AITradra could not answer that question. Please try again."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className={`flex flex-col ${
        fullView
          ? "h-[calc(100vh-140px)] w-full max-w-5xl mx-auto py-6 px-4"
          : "h-full w-full"
      }`}
    >
      <div
        className={`flex-1 overflow-y-auto no-scrollbar p-5 flex flex-col gap-6 ${
          fullView
            ? "bg-[var(--card-bg)] border border-[var(--border-color)] rounded-t-[var(--radius-lg)] shadow-sm"
            : ""
        }`}
      >
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center text-center mt-8 animate-fade-in px-4">
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-[#1e232b] border border-[var(--border-color)] mb-5 shadow-sm">
              <Sparkles size={28} className="text-[var(--accent)]" />
            </div>
            <h3 className="heading-2 text-white">Ask AITradra</h3>
            <p className="mt-3 text-[13px] text-[var(--text-muted)] max-w-[520px] leading-relaxed">
              Ask in plain English. AITradra can explain a stock or crypto move,
              compare opportunities, summarize market news, identify risks, and
              show the evidence behind an answer.
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-7 w-full max-w-2xl">
              {STARTER_QUESTIONS.map((question) => (
                <button
                  key={question}
                  onClick={() => setInput(question)}
                  className="px-4 py-3 rounded-[var(--radius-md)] bg-[#1e232b] border border-[var(--border-color)] text-left text-[12px] text-[var(--text-muted)] hover:border-[var(--accent)] hover:text-white transition-all"
                >
                  {question}
                </button>
              ))}
            </div>

            <div className="mt-7 flex items-start gap-2 max-w-xl rounded-[var(--radius-md)] border border-[var(--border-color)] bg-black/20 px-4 py-3 text-left">
              <ShieldCheck size={15} className="text-[var(--positive)] mt-0.5 shrink-0" />
              <p className="text-[11px] leading-relaxed text-[var(--text-muted)]">
                Answers use current market context when available and separate a
                possible setup from certainty. No AI answer can guarantee a profit.
              </p>
            </div>
          </div>
        )}

        {messages.map((message, index) => {
          const isUser = message.role === "user";
          return (
            <div
              key={`${message.role}-${index}`}
              className={`flex gap-3 animate-fade-in ${
                isUser ? "flex-row-reverse" : "flex-row"
              }`}
            >
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

              <div
                className={`flex flex-col max-w-[88%] ${
                  isUser ? "items-end" : "items-start"
                }`}
              >
                <div
                  className={`px-4 py-3 rounded-[var(--radius-lg)] text-[13px] leading-relaxed shadow-sm ${
                    isUser
                      ? "bg-[var(--accent)] border border-[var(--accent-hover)] text-white"
                      : "bg-[#1e232b] border border-[var(--border-color)] text-[var(--text-main)] prose prose-invert prose-sm max-w-none min-w-[220px] prose-p:leading-relaxed prose-pre:bg-[var(--app-bg)] prose-pre:border prose-pre:border-[var(--border-color)] prose-headings:text-white prose-a:text-[var(--accent)]"
                  }`}
                >
                  {isUser ? (
                    <span>{message.text}</span>
                  ) : (
                    <ReactMarkdown>{message.text || "No answer was returned."}</ReactMarkdown>
                  )}
                </div>

                {!isUser && message.meta?.error && (
                  <div className="flex items-center gap-1.5 mt-2 text-[10px] text-[var(--negative)]">
                    <ShieldAlert size={12} /> {message.meta.error}
                  </div>
                )}

                {!isUser &&
                  (message.priceData ||
                    message.sources?.length > 0 ||
                    message.meta?.contextTicker ||
                    message.meta?.confidence !== undefined) && (
                    <div className="mt-2 flex flex-wrap items-center gap-2 text-[10px] text-[var(--text-muted)]">
                      {message.meta?.contextTicker && (
                        <span className="surface-badge flex items-center gap-1">
                          <Activity size={10} />
                          {message.meta.contextTicker}
                        </span>
                      )}
                      {message.priceData?.source_used && (
                        <span className="surface-badge">
                          Price: {message.priceData.source_used}
                        </span>
                      )}
                      {message.meta?.confidence !== undefined &&
                        message.meta?.confidence !== null &&
                        Number.isFinite(Number(message.meta.confidence)) && (
                          <span className="surface-badge">
                            {Number(message.meta.confidence).toFixed(0)}% confidence
                          </span>
                        )}
                      {(message.sources || []).slice(0, 3).map((source, sourceIndex) => {
                        const headline =
                          source.headline ||
                          source.title ||
                          source.url ||
                          `Evidence ${sourceIndex + 1}`;
                        const body = (
                          <>
                            <Newspaper size={10} />
                            <span className="max-w-[240px] truncate">{headline}</span>
                          </>
                        );
                        return source.url ? (
                          <a
                            key={`${headline}-${sourceIndex}`}
                            href={source.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="surface-badge flex items-center gap-1 hover:text-white"
                          >
                            {body}
                          </a>
                        ) : (
                          <span
                            key={`${headline}-${sourceIndex}`}
                            className="surface-badge flex items-center gap-1"
                          >
                            {body}
                          </span>
                        );
                      })}
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
            <div className="px-4 py-3 rounded-[var(--radius-lg)] bg-[#1e232b] border border-[var(--border-color)] flex items-center gap-2">
              <Loader2 size={15} className="text-[var(--accent)] animate-spin" />
              <span className="text-[12px] text-[var(--text-muted)]">
                Checking market data, signals, risks and evidence…
              </span>
            </div>
          </div>
        )}

        {localError && (
          <div className="flex items-center gap-2 text-[12px] text-[var(--negative)] bg-[#ef444410] border border-[#ef444430] rounded-[var(--radius-md)] px-3 py-2">
            <ShieldAlert size={14} /> {localError}
          </div>
        )}
        <div ref={endRef} />
      </div>

      <div
        className={`p-4 border-t border-[var(--border-color)] bg-[var(--app-bg)] ${
          fullView
            ? "bg-[var(--card-bg)] border border-[var(--border-color)] border-t-0 rounded-b-[var(--radius-lg)] shadow-sm"
            : ""
        }`}
      >
        <form onSubmit={handleSubmit} className="relative flex items-center">
          <input
            type="text"
            value={input}
            onChange={(event) => setInput(event.target.value)}
            disabled={loading}
            placeholder="Ask a market question in plain English…"
            aria-label="Chat with AITradra"
            className="w-full bg-[#1e232b] border border-[var(--border-color)] rounded-[var(--radius-lg)] pl-4 pr-12 py-3 text-[13px] text-white focus:outline-none focus:border-[var(--accent)] transition-colors shadow-sm disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={!input.trim() || loading}
            aria-label="Send message"
            className="absolute right-2 top-1/2 -translate-y-1/2 h-8 w-8 flex items-center justify-center rounded-[var(--radius-md)] bg-[var(--accent)] text-white hover:bg-[var(--accent-hover)] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Send size={14} />
          </button>
        </form>
        <div className="mt-3 flex items-center justify-center gap-2">
          <span className="text-[10px] text-[var(--text-muted)]">
            {knowledgeReady ? "Market intelligence connected" : "Market intelligence loading"}
            {" • "}Review evidence and risk before acting
          </span>
        </div>
      </div>
    </div>
  );
}
