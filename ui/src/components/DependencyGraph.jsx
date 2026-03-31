import React, { useState, useEffect } from 'react';
import { Activity, Shield, Zap, Database, Terminal } from 'lucide-react';

const DependencyGraph = () => {
    const [graph, setGraph] = useState({ nodes: [], links: [] });
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetch('/api/mission/graph')
            .then(res => res.json())
            .then(data => {
                setGraph(data);
                setLoading(false);
            })
            .catch(err => console.error("Loading graph failed:", err));
    }, []);

    if (loading) return <div className="text-xs font-mono text-indigo-400 animate-pulse">Syncing Convoy Graph...</div>;

    const getIcon = (id) => {
        if (id.includes('Orchestrator')) return <Activity size={14} />;
        if (id.includes('Risk')) return <Shield size={14} />;
        if (id.includes('Technical')) return <Zap size={14} />;
        if (id.includes('Analyst')) return <Terminal size={14} />;
        return <Database size={14} />;
    };

    return (
        <div className="clay-card p-6 h-[400px] flex flex-col">
            <div className="flex justify-between items-center mb-4">
                <h3 className="text-xs font-bold tracking-widest uppercase text-indigo-300">Convoy Dependency Graph</h3>
                <div className="flex gap-2">
                    <span className="flex items-center gap-1 text-[10px] text-emerald-400"><div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"/> ACTIVE</span>
                    <span className="flex items-center gap-1 text-[10px] text-amber-400"><div className="w-1.5 h-1.5 rounded-full bg-amber-400"/> WAITING</span>
                </div>
            </div>
            
            <div className="flex-1 relative border border-white/5 rounded-xl bg-black/20 overflow-hidden">
                {/* Simple SVG Visualizer */}
                <svg width="100%" height="100%" viewBox="0 0 400 300">
                    <defs>
                        <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="0" refY="3.5" orient="auto">
                            <polygon points="0 0, 10 3.5, 0 7" fill="rgba(99,102,241,0.3)" />
                        </marker>
                    </defs>
                    
                    {/* Links */}
                    {graph.links.map((link, i) => {
                        const source = graph.nodes.find(n => n.id === link.source);
                        const target = graph.nodes.find(n => n.id === link.target);
                        if (!source || !target) return null;
                        
                        // Fake positions for simple layout
                        const sx = 200; const sy = 50; // Orchestrator
                        const tx = link.target.includes('Specialist') ? 100 : 300;
                        const ty = 150;
                        
                        return (
                            <line 
                                key={i}
                                x1={sx} y1={sy} x2={tx} y2={ty}
                                stroke="rgba(99,102,241,0.2)"
                                strokeWidth="1"
                                className="animate-flow-line"
                            />
                        );
                    })}

                    {/* Nodes */}
                    <g transform="translate(200, 50)">
                        <circle r="20" className="fill-indigo-500/20 stroke-indigo-400/50" />
                        <foreignObject x="-7" y="-7" width="14" height="14">
                            <Activity size={14} className="text-indigo-400" />
                        </foreignObject>
                        <text y="35" textAnchor="middle" className="fill-slate-300 text-[10px] font-mono">Orchestrator</text>
                    </g>

                    <g transform="translate(100, 150)">
                        <circle r="18" className="fill-slate-800 stroke-slate-700" />
                        <foreignObject x="-7" y="-7" width="14" height="14">
                            <Zap size={14} className="text-slate-400" />
                        </foreignObject>
                        <text y="35" textAnchor="middle" className="fill-slate-400 text-[10px] font-mono">Technical</text>
                    </g>

                    <g transform="translate(300, 150)">
                        <circle r="18" className="fill-emerald-500/10 stroke-emerald-400/50" />
                        <foreignObject x="-7" y="-7" width="14" height="14">
                            <Shield size={14} className="text-emerald-400" />
                        </foreignObject>
                        <text y="35" textAnchor="middle" className="fill-slate-300 text-[10px] font-mono">RiskManager</text>
                    </g>
                </svg>
            </div>
        </div>
    );
};

export default DependencyGraph;
