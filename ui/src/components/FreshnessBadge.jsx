import React from 'react';

export default function FreshnessBadge({ label }) {
  const colors = {
    "Live":      "text-emerald-500 border-emerald-500/20 bg-emerald-500/5",
    "Estimated": "text-indigo-400 border-indigo-500/20 bg-indigo-500/5",
    "Stale":     "text-red-400 border-red-500/20 bg-red-500/5",
  };
  
  const isStale = label?.includes("Cached") || label === "Stale";
  const colorClass = isStale ? colors.Stale : (colors[label] || "text-slate-500 border-white/5 bg-white/[0.02]");

  return (
    <span className={`inline-flex items-center gap-2 px-2 py-0.5 rounded-md text-[8px] font-bold border ${colorClass} uppercase tracking-[0.25em] leading-none`}>
      <div className={`w-1 h-1 rounded-full ${isStale ? "bg-red-500" : "bg-emerald-500"} animate-pulse shadow-[0_0_4px_currentColor]`} />
      {label}
    </span>
  );
}
