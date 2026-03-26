import {
  BarChart2, Newspaper, TrendingUp, ShieldAlert, Brain, Cpu
} from "lucide-react";

// ─── AGENTS ───────────────────────────────────────────────────────────────────
export const AGENTS = {
  data:      { name:'DataAgent',      color:'#3b82f6', icon:BarChart2,   acc:99.9, status:'Active',      tasks:1420, desc:'OHLCV + fundamentals ingestion' },
  news:      { name:'NewsAgent',      color:'#a855f7', icon:Newspaper,   acc:84.2, status:'Learning',    tasks:890,  desc:'RSS + sentiment classification' },
  trend:     { name:'TrendAgent',     color:'#00f0ff', icon:TrendingUp,  acc:78.5, status:'Active',      tasks:1105, desc:'RSI, MACD, Bollinger signals' },
  risk:      { name:'RiskAgent',      color:'#fbbf24', icon:ShieldAlert, acc:92.1, status:'Active',      tasks:650,  desc:'VaR, Beta, drawdown analysis' },
  ml:        { name:'MLAgent',        color:'#ff2a5f', icon:Brain,       acc:68.4, status:'Retraining',  tasks:430,  desc:'LSTM + XGBoost ensemble' },
  synthesis: { name:'SynthesisAgent', color:'#6366f1', icon:Cpu,         acc:88.8, status:'Active',      tasks:920,  desc:'LLM chain-of-thought synthesis' },
};

export const FLOW_STEPS = ['OBSERVE','THINK','PLAN','ACT','REFLECT','IMPROVE'];

// ─── MOCK DATA GENERATION ─────────────────────────────────────────────────────
const genOHLCV = (start, days, drift) => {
  let p = start;
  return Array.from({length: days+1}, (_, i) => {
    const vol = p * 0.022;
    const o = p + (Math.random()-.5)*vol;
    const c = o + (Math.random()-.5+drift)*vol;
    const h = Math.max(o,c) + Math.random()*vol*.6;
    const l = Math.min(o,c) - Math.random()*vol*.6;
    const v = Math.floor((50+Math.random()*80)*1e6);
    p = c;
    return { t: i-days, o, h, l, c, v };
  });
};

export const STOCKS = [
  { id:'NVDA', name:'NVIDIA Corp.',    ex:'NASDAQ', px:892.50, chg:4.8,  mcap:'$2.2T', vol:'41M', pe:'62.1', sector:'Chips',   lat: 37.3, lon:-121.9, ohlcv:genOHLCV(800,60,0.10), risk:{var:'4.2%',beta:1.8,vol:'High'} },
  { id:'AAPL', name:'Apple Inc.',      ex:'NASDAQ', px:178.42, chg:2.3,  mcap:'$2.8T', vol:'48M', pe:'28.4', sector:'Tech',    lat: 37.3, lon:-122.1, ohlcv:genOHLCV(160,60,0.05), risk:{var:'1.8%',beta:1.1,vol:'Low'} },
  { id:'TSLA', name:'Tesla Inc.',      ex:'NASDAQ', px:182.30, chg:-1.8, mcap:'$580B', vol:'85M', pe:'45.2', sector:'EV',      lat: 30.3, lon: -97.7, ohlcv:genOHLCV(200,60,-0.05),risk:{var:'5.1%',beta:2.2,vol:'High'} },
  { id:'BABA', name:'Alibaba Group',   ex:'HKEx',   px:78.40,  chg:1.4,  mcap:'$190B', vol:'30M', pe:'10.2', sector:'E-Com',   lat: 30.3, lon: 120.2, ohlcv:genOHLCV(70,60,0.02),  risk:{var:'3.5%',beta:1.4,vol:'Med'} },
  { id:'SAP',  name:'SAP SE',          ex:'FSX',    px:188.40, chg:1.2,  mcap:'$230B', vol:'4M',  pe:'40.1', sector:'Software',lat: 49.3, lon:   8.6, ohlcv:genOHLCV(175,60,0.08), risk:{var:'2.1%',beta:0.9,vol:'Low'} },
  { id:'BHP',  name:'BHP Group',       ex:'ASX',    px:44.20,  chg:-0.5, mcap:'$120B', vol:'6M',  pe:'12.8', sector:'Mining',  lat:-37.8, lon: 144.9, ohlcv:genOHLCV(46,60,-0.02), risk:{var:'2.8%',beta:1.0,vol:'Med'} },
];

