from __future__ import annotations

from dataclasses import dataclass


@dataclass
class EpisodeMetrics:
    total_reward: float
    efficacy: float
    safety: float
    compliance: float
    cost: float
    progress: float


def mean_metrics(rows: list[EpisodeMetrics]) -> dict[str, float]:
    if not rows:
        return {"total_reward": 0.0, "efficacy": 0.0, "safety": 0.0, "compliance": 0.0, "cost": 0.0, "progress": 0.0}

    denom = float(len(rows))
    return {
        "total_reward": sum(r.total_reward for r in rows) / denom,
        "efficacy": sum(r.efficacy for r in rows) / denom,
        "safety": sum(r.safety for r in rows) / denom,
        "compliance": sum(r.compliance for r in rows) / denom,
        "cost": sum(r.cost for r in rows) / denom,
        "progress": sum(r.progress for r in rows) / denom,
    }
