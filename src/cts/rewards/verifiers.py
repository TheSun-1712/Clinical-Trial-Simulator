from __future__ import annotations

from cts.config import RewardWeights
from cts.environment.models import Action, TrialState


def efficacy_score(state: TrialState, action: Action, next_state: TrialState) -> float:
    blended = 0.65 * next_state.efficacy_signal + 0.35 * next_state.biomarker_improvement
    return max(0.0, min(1.0, blended))


def safety_penalty(state: TrialState, action: Action, next_state: TrialState) -> float:
    if next_state.enrolled == 0:
        return 0.0
    ae_rate = next_state.adverse_events / next_state.enrolled
    severe_rate = next_state.serious_adverse_events / next_state.enrolled
    fatal_rate = next_state.fatal_reactions / next_state.enrolled
    reviewer_multiplier = 1.0 + max(0.0, -next_state.fda_sentiment)
    penalty = (0.45 * ae_rate + 1.25 * severe_rate + 2.5 * fatal_rate) * reviewer_multiplier
    return -max(0.0, min(1.0, penalty))


def compliance_score(state: TrialState, action: Action, next_state: TrialState) -> float:
    if next_state.fda_flag == "hold":
        return -1.0
    if next_state.fda_flag == "warning":
        return -0.4
    incidents = next_state.compliance_incidents
    return max(-1.0, 0.5 - 0.1 * incidents)


def cost_penalty(state: TrialState, action: Action, next_state: TrialState) -> float:
    budget = max(1.0, next_state.budget_spent)
    if next_state.enrolled == 0:
        return -0.2
    unit_cost = budget / next_state.enrolled
    normalized = min(1.0, unit_cost / 20000.0)
    return -normalized


def progress_bonus(state: TrialState, action: Action, next_state: TrialState) -> float:
    progression = (next_state.completed + 0.5 * next_state.active) / max(next_state.cohort_target, 1)
    compositional_learning = min(1.0, next_state.composition_iteration / max(1.0, next_state.week + 1))
    progress = 0.8 * progression + 0.2 * compositional_learning
    return max(0.0, min(1.0, progress))


def timeout_penalty(state: TrialState, action: Action, next_state: TrialState) -> float:
    if next_state.week <= 0:
        return 0.0
    if next_state.week > 0 and next_state.completed == 0 and next_state.week >= 8:
        return -0.5
    return 0.0


def combine_reward(weights: RewardWeights, components: dict[str, float]) -> float:
    return (
        weights.efficacy * components["efficacy"]
        + weights.safety * components["safety"]
        + weights.compliance * components["compliance"]
        + weights.cost * components["cost"]
        + weights.progress * components["progress"]
        + components["timeout"]
    )


def reward_breakdown(weights: RewardWeights, state: TrialState, action: Action, next_state: TrialState) -> dict:
    components = {
        "efficacy": efficacy_score(state, action, next_state),
        "safety": safety_penalty(state, action, next_state),
        "compliance": compliance_score(state, action, next_state),
        "cost": cost_penalty(state, action, next_state),
        "progress": progress_bonus(state, action, next_state),
        "timeout": timeout_penalty(state, action, next_state),
    }
    total = combine_reward(weights, components)
    return {
        "components": components,
        "weights": weights.model_dump(),
        "total": total,
    }
