import pathlib
import datetime

p = pathlib.Path(r'c:\Users\e629\Desktop\AITradra\agents\query_router.py')
lines = p.read_text(encoding='utf-8').splitlines(keepends=True)

# Find the start of act()
act_start = -1
for i, line in enumerate(lines):
    if "async def act(self, context: AgentContext) -> AgentContext:" in line:
        act_start = i
        break

if act_start != -1:
    before = lines[:act_start+1]
    
    # Identify the try block
    try_idx = -1
    for i in range(act_start+1, min(len(lines), act_start + 20)):
        if "try:" in lines[i]:
            try_idx = i
            break
            
    if try_idx != -1:
        after = lines[try_idx:]
        
        insert_code = """        ticker = context.observations.get("ticker")
        query = context.observations["query"]
        research_mode = context.metadata.get("research_mode", "QUICK")

        # ─── PARALLEL FAN-OUT to all 4 data sources ─────────────────────────
        gathered_context = await self._parallel_gather(query, ticker)

        if research_mode == "QUICK":
            logger.info(f"Using FAST PATH synthesis for ticker: {ticker or 'general'}")
            response = await self._fallback_llm_synthesize(query, ticker, gathered_context)
            context.result = {
                "response": response,
                "ticker": ticker,
                "intent": context.observations.get("intent", "general"),
                "research_mode": "QUICK",
                "confidence": 0.8,
                "sources_used": list(gathered_context.keys()),
                "data_freshness": datetime.now().isoformat(),
            }
            context.actions_taken.append({"action": "fast_path_complete"})
            return context

        # ─── Route through MythicOrchestrator ────────────────────────────────
"""
        new_lines = [line + '\n' for line in insert_code.split('\n')]
        
        p.write_text("".join(before + new_lines + after), encoding='utf-8')
        print("Patched successfully")
    else:
        print("Couldn't find try block")
else:
    print("Couldn't find act block")
