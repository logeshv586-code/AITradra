import React, { useState, useEffect } from 'react';
import { Activity, Shield, Zap, Database, Terminal, Cpu, Share2 } from 'lucide-react';

const DependencyGraph = () => {
    const [graph, setGraph] = useState({ nodes: [], links: [] });
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        // Mocking or fetching actual graph data
        const fetchData = async () => {
            try {
                const res = await fetch('/api/mission/graph');
                const data = await res.json();
                setGraph(data);
            } catch (err) {
                console.error("Loading graph failed:", err);
                // Fallback for demo
                setGraph({
                    nodes: [
                        { id: 'Orchestrator', type: 'core' },
                        { id: 'Technical', type: 'specialist' },
                        { id: 'Risk', type: 'specialist' }
                    ],
                    links: [
                        { source: 'Orchestrator', target: 'Technical' },
                        { source: 'Orchestrator', target: 'Risk' }
                    ]
                });
            } finally {
                setLoading(false);
            }
        };
        fetchData();
    }, []);

    if (loading) return (
        <div className="flex h-full items-center justify-center gap-3">
           <div className="w-1.5 h-1.5 rounded-full bg-indigo-500 animate-pulse" />
           <span className="text-[10px] font-mono text-slate-500 uppercase tracking-widest">Mapping Intelligence Convoy...</span>
        </div>
    );

    const COL_UP = "var(--accent-positive)";
    const COL_INDIGO = "var(--accent-indigo)";
    const COL_TEXT = "#94a3b8";

    return (
        <div className="glass-card p-6 h-[420px] flex flex-col gap-6 border border-white/[0.08] bg-white/[0.01]">
            <div className="flex justify-between items-center border-b border-white/[0.08] pb-4">
                <div className="flex items-center gap-3">
                   <Share2 size={16} className="text-indigo-400" />
                   <h3 className="text-[11px] font-bold tracking-[0.2em] uppercase text-white leading-none">Nexus Dependency Topology</h3>
                </div>
                <div className="flex gap-4">
                    <div className="flex items-center gap-2 text-[9px] font-bold text-slate-500 uppercase tracking-widest">
                       <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse shadow-[0_0_4px_var(--accent-positive)]"/> ACTIVE_MODE
                    </div>
                    <div className="flex items-center gap-2 text-[9px] font-bold text-slate-700 uppercase tracking-widest">
                       <div className="w-1.5 h-1.5 rounded-full bg-slate-800"/> STANDBY
                    </div>
                </div>
            </div>
            
            <div className="flex-1 relative border border-white/[0.06] rounded-xl bg-black/40 overflow-hidden shadow-inner">
                {/* Precision SVG Visualizer */}
                <svg width="100%" height="100%" viewBox="0 0 400 300" className="opacity-90">
                    <defs>
                        <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="2" refY="3.5" orient="auto">
                            <polygon points="0 0, 10 3.5, 0 7" fill="rgba(99,102,241,0.4)" />
                        </marker>
                        <radialGradient id="nodeGlow" cx="50%" cy="50%" r="50%">
                            <stop offset="0%" stopColor="var(--accent-indigo)" stopOpacity={0.2} />
                            <stop offset="100%" stopColor="var(--accent-indigo)" stopOpacity={0} />
                        </radialGradient>
                    </defs>
                    
                    {/* Synchronized Links */}
                    {graph.links.map((link, i) => {
                        // Coordinates based on static topology
                        const sx = 200, sy = 70; // Root node
                        const tx = link.target === 'Technical' ? 120 : 280;
                        const ty = 200;
                        
                        return (
                            <g key={i}>
                                <line 
                                    x1={sx} y1={sy} x2={tx} y2={ty}
                                    stroke="var(--accent-indigo)"
                                    strokeWidth="1"
                                    strokeOpacity="0.15"
                                    strokeDasharray="4,4"
                                />
                                <circle r="3" fill="var(--accent-indigo)" opacity="0.4">
                                    <animateMotion 
                                        dur="2s" 
                                        repeatCount="indefinite" 
                                        path={`M${sx},${sy} L${tx},${ty}`} 
                                    />
                                </circle>
                            </g>
                        );
                    })}

                    {/* Node: Orchestrator (Top) */}
                    <g transform="translate(200, 70)">
                        <circle r="35" fill="url(#nodeGlow)" />
                        <circle r="22" className="fill-indigo-500/10 stroke-indigo-500/40" strokeWidth="1" />
                        <foreignObject x="-9" y="-9" width="18" height="18">
                            <Cpu size={18} className="text-indigo-400" />
                        </foreignObject>
                        <text y="42" textAnchor="middle" className="fill-slate-400 text-[9px] font-bold uppercase tracking-widest">Orchestrator</text>
                    </g>

                    {/* Node: Technical (Left) */}
                    <g transform="translate(120, 200)">
                        <circle r="18" className="fill-slate-900 stroke-slate-800" strokeWidth="1" />
                        <foreignObject x="-8" y="-8" width="16" height="16">
                            <Zap size={16} className="text-slate-600" />
                        </foreignObject>
                        <text y="35" textAnchor="middle" className="fill-slate-600 text-[8px] font-bold uppercase tracking-widest font-mono">Specialist_Tech</text>
                    </g>

                    {/* Node: Risk (Right) */}
                    <g transform="translate(280, 200)">
                        <circle r="18" className="fill-emerald-500/5 stroke-emerald-500/30" strokeWidth="1" />
                        <foreignObject x="-8" y="-8" width="16" height="16">
                            <Shield size={16} className="text-emerald-500" />
                        </foreignObject>
                        <text y="35" textAnchor="middle" className="fill-slate-400 text-[8px] font-bold uppercase tracking-widest font-mono">Specialist_Risk</text>
                    </g>
                </svg>

                {/* Global Grid Overlay (Subtle) */}
                <div className="absolute inset-0 pointer-events-none opacity-[0.03]" 
                    style={{ backgroundImage: 'radial-gradient(var(--accent-indigo) 0.5px, transparent 0.5px)', backgroundSize: '16px 16px' }} />
            </div>
        </div>
    );
};

export default DependencyGraph;
