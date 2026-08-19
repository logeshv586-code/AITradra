import React, { useState } from "react";
import { Search, Send, Loader2 } from "lucide-react";

export default function AskBar({ onAsk }) {
  const [query, setQuery] = useState("");
  const [sending, setSending] = useState(false);

  const submit = async (event) => {
    event?.preventDefault();
    const text = query.trim();
    if (!text || sending || !onAsk) return;

    setSending(true);
    try {
      await onAsk(text);
      setQuery("");
    } finally {
      setSending(false);
    }
  };

  return (
    <form onSubmit={submit} className="relative w-full max-w-2xl mx-auto">
      <div className="relative flex items-center bg-[#13171f] border border-white/[0.08] rounded-xl overflow-hidden focus-within:border-indigo-500/50 transition-all shadow-lg">
        <div className="pl-4 text-slate-500">
          {sending ? (
            <Loader2 size={17} className="animate-spin text-indigo-400" />
          ) : (
            <Search size={17} />
          )}
        </div>
        <input
          type="text"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          disabled={sending}
          placeholder="Ask about a stock, crypto, or today’s market…"
          aria-label="Ask AITradra"
          className="flex-1 bg-transparent border-none outline-none py-3 px-4 text-[13px] text-white placeholder-slate-600 font-medium disabled:opacity-60"
        />
        <div className="pr-2">
          <button
            type="submit"
            disabled={!query.trim() || sending}
            aria-label="Send question"
            className={`h-8 w-8 flex items-center justify-center rounded-lg transition-all ${
              query.trim() && !sending
                ? "bg-indigo-600 text-white hover:bg-indigo-500"
                : "text-slate-700 bg-white/[0.02]"
            }`}
          >
            {sending ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
          </button>
        </div>
      </div>
    </form>
  );
}
