import React from 'react';

export default function FreshnessBadge({ label }) {
  const colors = {
    "Live":      "bg-green-900/40 text-green-300 border-green-500/30",
    "Estimated": "bg-purple-900/40 text-purple-300 border-purple-500/30",
    "Stale":     "bg-red-900/40 text-red-300 border-red-500/30",
  };
  
  const isStale = label?.includes("Cached") || label === "Stale";
  const colorClass = isStale ? colors.Stale : (colors[label] || "bg-slate-800 text-gray-400 border-white/10");

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[9px] font-bold border ${colorClass} uppercase tracking-widest`}>
      <span className={`w-1.5 h-1.5 rounded-full ${isStale ? "bg-red-500" : "bg-green-500"} animate-pulse`} />
      {label}
    </span>
  );
}
