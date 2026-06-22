"""B-plane — task classification and level-band selection policy.

Implements the rule-based decision policy from Section 6.1.6 of the paper.
The B-plane classifies a task along four dimensions:
  scope, uncertainty, risk, and required abstraction.
It then selects a level-band and builds instructions for the reactivation planner.
"""
from __future__ import annotations

import json
import re
from typing import Optional

import anthropic

from .models import TaskClassification
from anthropic.types import TextBlock


_SCOPE_RULES = {
    "narrow_factual":  (1, 2),
    "procedural":      (2, 3),
    "diagnostic":      (1, 3),
    "strategic":       (3, 4),
    "high_risk":       (1, 4),
}

_SCOPE_DESCRIPTIONS = {
    "narrow_factual":  "Simple fact lookup or single-step action with known answer.",
    "procedural":      "Execution of a known procedure or tool sequence.",
    "diagnostic":      "Debugging, root-cause analysis, or fault isolation.",
    "strategic":       "Open-ended planning, design, or multi-objective reasoning.",
    "high_risk":       "Actions that affect privacy, security, or irreversible state.",
}

_CLASSIFICATION_PROMPT = """You classify tasks for a software debugging agent.

Task: {task}

Classify the task along these dimensions:

scope — choose exactly one:
  - narrow_factual: simple lookup or single-step with a known answer
  - procedural: running a known command or tool sequence
  - diagnostic: debugging, fault isolation, root-cause analysis
  - strategic: open-ended planning or multi-objective reasoning
  - high_risk: affects security, privacy, or irreversible state

uncertainty (0.0–1.0): how much the agent benefits from past experience
risk (0.0–1.0): chance of irreversible or harmful action
abstraction_need (1–4): 1=raw traces needed, 2=episodes, 3=strategies, 4=governance

Return ONLY valid JSON. Example:
{{"scope":"diagnostic","uncertainty":0.7,"risk":0.1,"abstraction_need":2,"reasoning":"..."}}"""


class BPlane:
    """
    Classifies tasks and selects memory level-bands.
    Uses Claude for task classification; falls back to keyword heuristics.
    """

    def __init__(self, client: Optional[anthropic.Anthropic]):
        self.client = client

    def classify(self, task: str, context: dict | None = None) -> TaskClassification:
        """Classify a task and return a TaskClassification with level_band."""
        if self.client is None:
            self._classify_heuristic(task)

        try:
            result = self._classify_with_llm(task)
        except Exception:
            result = self._classify_heuristic(task)

        result.level_band = _SCOPE_RULES[result.scope]
        return result

    def _classify_with_llm(self, task: str) -> TaskClassification:
        prompt = _CLASSIFICATION_PROMPT.format(task=task)
        msg = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}],
        )
        block = msg.content[0]

        if not isinstance(block, TextBlock):
            raise ValueError(f"Expected TextBlock, got {type(block)}")
        
        raw = block.text.strip()
        # Strip markdown fences if present
        raw = re.sub(r"^```[a-z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)
        data = json.loads(raw)
        return TaskClassification(
            scope=data.get("scope", "diagnostic"),
            uncertainty=float(data.get("uncertainty", 0.5)),
            risk=float(data.get("risk", 0.2)),
            abstraction_need=int(data.get("abstraction_need", 2)),
            reasoning=data.get("reasoning", ""),
        )

    def _classify_heuristic(self, task: str) -> TaskClassification:
        task_lower = task.lower()
        if any(w in task_lower for w in ["debug", "fix", "error", "fail", "broken", "crash"]):
            return TaskClassification(scope="diagnostic", uncertainty=0.7,
                                      risk=0.2, abstraction_need=2)
        if any(w in task_lower for w in ["run", "execute", "test", "deploy", "install"]):
            return TaskClassification(scope="procedural", uncertainty=0.4,
                                      risk=0.2, abstraction_need=2)
        if any(w in task_lower for w in ["design", "plan", "architect", "decide"]):
            return TaskClassification(scope="strategic", uncertainty=0.8,
                                      risk=0.3, abstraction_need=3)
        if any(w in task_lower for w in ["delete", "drop", "remove", "security", "credential"]):
            return TaskClassification(scope="high_risk", uncertainty=0.5,
                                      risk=0.8, abstraction_need=4)
        return TaskClassification(scope="diagnostic", uncertainty=0.6,
                                  risk=0.2, abstraction_need=2)

    def should_retrieve_memory(self, classification: TaskClassification) -> bool:
        """Return True if past memory is likely to help."""
        return classification.uncertainty >= 0.3

    def compute_activation_score(
        self,
        node_strength: float,
        sim_score: float,
        node_level: int,
        level_band: tuple[int, int],
        node_use_count: int,
        node_failure_count: int,
    ) -> float:
        """
        Composite activation score from Section 6.1.1 (Eq. 2).
        Weights are v0 defaults; tune against task traces in production.
        """
        lo, hi = level_band
        in_band = 1.0 if lo <= node_level <= hi else 0.0
        if in_band == 0.0:
            return 0.0

        # Recency/frequency proxy: use_count with diminishing returns
        frequency = min(1.0, node_use_count / 20.0)

        # Failure penalty
        failure_ratio = (node_failure_count / max(1, node_use_count))
        risk_penalty = failure_ratio * 0.3

        score = (
            0.35 * sim_score
            + 0.30 * node_strength
            + 0.15 * frequency
            + 0.10 * in_band
            - risk_penalty
        )
        return max(0.0, score)
