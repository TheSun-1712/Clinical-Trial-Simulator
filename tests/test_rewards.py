from cts.config import default_config
from cts.environment.models import Action, ActionType, TrialState
from cts.rewards.verifiers import combine_reward, reward_breakdown


def test_reward_components_and_total_match_manual() -> None:
    cfg = default_config()
    state = TrialState(cohort_target=10)
    action = Action(type=ActionType.NOOP, magnitude=0.0)
    next_state = TrialState(
        week=5,
        cohort_target=10,
        enrolled=10,
        active=4,
        completed=4,
        adverse_events=1,
        serious_adverse_events=0,
        budget_spent=50000,
        efficacy_signal=0.7,
        fda_sentiment=0.2,
        fda_flag="monitoring",
    )

    rb = reward_breakdown(cfg.reward_weights, state, action, next_state)
    manual = combine_reward(cfg.reward_weights, rb["components"])
    assert abs(rb["total"] - manual) < 1e-9


def test_reward_edge_case_no_patients() -> None:
    cfg = default_config()
    state = TrialState(cohort_target=10)
    action = Action(type=ActionType.NOOP, magnitude=0.0)
    next_state = TrialState(cohort_target=10)

    rb = reward_breakdown(cfg.reward_weights, state, action, next_state)
    assert rb["components"]["safety"] == 0.0
    assert rb["components"]["cost"] <= 0.0
