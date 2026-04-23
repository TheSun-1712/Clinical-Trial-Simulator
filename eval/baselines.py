from __future__ import annotations

from cts.environment.models import Action, ActionType, TrialState


def random_policy_action(seed_value: int) -> Action:
    # Deterministic random baseline action from integer stream.
    action_types = [
        ActionType.RECRUIT,
        ActionType.ADJUST_DOSE,
        ActionType.HOLD_ENROLLMENT,
        ActionType.FILE_INTERIM_REPORT,
        ActionType.IMPLEMENT_AMENDMENT,
        ActionType.NOOP,
    ]
    idx = seed_value % len(action_types)
    magnitude = ((seed_value % 7) - 3) / 10.0
    if action_types[idx] == ActionType.RECRUIT:
        magnitude = float((seed_value % 4) + 1)
    return Action(type=action_types[idx], magnitude=magnitude)


def heuristic_policy_action(state: TrialState) -> Action:
    # Heuristic baseline: recruit up to safe limits, pause when any AE appears.
    if state.adverse_events > 0 or state.fda_flag == "warning":
        return Action(type=ActionType.HOLD_ENROLLMENT, magnitude=0.0)

    if state.enrolled < state.cohort_target:
        return Action(type=ActionType.RECRUIT, magnitude=3.0)

    if state.fda_flag == "hold":
        return Action(type=ActionType.FILE_INTERIM_REPORT, magnitude=0.0)

    return Action(type=ActionType.NOOP, magnitude=0.0)
