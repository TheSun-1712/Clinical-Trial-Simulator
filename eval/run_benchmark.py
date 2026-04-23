from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import random

from cts.config import default_config
from cts.environment.models import Action, ActionType
from cts.environment.trial_env import TrialEnv
from cts.policy import LinearPolicy, checkpoint_exists, load_policy_checkpoint
from cts.rewards.verifiers import reward_breakdown
from eval.baselines import heuristic_policy_action, random_policy_action
from eval.metrics import EpisodeMetrics, mean_metrics


@dataclass
class PolicyResult:
    name: str
    metrics: dict[str, float]
    source: str


def run_episode(env: TrialEnv, seed: int, policy_name: str, trained_policy: LinearPolicy | None = None) -> EpisodeMetrics:
    reset_result = env.reset(seed=seed)
    state = reset_result.state
    total_reward = 0.0
    latest = {"components": {"efficacy": 0.0, "safety": 0.0, "compliance": 0.0, "cost": 0.0, "progress": 0.0}}

    for step_idx in range(env.config.stage_config.max_weeks):
        if policy_name == "random":
            action = random_policy_action(seed + step_idx)
        elif policy_name == "heuristic":
            action = heuristic_policy_action(state)
        else:
            if trained_policy is None:
                action = heuristic_policy_action(state)
            else:
                action = trained_policy.select_action(
                    state,
                    env.config,
                    rng=random.Random(seed * 1000 + step_idx),
                    stochastic=False,
                )

        result = env.step(action)
        next_state = result.state
        rewards = reward_breakdown(env.config.reward_weights, state, action, next_state)
        total_reward += rewards["total"] + result.info["validation"]["penalty"]
        latest = rewards

        state = next_state
        if result.terminated or result.truncated:
            break

    return EpisodeMetrics(
        total_reward=total_reward,
        efficacy=latest["components"]["efficacy"],
        safety=latest["components"]["safety"],
        compliance=latest["components"]["compliance"],
        cost=latest["components"]["cost"],
        progress=latest["components"]["progress"],
    )


def _load_trained_policy(path: str | None) -> tuple[LinearPolicy | None, str]:
    if not path:
        return None, "fallback_heuristic"
    if not checkpoint_exists(path):
        return None, "fallback_heuristic"
    policy = load_policy_checkpoint(path)
    return policy, f"checkpoint:{Path(path)}"


def run_benchmark(episodes: int = 50, trained_checkpoint: str | None = None) -> list[PolicyResult]:
    config = default_config()
    policies = ["random", "heuristic", "trained"]
    results: list[PolicyResult] = []
    trained_policy, trained_source = _load_trained_policy(trained_checkpoint)

    for policy in policies:
        env = TrialEnv(config)
        rows = [run_episode(env, seed=1000 + i, policy_name=policy, trained_policy=trained_policy) for i in range(episodes)]
        source = "builtin" if policy != "trained" else trained_source
        results.append(PolicyResult(name=policy, metrics=mean_metrics(rows), source=source))

    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run benchmark across random/heuristic/trained policies")
    parser.add_argument("--episodes", type=int, default=50)
    parser.add_argument("--trained-checkpoint", default="artifacts/policy/latest.json")
    args = parser.parse_args()

    table = run_benchmark(episodes=args.episodes, trained_checkpoint=args.trained_checkpoint)
    for row in table:
        print(f"{row.name:10s} {row.metrics} source={row.source}")
