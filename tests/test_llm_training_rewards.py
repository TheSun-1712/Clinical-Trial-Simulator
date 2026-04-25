from __future__ import annotations

from training.train_grpo import _env_rollout_reward, _heuristic_reward


def _prompt(**overrides: str) -> str:
    payload = {
        "week": "4",
        "enrolled": "3",
        "active": "2",
        "completed": "1",
        "adverse_events": "0",
        "serious_adverse_events": "0",
        "budget_spent": "1000.0",
        "dose_level": "1.0",
        "efficacy_signal": "0.6",
        "recruitment_hold": "0",
        "fda_flag": "monitoring",
        "fda_sentiment": "0.2",
    }
    payload.update(overrides)
    return (
        "State: "
        + ", ".join(f"{key}={value}" for key, value in payload.items())
        + "."
    )


def test_reward_prefers_valid_json() -> None:
    prompt = _prompt()
    good = _heuristic_reward(prompt, '{"action_type":"recruit","magnitude":2.0}')
    bad = _heuristic_reward(prompt, "action_type=recruit magnitude=2.0")
    assert good > bad


def test_reward_penalizes_unsafe_recruitment() -> None:
    prompt = _prompt(recruitment_hold="1", serious_adverse_events="1", fda_flag="warning")
    unsafe = _heuristic_reward(prompt, '{"action_type":"recruit","magnitude":2.0}')
    safe = _heuristic_reward(prompt, '{"action_type":"file_interim_report","magnitude":0.0}')
    assert unsafe < safe


def test_reward_prefers_dose_reduction_in_safety_risk() -> None:
    prompt = _prompt(serious_adverse_events="2", fda_flag="hold")
    reduce_dose = _heuristic_reward(prompt, '{"action_type":"adjust_dose","magnitude":-0.2}')
    increase_dose = _heuristic_reward(prompt, '{"action_type":"adjust_dose","magnitude":0.2}')
    assert reduce_dose > increase_dose


def test_env_rollout_reward_is_bounded() -> None:
    prompt = _prompt(serious_adverse_events="1", fda_flag="warning")
    score = _env_rollout_reward(
        prompt,
        '{"action_type":"file_interim_report","magnitude":0.0}',
        rollout_steps=2,
        seed=17,
    )
    assert -1.0 <= score <= 1.0

