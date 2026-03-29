from crewai import Agent, Task, Crew, Process
from typing import List, Dict, Any, Optional
import os
import asyncio
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, ChatMessage, AIMessage
from langchain_core.outputs import ChatResult, ChatGeneration

from langchain_core.language_models.llms import LLM

class AxiomLangChainWrapper(LLM):
    """Bridge between AXIOM LLMClient and LangChain/CrewAI."""
    axiom_client: Any = None
    
    class Config:
        arbitrary_types_allowed = True

    def _call(self, prompt: str, stop: Optional[List[str]] = None, **kwargs) -> str:
        # Run async complete in sync context
        try:
            # We are likely inside a thread pool if called by CrewAI
            # or we need to bridge async to sync safely.
            import asyncio
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Use a helper to run coroutine in a safe way if loop is already running
            if loop.is_running():
                # This is the tricky part. CrewAI calls this synchronously.
                # If we are in the main thread's loop, we can't run_until_complete.
                # But CrewAI usually runs tasks in threads.
                from concurrent.futures import ThreadPoolExecutor
                with ThreadPoolExecutor() as executor:
                    future = executor.submit(lambda: asyncio.run(self.axiom_client.complete(prompt)))
                    return future.result()
            else:
                return loop.run_until_complete(self.axiom_client.complete(prompt))
        except Exception as e:
            return f"Error in AxiomLLM: {str(e)}"

    @property
    def _llm_type(self) -> str:
        return "axiom-mythic-llm"

class OmniCrewManager:
    def __init__(self, data_engine, llm_client):
        self.data_engine = data_engine
        self.llm = AxiomLangChainWrapper(axiom_client=llm_client)

    def _create_agents(self) -> Dict[str, Agent]:
        # 1. Market Researcher (combines technical and news)
        researcher = Agent(
            role='Senior Market Researcher',
            goal='Aggregate technical trends, news catalysts, and sentiment for {ticker}',
            backstory="""Expert at synthesizing multidimensional data. You look at charts and headlines 
            simultaneously to find the primary market driver.""",
            verbose=True,
            allow_delegation=False,
            llm=self.llm
        )

        # 2. Chief Strategist (combines risk and synthesis)
        strategist = Agent(
            role='Chief Mythic Strategist',
            goal='Generate final OMNI-AXIOM V5 trading signal and risk profile for {ticker}',
            backstory="""The decision maker. You take research and apply risk parameters to form 
            a high-confidence trading recommendation (UP/DOWN/SIDEWAYS).""",
            verbose=True,
            allow_delegation=True,
            llm=self.llm
        )

        return {
            "researcher": researcher,
            "strategist": strategist
        }

    def run_analysis(self, ticker: str, context: str) -> Dict:
        agents = self._create_agents()

        # Define Tasks
        task_research = Task(
            description=f"Conduct a deep dive into {ticker}. Analyze recent price action and top news headlines. Determine the 'Primary Driver'.",
            expected_output="A consolidated research report with technical and sentiment bias.",
            agent=agents["researcher"]
        )

        task_synthesis = Task(
            description=f"""Synthesize research for {ticker} into a final OMNI-AXIOM V5 report.
            Requirements:
            {{
                "ticker": "{ticker}",
                "prediction_direction": "UP | DOWN | SIDEWAYS",
                "confidence_score": (0-85),
                "expected_move_percent": float,
                "risk_level": "LOW | MEDIUM | HIGH",
                "reasoning_summary": "2 line summary",
                "primary_driver": "string",
                "signal": "string",
                "entry_price": float,
                "target_price": float,
                "stop_loss": float
            }}
            Context from market: {context}""",
            expected_output="Final structured trading intelligence report in JSON format.",
            agent=agents["strategist"]
        )

        # Create Crew
        crew = Crew(
            agents=[agents["researcher"], agents["strategist"]],
            tasks=[task_research, task_synthesis],
            process=Process.sequential,
            verbose=2
        )

        result = crew.kickoff(inputs={'ticker': ticker})
        return result
