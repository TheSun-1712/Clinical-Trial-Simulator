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
    # Dynamic heuristic baseline: recruit bravely, adjust doses, and file reports to show off the UI.
    if state.fda_flag == "hold":
        return Action(type=ActionType.FILE_INTERIM_REPORT, magnitude=0.0)
        
    if state.serious_adverse_events > 3 or state.fda_flag == "warning":
        return Action(type=ActionType.HOLD_ENROLLMENT, magnitude=0.0)

    if state.enrolled < state.cohort_target:
        return Action(type=ActionType.RECRUIT, magnitude=5.0)

    if state.efficacy_signal < 0.6 and state.dose_level < 1.4:
        return Action(type=ActionType.ADJUST_DOSE, magnitude=0.1)
    elif state.cumulative_toxicity > 0.3:
        return Action(type=ActionType.ADJUST_DOSE, magnitude=-0.1)

    return Action(type=ActionType.NOOP, magnitude=0.0)
