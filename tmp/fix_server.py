"""Fix the corrupted chat_endpoint in server.py"""
import pathlib

SERVER_PATH = pathlib.Path(r"c:\Users\e629\Desktop\AITradra\gateway\server.py")

lines = SERVER_PATH.read_text(encoding="utf-8").splitlines(keepends=True)
print(f"Original file: {len(lines)} lines")

# Keep lines before the chat endpoint (0-indexed: 0..1110 = lines 1..1111)
before = lines[:1111]
# Keep lines after the corrupted section (0-indexed: 1242+ = line 1243+)
after = lines[1242:]

NEW_CHAT_ENDPOINT = '''\n
@app.post("/api/chat")
@app.post("/api/agents/chat")
async def chat_endpoint(request: Request):
    """AXIOM MYTHIC - Multi-agent orchestrated intelligence.

    Routes through MythicOrchestrator pipeline:
    Parallel Fan-Out, Specialist Fleet, Critique, Calibrated Synthesis
    """
    body = await request.json()
    user_msg = body.get("message", "").strip()
    ticker = body.get("ticker", "")

    # Intercept scrape commands
    if user_msg.startswith("> scrape"):
        try:
            from scrapers.playwright_news import run_scraper
            import shlex

            parts = shlex.split(user_msg[8:].strip())
            query = parts[0] if parts else "Indian stock market"
            tickers = parts[1:] if len(parts) > 1 else []

            saved = await run_scraper(query, tickers, headless=True)
            return {
                "response": f"Scrape completed. Found and saved **{saved}** new articles for `{query}` and tickers `{tickers}` into `stock_news.db`.",
                "source": "playwright_scraper",
            }
        except Exception as e:
            logger.error(f"Scrape command failed: {e}")
            return {"response": f"Scraper failed: {e}", "source": "system"}

    if user_msg.startswith("> compare") or user_msg.startswith("> sentiment"):
        try:
            from agents.sentiment_engine import sentiment_engine

            cmd_parts = user_msg.split(" ")[1:]
            tickers = [t.upper() for t in cmd_parts if len(t) < 10]
            if not tickers and ticker:
                tickers = [ticker.upper()]

            res = await sentiment_engine.analyze_sentiment(user_msg, tickers)
            if res.get("error"):
                return {
                    "response": res.get("message", "Error analyzing sentiment."),
                    "source": "system",
                }

            return {
                "response": res["markdown"],
                "source": "sentiment_engine",
                "sources_used": res.get("sources_used", []),
            }
        except Exception as e:
            logger.error(f"Sentiment command failed: {e}")
            return {"response": f"Sentiment analysis failed: {e}", "source": "system"}

    # Route through the intelligent QueryRouter and MythicOrchestrator
    ctx = AgentContext(
        task=user_msg,
        ticker=ticker.upper() if ticker else None,
        metadata={
            "research_mode": body.get("research_mode", "QUICK"),
            "history": body.get("history", []),
        },
    )

    try:
        result = await asyncio.wait_for(query_router.run(ctx), timeout=120)
    except asyncio.TimeoutError:
        logger.warning(f"Chat query timed out for: {user_msg[:80]}")
        result = ctx
    except Exception as e:
        logger.error(f"Chat pipeline error: {e}")
        result = ctx

    if isinstance(result.result, dict) and result.result.get("response"):
        response = result.result.get("response", "")
        llm_meta = get_shared_llm().runtime_profile()
        return {
            "response": response,
            "source": "mythic_v4",
            "llm_provider": llm_meta.get("last_provider_used") or llm_meta.get("active_provider"),
            "model_router": llm_meta,
            "consensus": result.result.get("consensus"),
            "confidence": result.result.get("confidence"),
            "research_mode": result.result.get("research_mode", body.get("research_mode", "QUICK")),
            "intelligence_profile": result.result.get("intelligence_profile", {}),
            "specialist_outputs": result.result.get("specialist_outputs"),
            "critique": result.result.get("critique"),
            "pipeline_ms": result.result.get("pipeline_ms"),
            "sources_used": result.result.get("sources_used", []),
        }

    # Fallback: direct LLM call when the full pipeline fails or returns empty
    try:
        llm = get_shared_llm()
        system = (
            "You are AXIOM, an expert AI trading intelligence assistant. "
            "You analyze markets, stocks, and investment strategies with deep financial knowledge. "
            "Be specific, data-driven, and actionable. Use professional financial tone. "
            f"Current time: {datetime.now().isoformat()}"
        )
        prompt = f"User question: {user_msg}"
        if ticker:
            prompt += f"\\nContext ticker: {ticker.upper()}"

        direct_response = await llm.complete(prompt=prompt, system=system, temperature=0.3, max_tokens=1200)
        llm_meta = llm.runtime_profile()
        return {
            "response": direct_response,
            "source": "direct_llm_fallback",
            "llm_provider": llm_meta.get("last_provider_used") or llm_meta.get("active_provider"),
            "model_router": llm_meta,
        }
    except Exception as fallback_err:
        logger.error(f"Direct LLM fallback also failed: {fallback_err}")
        return {
            "response": "The intelligence pipeline is currently initializing. Please retry in a moment.",
            "source": "system_fallback",
        }

'''

# Build new content
new_section_lines = [line + "\n" for line in NEW_CHAT_ENDPOINT.split("\n")]
result = before + new_section_lines + after
SERVER_PATH.write_text("".join(result), encoding="utf-8")
print(f"Fixed file: {len(result)} lines")
print("Done!")
