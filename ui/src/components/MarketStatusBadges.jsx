import React, { useState, useEffect } from "react";
import { API_BASE } from "../api_config";

export default function MarketStatusBadges() {
  const [statuses, setStatuses] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/market/status`);
        const data = await res.json();
        setStatuses(data);
        setLoading(false);
      } catch (err) {
        console.error("Failed to fetch market status:", err);
      }
    };

    fetchStatus();
    const id = setInterval(fetchStatus, 60000); // Update every minute
    return () => clearInterval(id);
  }, []);

  if (loading || !statuses) return null;

  return (
    <div className="flex items-center gap-3 px-4 overflow-x-auto no-scrollbar max-w-[500px]">
      {Object.entries(statuses).map(([key, info]) => {
        const isOpen = info.status === "OPEN";
        return (
          <div key={key} className="flex items-center gap-2 px-3 py-0.5 rounded-md border border-white/[0.06] bg-white/[0.02] min-w-fit transition-all duration-120 hover:bg-white/[0.04]">
            <span className="text-[11px] grayscale-[0.2]">{info.emoji}</span>
            <span className="text-[9px] font-bold tracking-tight text-slate-500 uppercase">{key.replace('_', ' ')}</span>
            <div className={`w-1 h-1 rounded-full ${isOpen ? 'bg-emerald-500 animate-pulse shadow-[0_0_5px_rgba(52,211,153,0.5)]' : 'bg-slate-800'}`} />
          </div>
        );
      })}
    </div>
  );
}
