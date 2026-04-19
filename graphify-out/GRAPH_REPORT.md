# Graph Report - E:\AITradra  (2026-04-19)

## Corpus Check
- 195 files · ~123,368 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1970 nodes · 6389 edges · 111 communities detected
- Extraction: 39% EXTRACTED · 61% INFERRED · 0% AMBIGUOUS · INFERRED: 3929 edges (avg confidence: 0.58)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 22|Community 22]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 36|Community 36]]
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Community 39|Community 39]]
- [[_COMMUNITY_Community 40|Community 40]]
- [[_COMMUNITY_Community 41|Community 41]]
- [[_COMMUNITY_Community 42|Community 42]]
- [[_COMMUNITY_Community 43|Community 43]]
- [[_COMMUNITY_Community 44|Community 44]]
- [[_COMMUNITY_Community 45|Community 45]]
- [[_COMMUNITY_Community 46|Community 46]]
- [[_COMMUNITY_Community 47|Community 47]]
- [[_COMMUNITY_Community 48|Community 48]]
- [[_COMMUNITY_Community 49|Community 49]]
- [[_COMMUNITY_Community 50|Community 50]]
- [[_COMMUNITY_Community 51|Community 51]]
- [[_COMMUNITY_Community 52|Community 52]]
- [[_COMMUNITY_Community 53|Community 53]]
- [[_COMMUNITY_Community 54|Community 54]]
- [[_COMMUNITY_Community 55|Community 55]]
- [[_COMMUNITY_Community 56|Community 56]]
- [[_COMMUNITY_Community 57|Community 57]]
- [[_COMMUNITY_Community 58|Community 58]]
- [[_COMMUNITY_Community 59|Community 59]]
- [[_COMMUNITY_Community 60|Community 60]]
- [[_COMMUNITY_Community 61|Community 61]]
- [[_COMMUNITY_Community 62|Community 62]]
- [[_COMMUNITY_Community 63|Community 63]]
- [[_COMMUNITY_Community 64|Community 64]]
- [[_COMMUNITY_Community 65|Community 65]]
- [[_COMMUNITY_Community 66|Community 66]]
- [[_COMMUNITY_Community 67|Community 67]]
- [[_COMMUNITY_Community 68|Community 68]]
- [[_COMMUNITY_Community 69|Community 69]]
- [[_COMMUNITY_Community 70|Community 70]]
- [[_COMMUNITY_Community 71|Community 71]]
- [[_COMMUNITY_Community 72|Community 72]]
- [[_COMMUNITY_Community 73|Community 73]]
- [[_COMMUNITY_Community 74|Community 74]]
- [[_COMMUNITY_Community 75|Community 75]]
- [[_COMMUNITY_Community 76|Community 76]]
- [[_COMMUNITY_Community 77|Community 77]]
- [[_COMMUNITY_Community 78|Community 78]]
- [[_COMMUNITY_Community 79|Community 79]]
- [[_COMMUNITY_Community 80|Community 80]]
- [[_COMMUNITY_Community 81|Community 81]]
- [[_COMMUNITY_Community 82|Community 82]]
- [[_COMMUNITY_Community 83|Community 83]]
- [[_COMMUNITY_Community 84|Community 84]]
- [[_COMMUNITY_Community 85|Community 85]]
- [[_COMMUNITY_Community 86|Community 86]]
- [[_COMMUNITY_Community 87|Community 87]]
- [[_COMMUNITY_Community 88|Community 88]]
- [[_COMMUNITY_Community 89|Community 89]]
- [[_COMMUNITY_Community 90|Community 90]]
- [[_COMMUNITY_Community 91|Community 91]]
- [[_COMMUNITY_Community 92|Community 92]]
- [[_COMMUNITY_Community 93|Community 93]]
- [[_COMMUNITY_Community 94|Community 94]]
- [[_COMMUNITY_Community 95|Community 95]]
- [[_COMMUNITY_Community 96|Community 96]]
- [[_COMMUNITY_Community 97|Community 97]]
- [[_COMMUNITY_Community 98|Community 98]]
- [[_COMMUNITY_Community 99|Community 99]]
- [[_COMMUNITY_Community 100|Community 100]]
- [[_COMMUNITY_Community 101|Community 101]]
- [[_COMMUNITY_Community 102|Community 102]]
- [[_COMMUNITY_Community 103|Community 103]]
- [[_COMMUNITY_Community 104|Community 104]]
- [[_COMMUNITY_Community 105|Community 105]]
- [[_COMMUNITY_Community 106|Community 106]]
- [[_COMMUNITY_Community 107|Community 107]]
- [[_COMMUNITY_Community 108|Community 108]]
- [[_COMMUNITY_Community 109|Community 109]]
- [[_COMMUNITY_Community 110|Community 110]]

