from __future__ import annotations

from cts.environment.models import Action, ActionType, TrialState


def random_policy_action(seed_value: int) -> Action:
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
    """
    Multi-priority clinical trial policy:
    1. Safety: never let serious AEs exceed 4 without pausing
    2. Enrollment: aggressively recruit until cohort target is met
    3. Dose optimisation: adjust up when efficacy is low, down when toxicity rises
    4. Composition update: every 5 composition iterations, rebalance A/B/C
    5. Regulatory: file interim report ONLY once when FDA flag turns 'hold'
    6. NOOP otherwise — never infinitely loop on FILE_INTERIM_REPORT
    """
    # --- Safety gate ---
    if state.serious_adverse_events > 4:
        return Action(type=ActionType.HOLD_ENROLLMENT, magnitude=0.0)

    # --- Regulatory: file report ONLY when not yet filed for this hold ---
    # Cap at 1 report per 8 weeks to prevent spam
    if state.fda_flag == "hold" and state.interim_reports_filed == 0:
        return Action(type=ActionType.FILE_INTERIM_REPORT, magnitude=0.0)
    if state.fda_flag == "hold" and state.week % 8 == 0:
        return Action(type=ActionType.FILE_INTERIM_REPORT, magnitude=0.0)

    # --- Recruitment: primary goal until cohort target ---
    if state.enrolled < state.cohort_target:
        # Recruit aggressively in batches of 3-5
        batch = min(5, state.cohort_target - state.enrolled)
        return Action(type=ActionType.RECRUIT, magnitude=float(batch))

    # --- Implement amendment when FDA sentiment is poor ---
    if state.fda_sentiment < -0.3 and state.fda_flag == "warning":
        return Action(type=ActionType.IMPLEMENT_AMENDMENT, magnitude=0.0)

    # --- Composition update: rebalance every 6 steps ---
    if state.composition_iteration % 6 == 0 and state.composition_iteration > 0:
        # Shift weight toward the highest-reward component
        new_comp = {
            "a": round(min(0.6, state.composition.get("a", 0.34) + 0.05), 3),
            "b": round(max(0.1, state.composition.get("b", 0.33) - 0.03), 3),
            "c": round(max(0.1, state.composition.get("c", 0.33) - 0.02), 3),
        }
        return Action(type=ActionType.UPDATE_COMPOSITION, magnitude=0.0, composition=new_comp)

    # --- Dose optimisation ---
    if state.efficacy_signal < 0.55 and state.dose_level < 1.5:
        return Action(type=ActionType.ADJUST_DOSE, magnitude=0.1)
    if state.cumulative_toxicity > 0.35 and state.dose_level > 0.6:
        return Action(type=ActionType.ADJUST_DOSE, magnitude=-0.1)

    # --- Default: wait one week (never repeat file_interim_report endlessly) ---
    return Action(type=ActionType.NOOP, magnitude=0.0)
