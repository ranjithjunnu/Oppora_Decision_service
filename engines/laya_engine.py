"""
engine.py — Core Laya Decision Engine Wrapper.

Provides a singleton wrapper around Laya's Router with:
- Warm-up and pre-loading on startup (no repeated downloads or model loads).
- Precise millisecond latency measurements.
- Safe parsing and extraction of choices, probabilities, and confidence scores.
- Structured conversion into Pydantic contracts.
"""

import time
import logging
from typing import Dict, Any, Tuple, Optional, Callable
from laya import Router

from models.decision import ChoiceAnswer, QuestionSpec

logger = logging.getLogger("laya_decision_service.engine")


class DecisionEngine:
    """
    Singleton wrapper for the Laya Decision Router.
    Ensures weights are loaded once in memory and reused across all requests.
    """
    _instance: Optional["DecisionEngine"] = None

    def __new__(cls) -> "DecisionEngine":
        if cls._instance is None:
            cls._instance = super(DecisionEngine, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return

        logger.info("Initializing Laya DecisionEngine...")
        self.ready = False
        self.router = Router()
        self.default_model = "typed-decisions"
        self._warmup()
        self.ready = True
        self._initialized = True
        logger.info("Laya DecisionEngine ready.")

    def _warmup(self) -> None:
        """Load and exercise the model before reporting readiness."""
        try:
            logger.info("Warming up decision model...")
            dummy_state = "Warmup system state"
            dummy_questions = {
                "warmup": {
                    "type": "choice",
                    "instructions": "Warmup check",
                    "criteria": ["ready", "initializing"]
                }
            }
            self.router.predict(dummy_state, dummy_questions, model=self.default_model)
            logger.info("Warmup complete.")
        except Exception as e:
            logger.error(f"Engine warmup failed: {e}")
            raise

    def decide(
        self,
        state: str,
        questions: Dict[str, QuestionSpec],
        model: Optional[str] = None,
        *,
        capture_raw: Optional[Callable[[Any], None]] = None,
    ) -> Tuple[Dict[str, ChoiceAnswer], float]:
        """
        Executes a batch of decision questions against a given state.

        Returns:
            Tuple of (parsed_answers_dict, latency_ms)
        """
        target_model = model or self.default_model

        # Convert QuestionSpec into raw laya dict format
        raw_questions = {}
        for qid, qspec in questions.items():
            raw_questions[qid] = {
                "type": qspec.type,
                "instructions": qspec.instructions,
                "criteria": qspec.criteria
            }

        start_time = time.perf_counter()
        raw_result = self.router.predict(state, raw_questions, model=target_model)
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        # Optional observation for manual evaluation; existing callers and the
        # normalization/confidence calculation below remain unchanged.
        if capture_raw is not None:
            capture_raw(raw_result)

        parsed_answers: Dict[str, ChoiceAnswer] = {}
        answers_dict = raw_result.get("answers", {})

        for qid, answer_data in answers_dict.items():
            choice = answer_data.get("choice", "")
            raw_probs = answer_data.get("probabilities", {})
            probabilities = {k: round(float(v), 4) for k, v in raw_probs.items()}

            # Preserve scores without describing them as calibrated accuracy.
            winner_prob = probabilities.get(choice)
            ans_conf = answer_data.get("answer_confidence")
            raw_conf = answer_data.get("confidence")

            if winner_prob is not None:
                confidence = float(winner_prob)
                source = "model_probability"
            elif ans_conf is not None:
                confidence = float(ans_conf)
                source = "model_score"
            elif raw_conf is not None:
                confidence = float(raw_conf)
                source = "model_score"
            else:
                confidence = None
                source = "unavailable"

            parsed_answers[qid] = ChoiceAnswer(
                choice=choice,
                confidence=round(confidence, 4) if confidence is not None else None,
                source=source,
                probabilities=probabilities
            )

        return parsed_answers, round(elapsed_ms, 2)

    def decide_single(
        self,
        state: str,
        question_id: str,
        instructions: str,
        criteria: Any,
        model: Optional[str] = None
    ) -> Tuple[ChoiceAnswer, float]:
        """Convenience method for evaluating a single decision question."""
        spec = QuestionSpec(
            type="choice",
            instructions=instructions,
            criteria=criteria
        )
        answers, latency = self.decide(state, {question_id: spec}, model=model)
        return answers[question_id], latency


# Global singleton instance helper
_engine_instance: Optional[DecisionEngine] = None

def get_engine() -> DecisionEngine:
    """Returns the singleton DecisionEngine instance."""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = DecisionEngine()
    return _engine_instance