## God Nodes (most connected - your core abstractions)
1. `AgentContext` - 362 edges
2. `BaseAgent` - 202 edges
3. `RagAgent` - 135 edges
4. `LLMClient` - 111 edges
5. `McpNewsAgent` - 97 edges
6. `BlobAgent` - 86 edges
7. `ThinkAgent` - 85 edges
8. `AgentOrchestrator` - 73 edges
9. `SelfImprovementEngine` - 73 edges
10. `BatchAgent` - 72 edges

## Surprising Connections (you probably didn't know these)
- `Run a single agent through the Claude Flow loop and update the shared state.` --uses--> `AgentContext`  [INFERRED]
  E:\AITradra\agents\legacy\orchestrator\graph.py → E:\AITradra\agents\legacy\base_agent.py
- `Execute the full 14-agent LangGraph V2 pipeline.` --uses--> `AgentContext`  [INFERRED]
  E:\AITradra\agents\legacy\orchestrator\graph.py → E:\AITradra\agents\legacy\base_agent.py
- `Sentiment Engine — LLM-powered multi-ticker news analysis.  Reads scraped news` --uses--> `LLMClient`  [INFERRED]
  E:\AITradra\agents\sentiment_engine.py → E:\AITradra\llm\client.py
- `Runs LLM comparison on scraped news for the given tickers.` --uses--> `LLMClient`  [INFERRED]
  E:\AITradra\agents\sentiment_engine.py → E:\AITradra\llm\client.py
- `Converts the JSON result into a styled Markdown response suitable for ChatPanel.` --uses--> `LLMClient`  [INFERRED]
  E:\AITradra\agents\sentiment_engine.py → E:\AITradra\llm\client.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.01
Nodes (151): Broadcast alert to all configured channels., Return model routing metadata without exposing secrets., DataEngine, AXIOM Data Engine — Real Market Data from Knowledge Store + Multi-Source Collect, Hidden background fetch to warm the cache for a specific ticker., Deduplicated news from knowledge store + RSS + Web., Background news crawl., Aggregates everything for LLM reasoning. (+143 more)

### Community 1 - "Community 1"
Cohesion: 0.02
Nodes (166): AccuracyStoreAgent, get_agent(), AccuracyStore — SQLite-backed aggregate accuracy persistence.  Tracks rolling, Agent 27: Self-Correction Supervisor     Audits the accuracy of Layer 4 research, Fetch pending suggestions (created >24h ago, no perf update)., Calculate binary accuracy for each pending suggestion., run_audit(), AXIOMReplayStrategy (+158 more)

