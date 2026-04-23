from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass
from pathlib import Path

from cts.config import TrialConfig
from cts.environment.models import Action, ActionType, TrialState


@dataclass
class ActionTemplate:
    action_type: ActionType
    magnitude: float


ACTION_LIBRARY: list[ActionTemplate] = [
    ActionTemplate(ActionType.RECRUIT, 1.0),
    ActionTemplate(ActionType.RECRUIT, 2.0),
    ActionTemplate(ActionType.RECRUIT, 3.0),
    ActionTemplate(ActionType.ADJUST_DOSE, -0.1),
    ActionTemplate(ActionType.ADJUST_DOSE, 0.1),
    ActionTemplate(ActionType.HOLD_ENROLLMENT, 0.0),
    ActionTemplate(ActionType.FILE_INTERIM_REPORT, 0.0),
    ActionTemplate(ActionType.IMPLEMENT_AMENDMENT, 0.0),
    ActionTemplate(ActionType.NOOP, 0.0),
]


def feature_vector(state: TrialState, config: TrialConfig) -> list[float]:
    stage = config.stage_config
    return [
        1.0,
        min(1.0, state.week / max(stage.max_weeks, 1)),
        min(1.0, state.enrolled / max(state.cohort_target, 1)),
        min(1.0, state.active / max(state.cohort_target, 1)),
        min(1.0, state.completed / max(state.cohort_target, 1)),
        min(1.0, state.adverse_events / max(stage.max_adverse_events, 1)),
        min(1.0, state.serious_adverse_events / max(stage.max_adverse_events, 1)),
        min(1.0, state.budget_spent / max(stage.max_budget, 1.0)),
        min(1.0, max(0.0, state.efficacy_signal)),
        min(1.0, max(-1.0, state.fda_sentiment) + 1.0) / 2.0,
        1.0 if state.recruitment_hold else 0.0,
    ]


@dataclass
class LinearPolicy:
    weights: list[list[float]]

    @property
    def num_actions(self) -> int:
        return len(self.weights)

    @property
    def num_features(self) -> int:
        return len(self.weights[0]) if self.weights else 0

    def logits(self, features: list[float]) -> list[float]:
        return [sum(w * x for w, x in zip(row, features)) for row in self.weights]

    def probabilities(self, features: list[float], temperature: float = 1.0) -> list[float]:
        t = max(0.05, temperature)
        scores = [value / t for value in self.logits(features)]
        max_score = max(scores)
        exps = [math.exp(score - max_score) for score in scores]
        denom = sum(exps)
        return [value / denom for value in exps]

    def select_index(self, features: list[float], rng: random.Random, stochastic: bool = True) -> int:
        probs = self.probabilities(features)
        if not stochastic:
            return max(range(len(probs)), key=lambda idx: probs[idx])

        threshold = rng.random()
        cumulative = 0.0
        for idx, prob in enumerate(probs):
            cumulative += prob
            if cumulative >= threshold:
                return idx
        return len(probs) - 1

    def select_action(self, state: TrialState, config: TrialConfig, rng: random.Random, stochastic: bool = True) -> Action:
        features = feature_vector(state, config)
        index = self.select_index(features, rng, stochastic=stochastic)
        template = ACTION_LIBRARY[index]
        return Action(type=template.action_type, magnitude=template.magnitude)


def init_zero_policy() -> LinearPolicy:
    n_features = 11
    return LinearPolicy(weights=[[0.0 for _ in range(n_features)] for _ in ACTION_LIBRARY])


def save_policy_checkpoint(policy: LinearPolicy, path: str, metadata: dict | None = None) -> None:
    payload = {
        "format_version": 1,
        "policy_type": "linear_softmax",
        "weights": policy.weights,
        "action_library": [{"type": action.action_type.value, "magnitude": action.magnitude} for action in ACTION_LIBRARY],
        "metadata": metadata or {},
    }
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_policy_checkpoint(path: str) -> LinearPolicy:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("policy_type") != "linear_softmax":
        raise ValueError("Unsupported checkpoint policy type")
    return LinearPolicy(weights=payload["weights"])


def checkpoint_exists(path: str) -> bool:
    return Path(path).exists()
