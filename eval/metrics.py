from __future__ import annotations

from dataclasses import dataclass


@dataclass
class EpisodeMetrics:
    total_reward: float
    composite_efficiency: float
    efficacy: float
    safety: float
    compliance: float
    cost: float
    progress: float
    correction_triggers: int = 0
    stage_transitions: int = 0


def mean_metrics(rows: list[EpisodeMetrics]) -> dict[str, float]:
    if not rows:
        return {
            "total_reward": 0.0,
            "composite_efficiency": 0.0,
            "efficacy": 0.0,
            "safety": 0.0,
            "compliance": 0.0,
            "cost": 0.0,
            "progress": 0.0,
            "correction_triggers": 0.0,
            "stage_transitions": 0.0,
        }

    denom = float(len(rows))
    return {
        "total_reward": sum(r.total_reward for r in rows) / denom,
        "composite_efficiency": sum(r.composite_efficiency for r in rows) / denom,
        "efficacy": sum(r.efficacy for r in rows) / denom,
        "safety": sum(r.safety for r in rows) / denom,
        "compliance": sum(r.compliance for r in rows) / denom,
        "cost": sum(r.cost for r in rows) / denom,
        "progress": sum(r.progress for r in rows) / denom,
        "correction_triggers": sum(r.correction_triggers for r in rows) / denom,
        "stage_transitions": sum(r.stage_transitions for r in rows) / denom,
    }
