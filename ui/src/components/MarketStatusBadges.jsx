import React, { useState, useEffect } from "react";
import { Globe, Timer } from "lucide-react";
import { T } from "../theme";

export default function MarketStatusBadges() {
  const [statuses, setStatuses] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const res = await fetch("http://localhost:8000/api/market/status");
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
          <div key={key} className="flex items-center gap-1.5 px-2 py-0.5 rounded border border-white/5 bg-black/40 min-w-fit">
            <span className="text-[10px] grayscale-[0.5]">{info.emoji}</span>
            <span className="text-[9px] font-black tracking-tighter text-slate-400 uppercase">{key.replace('_', ' ')}</span>
            <div className={`w-1.5 h-1.5 rounded-full ${isOpen ? 'bg-green-500 animate-pulse shadow-[0_0_5px_rgba(34,197,94,0.5)]' : 'bg-slate-700'}`} />
          </div>
        );
      })}
    </div>
  );
}