export const NEWS = {
  NVDA:[
    {src:'Reuters',  t:'2h',  txt:'Nvidia Blackwell chips demand far exceeds supply forecasts.', s:0.85},
    {src:'Bloomberg',t:'5h',  txt:'Data center AI capex cycle showing no signs of slowdown.',    s:0.72},
    {src:'FT',       t:'8h',  txt:'TSMC increases CoWoS packaging capacity for Nvidia orders.', s:0.64},
  ],
  TSLA:[
    {src:'WSJ',  t:'1h',  txt:'Tesla Q1 deliveries expected to miss consensus by 8–12%.', s:-0.78},
    {src:'CNBC', t:'3h',  txt:'EV pricing pressure intensifies across US and Europe.',     s:-0.55},
  ],
  AAPL:[
    {src:'Bloomberg',t:'4h', txt:'Apple Intelligence rollout accelerates in key markets.',  s:0.62},
    {src:'Reuters',  t:'9h', txt:'Services segment on track to hit $100B annual revenue.', s:0.58},
  ],
};

export const PORTFOLIO = [
  { id:'NVDA', qty:12,  avg:810.00, px:892.50, weight:31.2 },
  { id:'AAPL', qty:55,  avg:165.20, px:178.42, weight:28.7 },
  { id:'SAP',  qty:20,  avg:175.00, px:188.40, weight:11.0 },
  { id:'BABA', qty:100, avg:72.00,  px:78.40,  weight:22.8 },
  { id:'BHP',  qty:80,  avg:47.00,  px:44.20,  weight:6.3  },
];

export const MEMORIES = {
  episodic:[
    { id:1, ticker:'NVDA', pred:'BUY', target:850, actual:892.5, acc:'94%', ago:'12d', note:'LSTM breakout signal accurate. Added to training set.' },
    { id:2, ticker:'TSLA', pred:'SELL',target:180, actual:182.3, acc:'71%', ago:'28d', note:'Overestimated support. Sentiment lagged by 6h.' },
  ],
  semantic:[
    { id:1, type:'pattern', title:'AI Chip Breakout Pattern',     sims:12, conf:87, ago:'3d'  },
    { id:2, type:'news',    title:'EV Demand Shock Correlation',  sims:8,  conf:79, ago:'7d'  },
  ],
  working: [
    { agent:'DataAgent',      key:'NVDA_60D_OHLCV',  size:'128KB',  ttl:'5m'  },
    { agent:'SynthesisAgent', key:'NVDA_COT_DRAFT',  size:'8KB',    ttl:'2m'  },
  ],
};

export const INSIGHTS = [
  { id:1, agent:'SynthesisAgent', ticker:'NVDA', type:'BULLISH', conf:88, title:'AI Capex Supercycle Intact',  body:'Data center spending from hyperscalers shows no deceleration signal. NVDA positioned as primary beneficiary.', ts:'3m ago', tags:['Macro','Sector'] },
  { id:2, agent:'MLAgent',        ticker:'TSLA', type:'BEARISH', conf:74, title:'Delivery Miss Pre-Signaled',  body:'LSTM model detected negative divergence in production proxy signals 14 days ago. Now confirming.', ts:'18m ago', tags:['ML','Pattern'] },
];

export const SYSTEM_HEALTH = [
  { name:'DataAgent',      uptime:'99.98%', latency:'180ms', cpu:'12%', calls:14200 },
  { name:'NewsAgent',      uptime:'97.40%', latency:'890ms', cpu:'28%', calls:4410  },
  { name:'MLAgent',        uptime:'94.20%', latency:'2100ms',cpu:'62%', calls:3200  },
  { name:'SynthesisAgent', uptime:'99.70%', latency:'3400ms',cpu:'44%', calls:5800  },
];

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
