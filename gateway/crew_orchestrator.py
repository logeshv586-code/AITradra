from crewai import Agent, Task, Crew, Process
from crewai.llms.base_llm import BaseLLM
from typing import Dict, Any
import asyncio


class AxiomCrewLLM(BaseLLM):
    """CrewAI-native adapter around the project's async LLM client."""

    def __init__(self, axiom_client: Any):
        self.axiom_client = axiom_client
        super().__init__(model="axiom/mythic", temperature=0.2, provider="axiom")

    def _messages_to_prompt(self, messages: Any) -> str:
        if isinstance(messages, str):
            return messages

        parts = []
        for message in messages or []:
            if isinstance(message, dict):
                role = message.get("role", "user")
                content = message.get("content", "")
            else:
                role = getattr(message, "role", "user")
                content = getattr(message, "content", "")

            if isinstance(content, list):
                text_chunks = []
                for chunk in content:
                    if isinstance(chunk, dict) and chunk.get("type") == "text":
                        text_chunks.append(chunk.get("text", ""))
                    elif isinstance(chunk, str):
                        text_chunks.append(chunk)
                content = "\n".join(filter(None, text_chunks))

            parts.append(f"{role.upper()}:\n{content}")

        return "\n\n".join(filter(None, parts))

    def _run_complete_sync(self, prompt: str) -> str:
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            from concurrent.futures import ThreadPoolExecutor

            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(lambda: asyncio.run(self.axiom_client.complete(prompt, role="analysis")))
                return future.result()

        if loop is None:
            return asyncio.run(self.axiom_client.complete(prompt, role="analysis"))

        return loop.run_until_complete(self.axiom_client.complete(prompt, role="analysis"))

    def call(
        self,
        messages,
        tools=None,
        callbacks=None,
        available_functions=None,
        from_task=None,
        from_agent=None,
        response_model=None,
    ) -> str:
        prompt = self._messages_to_prompt(messages)
        return self._run_complete_sync(prompt)

    async def acall(
        self,
        messages,
        tools=None,
        callbacks=None,
        available_functions=None,
        from_task=None,
        from_agent=None,
        response_model=None,
    ) -> str:
        prompt = self._messages_to_prompt(messages)
        return await self.axiom_client.complete(prompt, role="analysis")

class OmniCrewManager:
    def __init__(self, data_engine, llm_client):
        self.data_engine = data_engine
        self.llm = AxiomCrewLLM(axiom_client=llm_client)

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
            # Newer CrewAI/Pydantic validation requires a real bool here.
            verbose=True
        )

        result = crew.kickoff(inputs={'ticker': ticker})
        return result
