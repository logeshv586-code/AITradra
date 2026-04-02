import {
  BarChart2, Newspaper, TrendingUp, ShieldAlert, Brain, Cpu, Layers, Activity, Terminal,
  Crosshair, Shield, Globe2, Microscope, Sparkles
} from "lucide-react";

// ─── AGENTS (V4 Mythic Cognitive Matrix) ─────────────────────────────────────
export const AGENTS = {
  // V3 Intelligence Agents
  datacollector: { name:'DataCollector',      color:'#3b82f6', icon:BarChart2,   acc:99.9, status:'Active',      tasks:2450, desc:'6-Step live OHLCV extraction',        tier:'v3' },
  blobstorage:   { name:'BlobStorageAgent',   color:'#10b981', icon:Layers,       acc:100.0,status:'Active',      tasks:1200, desc:'Daily persistent intelligence',       tier:'v3' },
  marketrag:     { name:'MarketRagAgent',     color:'#6366f1', icon:Brain,        acc:94.2, status:'Active',      tasks:850,  desc:'FAISS semantic market search',        tier:'v3' },
  newsintel:     { name:'NewsIntelAgent',     color:'#a855f7', icon:Newspaper,   acc:88.4, status:'Active',      tasks:1890, desc:'NVIDIA NIM sentiment scoring',       tier:'v3' },
  pricemove:     { name:'PriceMoveAgent',     color:'#00f0ff', icon:TrendingUp,  acc:82.5, status:'Active',      tasks:1560, desc:'6-Step statistical analysis',        tier:'v3' },
  forecast:      { name:'ForecastAgent',      color:'#fbbf24', icon:Activity,    acc:78.1, status:'Active',      tasks:940,  desc:'Technical trend projection',         tier:'v3' },
  explanation:   { name:'ExplainAgent',       color:'#ff2a5f', icon:Cpu,         acc:96.8, status:'Active',      tasks:720,  desc:'NVIDIA Nemotron synthesis',          tier:'v3' },
  think:         { name:'ThinkAgent',         color:'#6366f1', icon:Brain,       acc:94.5, status:'Active',      tasks:1100, desc:'Chain-of-thought reasoner',          tier:'v3' },
  mcpnews:       { name:'McpNewsAgent',       color:'#a855f7', icon:Newspaper,   acc:91.2, status:'Active',      tasks:1450, desc:'Multi-source aggregator',            tier:'v3' },
  batch:         { name:'BatchAgent',         color:'#f6ad55', icon:Activity,    acc:100.0,status:'Standby',     tasks:800,  desc:'Nightly S&P 500 processing',         tier:'v3' },
  uiapi:         { name:'UIApiAgent',         color:'#ffffff', icon:Terminal,    acc:99.9, status:'Active',      tasks:5000, desc:'6-Step orchestration gateway',       tier:'v3' },
  // V4 Mythic-Tier Specialist Fleet
  orchestrator:  { name:'MythicOrchestrator', color:'#e040fb', icon:Sparkles,   acc:97.5, status:'Active',      tasks:3200, desc:'ReAct reasoning loop — parallel specialist dispatch, critique, calibrated synthesis', tier:'v4_mythic' },
  techspec:      { name:'TechnicalSpecialist',color:'#00e5ff', icon:Crosshair,  acc:91.8, status:'Active',      tasks:2100, desc:'OHLCV pattern analysis — support/resistance, momentum, trend detection', tier:'v4_mythic' },
  riskspec:      { name:'RiskSpecialist',     color:'#ff5252', icon:Shield,     acc:93.4, status:'Active',      tasks:1800, desc:'VaR(95%), max drawdown, beta, stress scenario evaluation', tier:'v4_mythic' },
  macrospec:     { name:'MacroSpecialist',    color:'#69f0ae', icon:Globe2,     acc:89.7, status:'Active',      tasks:1600, desc:'News sentiment scoring, earnings signals, sector rotation analysis', tier:'v4_mythic' },
  critique:      { name:'CritiqueAgent',      color:'#ffab40', icon:Microscope, acc:95.2, status:'Active',      tasks:2800, desc:'Self-reflection layer — contradiction detection, confidence calibration (40% agreement + 30% RAG + 30% recency)', tier:'v4_mythic' },
  sentspec:      { name:'SentimentSpecialist',color:'#a855f7', icon:Newspaper,  acc:94.5, status:'Active',      tasks:1400, desc:'Psychology and retail/institutional sentiment evaluation', tier:'v4_mythic' },
  fundaspec:     { name:'FundamentalSpecialist',color:'#f6ad55', icon:BarChart2,acc:96.1, status:'Active',      tasks:1900, desc:'Valuation, earnings quality, and growth prospects', tier:'v4_mythic' },
  sectorspec:    { name:'SectorSpecialist',   color:'#10b981', icon:Layers,     acc:92.4, status:'Active',      tasks:1200, desc:'Relative performance and macro-sector rotation', tier:'v4_mythic' },
  catspec:       { name:'CatalystSpecialist', color:'#ff2a5f', icon:Activity,   acc:90.8, status:'Active',      tasks:1350, desc:'Upcoming events (earnings, FDA, lawsuits, mergers)', tier:'v4_mythic' },
};

