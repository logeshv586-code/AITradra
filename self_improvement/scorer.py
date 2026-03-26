"""Prediction Scorer — Calculates accuracy of past market predictions."""

from core.logger import get_logger

logger = get_logger(__name__)


class PredictionScorer:
    """Evaluates agent recommendations against real-world outcomes."""

    def calculate_accuracy(self, prediction_price: float, target_price: float,
                           actual_price: float, direction: str) -> float:
        """
        Calculates a continuous accuracy score between 0.0 and 1.0.
        Rewards correct directional moves, penalizes completely wrong ones.
        """
        if direction == "BULLISH":
            if actual_price >= target_price: return 1.0
            if actual_price <= prediction_price: return 0.0
            return (actual_price - prediction_price) / (target_price - prediction_price)
        else:
            if actual_price <= target_price: return 1.0
            if actual_price >= prediction_price: return 0.0
            return (prediction_price - actual_price) / (prediction_price - target_price)

    def evaluate_llm_reasoning(self, original_reasoning: str, outcome: str) -> str:
        """Uses LLM to critique its own past reasoning when a prediction fails."""
        # Stubbed CoT critique
        return f"Critique attached for outcome {outcome}"