### Community 2 - "Community 2"
Cohesion: 0.02
Nodes (98): AccuracyStore, Return top performers grouped by the chosen dimension.          group_by can b, Return all rows for a specific ticker., Global summary stats across all rows., Persists aggregate prediction accuracy keyed by (ticker, model, provider, direct, Upsert a new accuracy data point into the aggregate table., Update database and refresh agent health metrics., CCXTBroker (+90 more)

### Community 3 - "Community 3"
Cohesion: 0.12
Nodes (117): ArbitrageAgent, BacktestAgent, DataAgent, EarningsAgent, MacroAgent, MLAgent, NewsAgent, OptionsFlowAgent (+109 more)

### Community 4 - "Community 4"
Cohesion: 0.02
Nodes (30): Helper to log a thought and add it to the context., Execute the full Claude Flow loop — the ONLY entry point., BaseLLM, get_shared_llm(), AXIOM LLM Client — Local NVIDIA Nemotron GGUF as Primary Provider.  Priority c, Core completion method with NVIDIA NIM as primary, LM Studio as fallback., Lightweight completion for utility tasks (NER, classification, etc)., Inference using LM Studio's OpenAI-compatible API. (+22 more)

### Community 5 - "Community 5"
Cohesion: 0.03
Nodes (69): _already_indexed(), ask_stream(), _build_embedder(), EmbedderBase, _ensure_tables(), _fake_stream(), _fetch_insights_by_ids(), _fetch_news_by_ids() (+61 more)

### Community 6 - "Community 6"
Cohesion: 0.03
Nodes (53): Simple VADER-based sentiment. Upgrade to FinBERT for production., Generate a structured data-driven response when no LLM is available., GraphMemory, MiroFish Graph Memory — Zep-backed Knowledge Graph store for world events and en, Manages high-fidelity memory using Zep Graph.     Converts unstructured data (n, Internal initialization of Zep collection., Add world data to the graph memory., Semantic and graph-based search for world state retrieval. (+45 more)

### Community 7 - "Community 7"
Cohesion: 0.03
Nodes (35): TrendAgent — Calculates technical indicators using pandas-ta., Collects raw market data, routing through TickerRegistry for Universal OSS suppo, Identify asset class and correct data source., BaseSettings, KNOWLEDGE_DB_PATH(), MARKET_DATA_DB_PATH(), AXIOM Core Configuration — all settings from environment variables., Central configuration using Pydantic settings with env var loading. (+27 more)

### Community 8 - "Community 8"
Cohesion: 0.03
Nodes (23): ABC, act(), observe(), plan(), BaseAgent — Abstract base implementing Claude Flow loop: OBSERVE → THINK → PLAN, Standard execution flow with integrated telemetry., reflect(), think() (+15 more)

### Community 9 - "Community 9"
Cohesion: 0.04
Nodes (38): Procedural synthesis if LLM fails., _agent_heartbeat(), main(), AXIOM unified entry point. Starts the scheduler and gateway API, while warming, Warm the optional local GGUF fallback without delaying API availability., Initialize Mem0 in the background so offline services do not block startup., Force-initialize all agents in health monitor to ONLINE status on startup., _warm_local_llm() (+30 more)

### Community 10 - "Community 10"
Cohesion: 0.07
Nodes (37): BaseBroker, BaseBroker, Order, OrderSide, OrderType, PaperBroker, BROKER ROUTER — Claude Flow Infrastructure (100% OSS) Routes trade execution th, Routes orders to the correct broker based on asset class. (+29 more)

### Community 11 - "Community 11"
Cohesion: 0.05
Nodes (39): _pct_change(), blob_agent.py  —  Async-safe blob / cache agent ================================, Load a ticker blob from disk (if fresh) or fetch fresh data.         SAFE to awa, Inference using local specialized GGUF models., _cache_path(), collect_daily_data(), collect_historical_data(), collect_news_data() (+31 more)

### Community 12 - "Community 12"
Cohesion: 0.08
Nodes (39): _build_user_prompt(), _call_llm(), compute_price_change(), _ensure_tables(), explain_on_demand(), fetch_recent_news(), fetch_recent_ohlcv(), get_agent() (+31 more)

### Community 13 - "Community 13"
Cohesion: 0.1
Nodes (12): OpenSourceDataEngine, Open-source data engine using OpenBB Platform + SEC EDGAR + yfinance + SearXNG., SEC EDGAR Full-Text Search API — 100% free, no API key needed., SearXNG self-hosted — completely free, no API key, FRED API — free, get key at fred.stlouisfed.org.         No key? OpenBB econdb, Aggregates everything for LLM reasoning., yfinance — free, no key, OpenBB Platform — free tier with yfinance provider (+4 more)

### Community 14 - "Community 14"
Cohesion: 0.11
Nodes (20): Maps a role to specific model, tokens, temperature, and API KEY., Inference using NVIDIA NIM with specialized keys per model., Exception, AgentError, AgentTimeoutError, AxiomError, ConfigurationError, DataFetchError (+12 more)

### Community 15 - "Community 15"
Cohesion: 0.11
Nodes (13): is_available(), Vibe Trading AI Gateway — Bridge to vibe-trading-ai CLI and API.  Provides a u, Run quantic analysis (SMC, Monte Carlo, Bootstrap).          Args:, Generate trading strategy code from natural language.          Args:, Run backtest using one of 7 engines.          Args:             strategy_code, Run analysis across multiple markets simultaneously.          Args:, Return list of available swarm presets., Gateway to interact with vibe-trading-ai CLI. (+5 more)

### Community 16 - "Community 16"
Cohesion: 0.22
Nodes (6): get_news_mcp(), NewsMCP, mcp/news_mcp.py  —  Institutional News MCP (Layer 5) ===========================, Standardized interface for agents to query news data., Search for news headlines for a specific ticker in the KnowledgeStore., Get the primary drivers extracted by the NewsIntelAgent for a ticker.

### Community 17 - "Community 17"
Cohesion: 0.22
Nodes (1): ErrorBoundary

### Community 18 - "Community 18"
Cohesion: 0.25
Nodes (3): EventBus, AXIOM Event Bus — lightweight pub/sub for inter-component communication., Simple async event bus for system-wide event propagation.

### Community 19 - "Community 19"
Cohesion: 0.29
Nodes (3): InputGuard, seojoonkim/prompt-guard — runs fully locally. No HTTP call needed if installed, Returns clean input or raises HTTPException

### Community 20 - "Community 20"
Cohesion: 0.46
Nodes (6): clamp(), formatLevel(), getTone(), QuanticInsightView(), toNumber(), toPercent()

### Community 21 - "Community 21"
Cohesion: 0.33
Nodes (6): Base, AgentExperience, PredictionRecord, Structured Memory — SQLAlchemy ORM models., SQLAlchemy model for agent predictions and scoring., SQLAlchemy model for episodic memory metadata.

### Community 22 - "Community 22"
Cohesion: 0.48
Nodes (6): buildOverviewArticles(), buildSummary(), buildThemes(), getSentimentStyle(), NewsEvidenceView(), normalizeIntelPayload()

### Community 23 - "Community 23"
Cohesion: 0.33
Nodes (5): log_event(), Langfuse self-hosted observability (v4.0.1 compatible). Tracks every LLM call:, Decorator to auto-trace any LLM call to Langfuse using the @observe decorator., Log a manual event to Langfuse, trace_llm()

### Community 24 - "Community 24"
Cohesion: 0.33
Nodes (3): GitHubWorkflow, AXIOM GitHub Workflow — Automated branch, commit, and PR management for Shadow A, Creates a new branch, commits files, and opens a PR.         files: [{"path": "

### Community 25 - "Community 25"
Cohesion: 0.4
Nodes (0): 

### Community 26 - "Community 26"
Cohesion: 0.5
Nodes (2): formatTime(), IntelligenceStatusView()

### Community 27 - "Community 27"
Cohesion: 0.7
Nodes (3): formatCompactNumber(), StockDetailView(), toNumber()

### Community 28 - "Community 28"
Cohesion: 0.5
Nodes (3): calibrate_confidence(), Critique Layer — Self-reflection and confidence calibration.  Adapted from the, Calibrate final confidence score using the mythic-tier formula.          Weigh

### Community 29 - "Community 29"
Cohesion: 0.5
Nodes (2): AdvancedCandlestickChart(), computeMA()

### Community 30 - "Community 30"
Cohesion: 0.67
Nodes (2): ALERT MANAGER — Multi-Channel Broadcast (100% OSS) Sends trading signals via Te, TradingAlert

### Community 31 - "Community 31"
Cohesion: 0.67
Nodes (1): Check GitHub API connection with the provided PAT.

### Community 32 - "Community 32"
Cohesion: 1.0
Nodes (2): getBaseUrl(), getWsUrl()

### Community 33 - "Community 33"
Cohesion: 0.67
Nodes (0): 

### Community 34 - "Community 34"
Cohesion: 0.67
Nodes (0): 

### Community 35 - "Community 35"
Cohesion: 0.67
Nodes (0): 

### Community 36 - "Community 36"
Cohesion: 0.67
Nodes (0): 

### Community 37 - "Community 37"
Cohesion: 0.67
Nodes (0): 

### Community 38 - "Community 38"
Cohesion: 0.67
Nodes (0): 

### Community 39 - "Community 39"
Cohesion: 0.67
Nodes (0): 

### Community 40 - "Community 40"
Cohesion: 0.67
Nodes (0): 

### Community 41 - "Community 41"
Cohesion: 0.67
Nodes (0): 

### Community 42 - "Community 42"
Cohesion: 1.0
Nodes (1): MiroFish Simulation Engine — Round-based sandbox for agent interactions.

### Community 43 - "Community 43"
Cohesion: 1.0
Nodes (1): Fix the corrupted chat_endpoint in server.py

### Community 44 - "Community 44"
Cohesion: 1.0
Nodes (0): 

### Community 45 - "Community 45"
Cohesion: 1.0
Nodes (0): 

### Community 46 - "Community 46"
Cohesion: 1.0
Nodes (0): 

### Community 47 - "Community 47"
Cohesion: 1.0
Nodes (0): 

### Community 48 - "Community 48"
Cohesion: 1.0
Nodes (0): 

### Community 49 - "Community 49"
Cohesion: 1.0
Nodes (0): 

### Community 50 - "Community 50"
Cohesion: 1.0
Nodes (0): 

### Community 51 - "Community 51"
Cohesion: 1.0
Nodes (0): 

### Community 52 - "Community 52"
Cohesion: 1.0
Nodes (0): 

### Community 53 - "Community 53"
Cohesion: 1.0
Nodes (0): 

### Community 54 - "Community 54"
Cohesion: 1.0
Nodes (0): 

### Community 55 - "Community 55"
Cohesion: 1.0
Nodes (0): 

### Community 56 - "Community 56"
Cohesion: 1.0
Nodes (0): 

### Community 57 - "Community 57"
Cohesion: 1.0
Nodes (0): 

### Community 58 - "Community 58"
Cohesion: 1.0
Nodes (0): 

### Community 59 - "Community 59"
Cohesion: 1.0
Nodes (0): 

### Community 60 - "Community 60"
Cohesion: 1.0
Nodes (0): 

### Community 61 - "Community 61"
Cohesion: 1.0
Nodes (0): 

### Community 62 - "Community 62"
Cohesion: 1.0
Nodes (0): 

### Community 63 - "Community 63"
Cohesion: 1.0
Nodes (0): 

### Community 64 - "Community 64"
Cohesion: 1.0
Nodes (0): 

### Community 65 - "Community 65"
Cohesion: 1.0
Nodes (0): 

### Community 66 - "Community 66"
Cohesion: 1.0
Nodes (0): 

### Community 67 - "Community 67"
Cohesion: 1.0
Nodes (0): 

### Community 68 - "Community 68"
Cohesion: 1.0
Nodes (0): 

### Community 69 - "Community 69"
Cohesion: 1.0
Nodes (0): 

### Community 70 - "Community 70"
Cohesion: 1.0
Nodes (0): 

### Community 71 - "Community 71"
Cohesion: 1.0
Nodes (0): 

### Community 72 - "Community 72"
Cohesion: 1.0
Nodes (0): 

### Community 73 - "Community 73"
Cohesion: 1.0
Nodes (0): 

### Community 74 - "Community 74"
Cohesion: 1.0
Nodes (0): 

### Community 75 - "Community 75"
Cohesion: 1.0
Nodes (0): 

### Community 76 - "Community 76"
Cohesion: 1.0
Nodes (0): 

### Community 77 - "Community 77"
Cohesion: 1.0
Nodes (0): 

### Community 78 - "Community 78"
Cohesion: 1.0
Nodes (0): 

### Community 79 - "Community 79"
Cohesion: 1.0
Nodes (0): 

### Community 80 - "Community 80"
Cohesion: 1.0
Nodes (0): 

### Community 81 - "Community 81"
Cohesion: 1.0
Nodes (0): 

### Community 82 - "Community 82"
Cohesion: 1.0
Nodes (0): 

### Community 83 - "Community 83"
Cohesion: 1.0
Nodes (0): 

### Community 84 - "Community 84"
Cohesion: 1.0
Nodes (1): Allow env modes like 'release' or 'development' for DEBUG.

### Community 85 - "Community 85"
Cohesion: 1.0
Nodes (1): Joins filename from .env with project root to create an absolute path.

### Community 86 - "Community 86"
Cohesion: 1.0
Nodes (1): Returns the current time in IST.

### Community 87 - "Community 87"
Cohesion: 1.0
Nodes (1): Returns 'OPEN' or 'CLOSED' for a given market key.

### Community 88 - "Community 88"
Cohesion: 1.0
Nodes (1): Returns the current status of all major markets.

### Community 89 - "Community 89"
Cohesion: 1.0
Nodes (1): Maps a ticker symbol to its primary market.

### Community 90 - "Community 90"
Cohesion: 1.0
Nodes (1): Returns context for AI suggestions based on market status.

### Community 91 - "Community 91"
Cohesion: 1.0
Nodes (0): 

### Community 92 - "Community 92"
Cohesion: 1.0
Nodes (0): 

### Community 93 - "Community 93"
Cohesion: 1.0
Nodes (0): 

### Community 94 - "Community 94"
Cohesion: 1.0
Nodes (1): Preloads local GGUF models into memory. Loads both reasoning and general models.

### Community 95 - "Community 95"
Cohesion: 1.0
Nodes (0): 

### Community 96 - "Community 96"
Cohesion: 1.0
Nodes (0): 

### Community 97 - "Community 97"
Cohesion: 1.0
Nodes (0): 

### Community 98 - "Community 98"
Cohesion: 1.0
Nodes (0): 

### Community 99 - "Community 99"
Cohesion: 1.0
Nodes (0): 

### Community 100 - "Community 100"
Cohesion: 1.0
Nodes (0): 

### Community 101 - "Community 101"
Cohesion: 1.0
Nodes (0): 

### Community 102 - "Community 102"
Cohesion: 1.0
Nodes (0): 

### Community 103 - "Community 103"
Cohesion: 1.0
Nodes (0): 

### Community 104 - "Community 104"
Cohesion: 1.0
Nodes (1): Expects a DataFrame with [timestamp, open, high, low, close, volume].         R

### Community 105 - "Community 105"
Cohesion: 1.0
Nodes (1): Returns the latest indicator values as a dictionary.

### Community 106 - "Community 106"
Cohesion: 1.0
Nodes (0): 

### Community 107 - "Community 107"
Cohesion: 1.0
Nodes (0): 

### Community 108 - "Community 108"
Cohesion: 1.0
Nodes (0): 

### Community 109 - "Community 109"
Cohesion: 1.0
Nodes (0): 

### Community 110 - "Community 110"
Cohesion: 1.0
Nodes (0): 

## Knowledge Gaps
- **294 isolated node(s):** `Abstract base. Subclasses implement encode().`, `Uses the LM Studio /v1/embeddings endpoint — same server already running.     W`, `sentence-transformers/all-MiniLM-L6-v2 — requires model download.`, `Deterministic hash-based embedding — no downloads, no network, no GPU.     Same`, `Try LM Studio first, then sentence-transformers, then hash fallback.` (+289 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 42`** (2 nodes): `simulation_engine.py`, `MiroFish Simulation Engine — Round-based sandbox for agent interactions.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 43`** (2 nodes): `fix_server.py`, `Fix the corrupted chat_endpoint in server.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 44`** (2 nodes): `vite.config.js`, `manualChunks()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 45`** (2 nodes): `AgentMatrixView()`, `AgentMatrixView.jsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 46`** (2 nodes): `AgentStreamPanel()`, `AgentStreamPanel.jsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 47`** (2 nodes): `AskBar()`, `AskBar.jsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 48`** (2 nodes): `ChatPanel()`, `ChatPanel.jsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 49`** (2 nodes): `DependencyGraph()`, `DependencyGraph.jsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 50`** (2 nodes): `DiagnosticView()`, `DiagnosticView.jsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 51`** (2 nodes): `FreshnessBadge.jsx`, `FreshnessBadge()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 52`** (2 nodes): `LiveTickerBar.jsx`, `LiveTickerBar()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 53`** (2 nodes): `Logo.jsx`, `Logo()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 54`** (2 nodes): `MarketStatusBadges.jsx`, `MarketStatusBadges()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 55`** (2 nodes): `MoveExplainer.jsx`, `MoveExplainer()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 56`** (2 nodes): `PortfolioInsightsView.jsx`, `PortfolioInsightsView()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 57`** (2 nodes): `ShadowPortfolioCard.jsx`, `ShadowPortfolioCard()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 58`** (2 nodes): `StockChat.jsx`, `StockChat()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 59`** (2 nodes): `StockDetailPanel.jsx`, `StockDetailPanel()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 60`** (2 nodes): `SwipeDecide.jsx`, `SwipeDecide()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 61`** (2 nodes): `TrendingStocksView.jsx`, `TrendingStocksView()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 62`** (2 nodes): `VirtualPortfolioView.jsx`, `VirtualPortfolioView()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 63`** (2 nodes): `WhyCard.jsx`, `WhyCard()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 64`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 65`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 66`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 67`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 68`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 69`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 70`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 71`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 72`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 73`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 74`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 75`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 76`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 77`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 78`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 79`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 80`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 81`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 82`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 83`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 84`** (1 nodes): `Allow env modes like 'release' or 'development' for DEBUG.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 85`** (1 nodes): `Joins filename from .env with project root to create an absolute path.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 86`** (1 nodes): `Returns the current time in IST.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 87`** (1 nodes): `Returns 'OPEN' or 'CLOSED' for a given market key.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 88`** (1 nodes): `Returns the current status of all major markets.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 89`** (1 nodes): `Maps a ticker symbol to its primary market.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 90`** (1 nodes): `Returns context for AI suggestions based on market status.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 91`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 92`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 93`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 94`** (1 nodes): `Preloads local GGUF models into memory. Loads both reasoning and general models.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 95`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 96`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 97`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 98`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 99`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 100`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 101`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 102`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 103`** (1 nodes): `fix_router.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 104`** (1 nodes): `Expects a DataFrame with [timestamp, open, high, low, close, volume].         R`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 105`** (1 nodes): `Returns the latest indicator values as a dictionary.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 106`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 107`** (1 nodes): `eslint.config.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 108`** (1 nodes): `main.jsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 109`** (1 nodes): `theme.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 110`** (1 nodes): `config.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `AgentContext` connect `Community 1` to `Community 0`, `Community 2`, `Community 3`, `Community 4`, `Community 6`, `Community 7`, `Community 8`, `Community 9`, `Community 10`, `Community 11`?**
  _High betweenness centrality (0.190) - this node is a cross-community bridge._
- **Why does `BaseAgent` connect `Community 1` to `Community 0`, `Community 2`, `Community 3`, `Community 4`, `Community 6`, `Community 7`, `Community 8`, `Community 9`, `Community 10`, `Community 11`?**
  _High betweenness centrality (0.048) - this node is a cross-community bridge._
- **Why does `LLMClient` connect `Community 3` to `Community 0`, `Community 1`, `Community 2`, `Community 4`, `Community 6`, `Community 7`, `Community 9`, `Community 10`, `Community 11`, `Community 14`?**
  _High betweenness centrality (0.027) - this node is a cross-community bridge._
- **Are the 359 inferred relationships involving `AgentContext` (e.g. with `AXIOM unified entry point. Starts the scheduler and gateway API, while warming` and `Warm the optional local GGUF fallback without delaying API availability.`) actually correct?**
  _`AgentContext` has 359 INFERRED edges - model-reasoned connections that need verification._
- **Are the 188 inferred relationships involving `BaseAgent` (e.g. with `AccuracyStoreAgent` and `AccuracyStore — SQLite-backed aggregate accuracy persistence.  Tracks rolling`) actually correct?**
  _`BaseAgent` has 188 INFERRED edges - model-reasoned connections that need verification._
- **Are the 117 inferred relationships involving `RagAgent` (e.g. with `ApiAgent` and `Agent 8 & 11: UI API Agent & Orchestrator - Central Interface coordinating all 1`) actually correct?**
  _`RagAgent` has 117 INFERRED edges - model-reasoned connections that need verification._
- **Are the 96 inferred relationships involving `LLMClient` (e.g. with `AXIOM unified entry point. Starts the scheduler and gateway API, while warming` and `Warm the optional local GGUF fallback without delaying API availability.`) actually correct?**
  _`LLMClient` has 96 INFERRED edges - model-reasoned connections that need verification._