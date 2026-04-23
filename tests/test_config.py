from pydantic import ValidationError

from cts.config import RewardWeights, TrialConfig


def test_reward_weights_sum_to_one() -> None:
    weights = RewardWeights()
    assert abs(sum(weights.model_dump().values()) - 1.0) < 1e-9


def test_reward_weights_invalid_sum() -> None:
    try:
        RewardWeights(efficacy=0.5, safety=0.5, compliance=0.5, cost=0.0, progress=0.0)
        assert False, "Expected ValidationError"
    except ValidationError:
        assert True


def test_trial_config_stage_access() -> None:
    cfg = TrialConfig(stage="stage2")
    assert cfg.stage_config.name == "stage2"
    assert cfg.stage_config.cohort_size == 30
