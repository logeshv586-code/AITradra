"""AXIOM Custom Exception Hierarchy — typed exceptions for clean error handling."""


class AxiomError(Exception):
    """Base exception for all AXIOM errors."""
    pass


class AgentError(AxiomError):
    """Error within an agent's execution."""
    def __init__(self, agent_name: str, message: str):
        self.agent_name = agent_name
        super().__init__(f"[{agent_name}] {message}")


class AgentTimeoutError(AgentError):
    """Agent exceeded its timeout."""
    pass


class DataFetchError(AxiomError):
    """Failed to fetch external data (yfinance, news, etc.)."""
    def __init__(self, source: str, message: str):
        self.source = source
        super().__init__(f"[{source}] {message}")


class LLMError(AxiomError):
    """Error communicating with LLM provider."""
    pass


class MemoryError(AxiomError):
    """Error in memory operations."""
    pass


class PredictionError(AxiomError):
    """Error in prediction pipeline."""
    pass


class ConfigurationError(AxiomError):
    """Invalid or missing configuration."""
    pass
