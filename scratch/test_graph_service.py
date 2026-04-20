
import asyncio
from gateway.knowledge_graph_service import knowledge_graph

async def test_graph():
    print("Testing Knowledge Graph Service...")
    # Test with a known symbol or common term
    term = "AAPL"
    context = knowledge_graph.get_code_context(term)
    print(f"\nContext for '{term}':\n{context}")
    
    # Test with a function name
    term = "collect_daily_data"
    context = knowledge_graph.get_code_context(term)
    print(f"\nContext for '{term}':\n{context}")

if __name__ == "__main__":
    asyncio.run(test_graph())
