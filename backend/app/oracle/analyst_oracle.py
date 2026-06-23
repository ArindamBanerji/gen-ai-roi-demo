from __future__ import annotations

import random


class AnalystOracle:
    """Parametric oracle for SOC pipeline validation.

    Generates synthetic outcomes with a KNOWN injected effect.
    The pipeline must RECOVER this effect -- if it does, the
    measurement instrument is validated (T-O).

    NOT a magnitude claim. The oracle proves capability, not size.
    """

    def __init__(
        self,
        *,
        base_escalation_rate: float = 0.30,
        treatment_lift: float = 0.10,
        base_accuracy: float = 0.70,
        accuracy_lift: float = 0.05,
        seed: int = 42,
    ) -> None:
        self._base_rate = base_escalation_rate
        self._lift = treatment_lift
        self._base_accuracy = base_accuracy
        self._accuracy_lift = accuracy_lift
        self._rng = random.Random(seed)

    @property
    def known_effect(self) -> float:
        """Known treatment lift on escalation rate."""
        return self._lift

    @property
    def known_accuracy_effect(self) -> float:
        """Known treatment lift on accuracy."""
        return self._accuracy_lift

    def synthetic_outcome(self, *, shown: bool) -> dict:
        """Generate one synthetic analyst outcome.

        Args:
            shown: True = treatment (advisory shown), False = control.

        Returns:
            {analyst_action, was_override, quality_signal, correct}

        CRITICAL: `correct` is MODELED, not hardcoded True.
        p_correct = base_accuracy + (accuracy_lift if shown else 0)
        """
        p_escalate = self._base_rate + (self._lift if shown else 0)
        escalate = self._rng.random() < _clamp_probability(p_escalate)

        p_correct = self._base_accuracy + (self._accuracy_lift if shown else 0)
        correct = self._rng.random() < _clamp_probability(p_correct)

        action = "escalate_tier2" if escalate else "dismiss"
        was_override = self._rng.random() < 0.15
        quality_signal = 1.0 if correct else 0.0

        return {
            "action": action,
            "analyst_action": action,
            "was_override": was_override,
            "quality_signal": quality_signal,
            "correct": correct,
        }


def _clamp_probability(value: float) -> float:
    return max(0.0, min(float(value), 1.0))
