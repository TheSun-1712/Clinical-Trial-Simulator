from __future__ import annotations

from cts.config import RewardWeights
from cts.environment.models import Action, ActionType, TrialState


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


def risk_penalty(state: TrialState, action: Action, next_state: TrialState) -> float:
    ae_rate = next_state.adverse_events / max(next_state.enrolled, 1)
    severe_rate = next_state.serious_adverse_events / max(next_state.enrolled, 1)
    fatal_rate = next_state.fatal_reactions / max(next_state.enrolled, 1)
    raw = 0.35 * ae_rate + 0.75 * severe_rate + 1.5 * fatal_rate
    if next_state.fda_flag == "hold":
        raw += 0.25
    elif next_state.fda_flag == "warning":
        raw += 0.12
    return -max(0.0, min(1.0, raw))


def opportunity_cost_penalty(state: TrialState, action: Action, next_state: TrialState) -> float:
    # Lenient during the first 4 weeks of recruitment ramp-up
    if next_state.week < 4:
        if next_state.enrolled == 0:
            return -0.2
        return 0.1

    if next_state.enrolled == 0:
        return -1.0

    efficacy_gap = max(0.0, 0.55 - next_state.efficacy_signal)
    safety_pressure = max(0.0, next_state.serious_adverse_events / max(next_state.enrolled, 1) - 0.02)

    if next_state.fda_flag == "hold" and action.type not in {ActionType.HOLD_ENROLLMENT, ActionType.FILE_INTERIM_REPORT}:
        return -min(1.0, 0.35 + safety_pressure)

    if efficacy_gap > 0.1 and action.type in {ActionType.NOOP, ActionType.HOLD_ENROLLMENT}:
        return -min(1.0, 0.25 + efficacy_gap)

    return max(-0.2, 0.2 - 0.3 * efficacy_gap)


def composite_efficiency_score(components: dict[str, float]) -> float:
    efficacy = max(0.0, min(1.0, components.get("efficacy", 0.0)))
    safety = (max(-1.0, min(1.0, components.get("safety", 0.0))) + 1.0) / 2.0
    compliance = (max(-1.0, min(1.0, components.get("compliance", 0.0))) + 1.0) / 2.0
    cost = (max(-1.0, min(1.0, components.get("cost", 0.0))) + 1.0) / 2.0
    progress = max(0.0, min(1.0, components.get("progress", 0.0)))
    risk = (max(-1.0, min(1.0, components.get("risk", 0.0))) + 1.0) / 2.0
    opportunity = (max(-1.0, min(1.0, components.get("opportunity_cost", 0.0))) + 1.0) / 2.0
    return max(0.0, min(1.0, (efficacy + safety + compliance + cost + progress + (1.0 - risk) + opportunity) / 7.0))


def combine_reward(weights: RewardWeights, components: dict[str, float]) -> float:
    # Add a statistical precision bonus that scales with trial progress
    # Reward = (Power achieved) * (Fraction of trial completed)
    total = (
        weights.efficacy * components["efficacy"]
        + weights.safety * components["safety"]
        + weights.compliance * components["compliance"]
        + weights.cost * components["cost"]
        + weights.progress * components["progress"]
        + components["timeout"]
    )
    total += 0.08 * components.get("risk", 0.0)
    total += 0.40 * components.get("opportunity_cost", 0.0)
    return max(-1.0, min(1.0, total))


def reward_breakdown(weights: RewardWeights, state: TrialState, action: Action, next_state: TrialState) -> dict:
    components = {
        "efficacy": efficacy_score(state, action, next_state),
        "safety": safety_penalty(state, action, next_state),
        "compliance": compliance_score(state, action, next_state),
        "cost": cost_penalty(state, action, next_state),
        "progress": progress_bonus(state, action, next_state),
        "risk": risk_penalty(state, action, next_state),
        "opportunity_cost": opportunity_cost_penalty(state, action, next_state),
        "timeout": timeout_penalty(state, action, next_state),
    }
    total = combine_reward(weights, components)
    return {
        "components": components,
        "weights": weights.model_dump(),
        "total": total,
        "composite_efficiency": composite_efficiency_score(components),
    }
