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

    if len(next_state.adverse_event_log) < len(state.adverse_event_log):
        return TransitionValidationResult(False, -0.8, "ae_log_rewind", True)

    if action.type == ActionType.RECRUIT and state.recruitment_hold and next_state.enrolled > state.enrolled:
        return TransitionValidationResult(False, -0.8, "recruit_while_hold", True)

    max_expected_delta = max(1, state.cohort_target // 2)
    if (next_state.enrolled - state.enrolled) > max_expected_delta:
        return TransitionValidationResult(False, -0.8, "cohort_jump", True)

    return TransitionValidationResult(True, 0.0, "ok", False)
