from cts.environment.models import Action, ActionType, TrialState
from cts.rewards.anti_cheat import validate_transition


def test_invalid_negative_budget_penalty_fires() -> None:
    state = TrialState(enrolled=2, active=2, cohort_target=10)
    next_state = TrialState(enrolled=2, active=2, cohort_target=10, budget_spent=-1)

    result = validate_transition(state, Action(ActionType.NOOP, 0.0), next_state)
    assert not result.valid
    assert result.penalty < 0
    assert result.terminate


def test_invalid_serious_event_count_penalty_fires() -> None:
    state = TrialState(enrolled=5, active=5, cohort_target=10)
    next_state = TrialState(enrolled=5, active=5, adverse_events=1, serious_adverse_events=2, cohort_target=10)

    result = validate_transition(state, Action(ActionType.NOOP, 0.0), next_state)
    assert not result.valid
    assert result.reason == "serious_exceeds_total_ae"


def test_clean_transition_passes() -> None:
    state = TrialState(enrolled=5, active=5, cohort_target=10)
    next_state = TrialState(enrolled=5, active=4, completed=1, adverse_events=0, serious_adverse_events=0, cohort_target=10)

    result = validate_transition(state, Action(ActionType.NOOP, 0.0), next_state)
    assert result.valid
    assert result.penalty == 0.0