export const FLOW_STEPS = ['OBSERVE','THINK','PLAN','ACT','REFLECT','IMPROVE'];
export const MYTHIC_STEPS = ['FAN-OUT','SPECIALISTS','CRITIQUE','CALIBRATE','SYNTHESIZE'];

// ─── CONTINENT POLYGONS (Globe visualization) ─────────────────────────────────
export const CONTINENTS = [
  [[70,-140],[72,-120],[68,-95],[60,-95],[58,-100],[55,-110],[50,-125],[40,-124],[35,-120],[30,-115],[25,-110],[20,-105],[18,-95],[18,-88],[22,-80],[25,-80],[30,-81],[35,-75],[40,-70],[42,-70],[44,-66],[47,-53],[52,-55],[58,-62],[62,-64],[65,-68],[68,-65],[70,-68],[72,-78],[74,-85],[74,-100],[72,-115],[70,-140]],
  [[12,-72],[10,-62],[8,-60],[2,-50],[0,-50],[-5,-35],[-10,-37],[-15,-39],[-20,-40],[-25,-48],[-30,-50],[-35,-57],[-38,-57],[-40,-62],[-42,-65],[-52,-68],[-55,-65],[-55,-68],[-52,-72],[-48,-76],[-45,-74],[-40,-73],[-35,-72],[-30,-70],[-25,-70],[-20,-70],[-18,-70],[-15,-75],[-10,-78],[-5,-80],[0,-80],[5,-77],[10,-75],[12,-72]],
  [[70,30],[68,20],[65,14],[60,5],[58,5],[56,8],[54,8],[52,4],[50,2],[48,0],[46,2],[44,8],[42,12],[40,18],[38,16],[36,14],[36,28],[38,36],[40,36],[42,28],[44,28],[46,24],[48,22],[52,22],[54,20],[56,22],[58,28],[62,28],[64,26],[66,28],[70,30]],
  [[36,10],[32,12],[28,12],[22,15],[15,18],[10,15],[5,2],[0,10],[-5,12],[-10,14],[-15,12],[-20,12],[-25,15],[-30,17],[-35,20],[-34,26],[-30,30],[-25,33],[-20,35],[-15,38],[-10,40],[-5,40],[0,42],[5,42],[10,42],[15,42],[20,38],[25,35],[30,32],[35,32],[36,22],[36,10]],
  [[70,30],[68,30],[65,40],[60,45],[55,50],[50,60],[45,60],[40,55],[38,58],[36,44],[36,36],[30,32],[22,40],[14,44],[12,48],[10,44],[10,52],[14,52],[18,56],[22,60],[26,56],[30,60],[35,62],[40,68],[42,78],[40,85],[38,88],[36,100],[26,100],[22,110],[18,110],[14,108],[10,105],[8,110],[12,110],[16,112],[20,110],[24,120],[28,120],[32,118],[38,120],[42,122],[46,135],[50,142],[52,142],[55,140],[58,130],[62,128],[66,130],[70,110],[72,100],[72,80],[70,70],[68,50],[70,30]],
  [[-18,122],[-14,126],[-12,130],[-12,136],[-16,136],[-18,140],[-20,148],[-25,152],[-30,153],[-35,150],[-38,146],[-38,140],[-34,136],[-32,134],[-32,130],[-28,126],[-22,114],[-18,122]]
];

// ─── UTILITIES ────────────────────────────────────────────────────────────────
export const computeMA = (data, period) => {
  return data.map((_, i) => {
    if (i < period - 1) return null;
    const slice = data.slice(i - period + 1, i + 1);
    return slice.reduce((sum, d) => sum + d.c, 0) / period;
  });
};
