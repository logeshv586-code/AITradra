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
        if prediction_price <= 0 or actual_price <= 0:
            return 0.0

        normalized = self.normalize_direction(direction)
        target_price = target_price or prediction_price

        if normalized == "BULLISH":
            if target_price <= prediction_price:
                target_price = prediction_price * 1.01
            if actual_price >= target_price:
                return 1.0
            if actual_price <= prediction_price:
                return 0.0
            return max(min((actual_price - prediction_price) / (target_price - prediction_price), 1.0), 0.0)

        if normalized == "BEARISH":
            if target_price >= prediction_price:
                target_price = prediction_price * 0.99
            if actual_price <= target_price:
                return 1.0
            if actual_price >= prediction_price:
                return 0.0
            return max(min((prediction_price - actual_price) / (prediction_price - target_price), 1.0), 0.0)

        realized_move = abs((actual_price - prediction_price) / prediction_price)
        return max(0.0, min(1.0, 1.0 - (realized_move / 0.03)))

    def normalize_direction(self, direction: str) -> str:
        """Map app verdict labels into scoring directions."""
        value = str(direction or "").upper()
        if value in {"UP", "BULLISH", "BUY", "LONG", "ACCUMULATE"}:
            return "BULLISH"
        if value in {"DOWN", "BEARISH", "SELL", "SHORT", "AVOID"}:
            return "BEARISH"
        return "NEUTRAL"

    def evaluate_llm_reasoning(self, original_reasoning: str, outcome: str) -> str:
        """Uses LLM to critique its own past reasoning when a prediction fails."""
        # Stubbed CoT critique
        return f"Critique attached for outcome {outcome}"
