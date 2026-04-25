from cts.agents.correction_agent import recommendation_rule_ids, recommend_corrections
from cts.environment.models import Action, ActionType, TrialState


def test_correction_agent_prioritizes_holds_on_fda_hold() -> None:
    state = TrialState(enrolled=4, active=4, stage_name="stage1")
    action = Action(type=ActionType.NOOP, magnitude=0.0)
    next_state = TrialState(
        enrolled=4,
        active=4,
        stage_name="stage1",
        fda_flag="hold",
        fda_sentiment=-1.0,
        serious_adverse_events=2,
        adverse_events=3,
    )

    payload = recommend_corrections(state, action, next_state)

    assert payload["trigger_count"] >= 1
    assert payload["recommendations"][0]["action"] == ActionType.HOLD_ENROLLMENT.value
    assert payload["primary_rule_id"] == "SAFETY_HOLD"
    assert list(recommendation_rule_ids(payload))


def test_correction_agent_emits_stability_recommendation_when_clean() -> None:
    state = TrialState(enrolled=10, active=5, stage_name="stage2", composite_efficiency=0.85, efficacy_signal=0.9)
    action = Action(type=ActionType.RECRUIT, magnitude=2.0)
    next_state = TrialState(enrolled=10, active=5, stage_name="stage2", composite_efficiency=0.85, efficacy_signal=0.9)

    payload = recommend_corrections(state, action, next_state)

    assert payload["trigger_count"] >= 1
    assert payload["recommendations"][0]["rule_id"] == "STABLE_CONTINUE"
