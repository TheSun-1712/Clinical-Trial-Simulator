from cts.config import default_config
from cts.environment.models import Action, ActionType
from cts.environment.trial_env import TrialEnv


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
