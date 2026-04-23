from __future__ import annotations

from dataclasses import dataclass

from cts.environment.models import Action, TrialState
from cts.environment.models import ActionType


@dataclass
class TransitionValidationResult:
    valid: bool
    penalty: float
    reason: str
    terminate: bool


def validate_transition(state: TrialState, action: Action, next_state: TrialState) -> TransitionValidationResult:
    if next_state.enrolled < 0 or next_state.active < 0:
        return TransitionValidationResult(False, -1.0, "negative_population", True)

    if next_state.enrolled < state.enrolled:
        return TransitionValidationResult(False, -1.0, "enrolled_decreased", True)

    if next_state.budget_spent < 0:
        return TransitionValidationResult(False, -1.0, "negative_budget", True)

    if next_state.serious_adverse_events > next_state.adverse_events:
        return TransitionValidationResult(False, -1.0, "serious_exceeds_total_ae", True)

    if next_state.fatal_reactions > next_state.serious_adverse_events:
        return TransitionValidationResult(False, -1.0, "fatal_exceeds_serious", True)

    if next_state.major_reactions + next_state.minor_reactions + next_state.fatal_reactions > max(next_state.enrolled, next_state.sample_batch_size):
        return TransitionValidationResult(False, -0.9, "reaction_histogram_invalid", True)

    if len(next_state.adverse_event_log) < len(state.adverse_event_log):
        return TransitionValidationResult(False, -0.8, "ae_log_rewind", True)

    if action.type == ActionType.RECRUIT and state.recruitment_hold and next_state.enrolled > state.enrolled:
        return TransitionValidationResult(False, -0.8, "recruit_while_hold", True)

    max_expected_delta = max(1, state.cohort_target // 2)
    if (next_state.enrolled - state.enrolled) > max_expected_delta:
        return TransitionValidationResult(False, -0.8, "cohort_jump", True)

    composition_sum = sum(next_state.composition.values())
    if abs(composition_sum - 1.0) > 1e-6:
        return TransitionValidationResult(False, -0.8, "composition_not_normalized", True)

    for key, value in next_state.composition.items():
        if value < 0.0 or value > 1.0:
            return TransitionValidationResult(False, -0.8, f"composition_bound_violation:{key}", True)

    return TransitionValidationResult(True, 0.0, "ok", False)
