from cts.config import default_config
from cts.environment.models import Action, ActionType
from cts.environment.trial_env import TrialEnv
from cts.config import EventRates, StageConfig, FDAConfig, RewardWeights
from cts.environment.models import DiseaseType
from cts.config import TrialConfig


def test_seeded_reset_and_step_are_deterministic() -> None:
    cfg = default_config()
    env_a = TrialEnv(cfg)
    env_b = TrialEnv(cfg)

    a0 = env_a.reset(seed=123)
    b0 = env_b.reset(seed=123)
    assert a0.observation == b0.observation

    action = Action(type=ActionType.RECRUIT, magnitude=3.0)
    a1 = env_a.step(action)
    b1 = env_b.step(action)

    assert a1.state == b1.state
    assert a1.observation == b1.observation


def test_episode_terminates_on_max_weeks() -> None:
    cfg = default_config()
    env = TrialEnv(cfg)
    env.reset(seed=7)

    final = None
    for _ in range(cfg.stage_config.max_weeks):
        final = env.step(Action(type=ActionType.NOOP, magnitude=0.0))
        if final.terminated or final.truncated:
            break

    assert final is not None
    assert final.truncated or final.terminated


def test_phase_promotion_and_correction_metadata_are_emitted() -> None:
    cfg = TrialConfig(
        stage="stage1",
        stage1=StageConfig(
            name="stage1",
            cohort_size=4,
            max_weeks=8,
            max_adverse_events=3,
            max_budget=100000,
            event_rates=EventRates(adverse_event_prob=0.0, serious_adverse_event_prob=0.0, dropout_prob=0.0),
            promotion_mean_reward=-1.0,
            promotion_window=1,
        ),
        stage2=StageConfig(
            name="stage2",
            cohort_size=8,
            max_weeks=10,
            max_adverse_events=4,
            max_budget=200000,
            event_rates=EventRates(adverse_event_prob=0.0, serious_adverse_event_prob=0.0, dropout_prob=0.0),
            promotion_mean_reward=-1.0,
            promotion_window=1,
        ),
        stage3=StageConfig(
            name="stage3",
            cohort_size=12,
            max_weeks=12,
            max_adverse_events=5,
            max_budget=300000,
            event_rates=EventRates(adverse_event_prob=0.0, serious_adverse_event_prob=0.0, dropout_prob=0.0),
            promotion_mean_reward=-1.0,
            promotion_window=1,
        ),
        reward_weights=RewardWeights(),
        fda=FDAConfig(warning_ae_rate=1.0, hold_ae_rate=1.0, efficacy_floor=0.0),
        disease=DiseaseType.TYPE2_DIABETES,
    )
    env = TrialEnv(cfg)
    env.reset(seed=11)

    result = env.step(Action(type=ActionType.NOOP, magnitude=0.0))

    assert result.state.stage_name == "stage2"
    assert result.state.stage_transition_count == 1
    assert "stage_transition" in result.info
    assert "correction" in result.info
    assert result.info["correction"]["trigger_count"] >= 1
