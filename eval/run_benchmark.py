from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
import random
from typing import Any

from cts.config import default_config
from cts.environment.models import Action, ActionType, DiseaseType
from cts.environment.trial_env import TrialEnv
from cts.policy_loader import PolicyLike, checkpoint_exists, load_any_policy_checkpoint, policy_checkpoint_type
from cts.rewards.verifiers import reward_breakdown
from eval.analytics import current_timestamp, save_benchmark_report
from eval.baselines import heuristic_policy_action, random_policy_action
from eval.metrics import EpisodeMetrics, mean_metrics


@dataclass
class PolicyResult:
    name: str
    metrics: dict[str, float]
    source: str


@dataclass
class EpisodeRunResult:
    metrics: EpisodeMetrics
    timeline: list[dict[str, Any]]


def run_episode(env: TrialEnv, seed: int, policy_name: str, trained_policy: PolicyLike | None = None) -> EpisodeRunResult:
    reset_result = env.reset(seed=seed)
    state = reset_result.state
    total_reward = 0.0
    latest = {
        "components": {
            "efficacy": 0.0,
            "safety": 0.0,
            "compliance": 0.0,
            "cost": 0.0,
            "progress": 0.0,
            "risk": 0.0,
            "opportunity_cost": 0.0,
        },
        "composite_efficiency": 0.0,
    }
    correction_triggers = 0
    stage_transitions = 0
    timeline: list[dict[str, Any]] = []

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
        rewards = result.info.get("reward") or reward_breakdown(env.config.reward_weights, state, action, next_state)
        total_reward += rewards["total"] + result.info["validation"]["penalty"]
        latest = rewards

        correction = result.info.get("correction", {})
        correction_triggers += int(correction.get("trigger_count", 0))
        correction_confidence = 0.0
        recommendations = correction.get("recommendations", [])
        if recommendations:
            correction_confidence = float(recommendations[0].get("confidence", 0.0))
        if result.info.get("stage_transition"):
            stage_transitions += 1

        timeline.append(
            {
                "policy": policy_name,
                "week": next_state.week,
                "stage": next_state.stage_name,
                "disease": next_state.disease.value,
                "action": action.type.value,
                "magnitude": action.magnitude,
                "total_reward": rewards["total"],
                "composite_efficiency": rewards.get("composite_efficiency", 0.0),
                "efficacy": rewards["components"]["efficacy"],
                "safety": rewards["components"]["safety"],
                "compliance": rewards["components"]["compliance"],
                "cost": rewards["components"]["cost"],
                "progress": rewards["components"]["progress"],
                "risk": rewards["components"]["risk"],
                "opportunity_cost": rewards["components"]["opportunity_cost"],
                "fda_flag": next_state.fda_flag,
                "fda_sentiment": next_state.fda_sentiment,
                "correction_rule_id": correction.get("primary_rule_id"),
                "correction_confidence": correction_confidence,
                "correction_trigger_count": correction.get("trigger_count", 0),
                "stage_transition": bool(result.info.get("stage_transition")),
                "enrolled": next_state.enrolled,
                "active": next_state.active,
                "completed": next_state.completed,
                "adverse_events": next_state.adverse_events,
                "serious_adverse_events": next_state.serious_adverse_events,
                "budget_spent": next_state.budget_spent,
            }
        )

        state = next_state
        if result.terminated or result.truncated:
            break

    return EpisodeRunResult(
        metrics=EpisodeMetrics(
            total_reward=total_reward,
            composite_efficiency=latest["composite_efficiency"],
            efficacy=latest["components"]["efficacy"],
            safety=latest["components"]["safety"],
            compliance=latest["components"]["compliance"],
            cost=latest["components"]["cost"],
            progress=latest["components"]["progress"],
            correction_triggers=correction_triggers,
            stage_transitions=stage_transitions,
        ),
        timeline=timeline,
    )


def _load_trained_policy(path: str | None) -> tuple[PolicyLike | None, str]:
    if not path:
        return None, "fallback_heuristic"
    if not checkpoint_exists(path):
        return None, "fallback_heuristic"
    try:
        policy = load_any_policy_checkpoint(path)
        return policy, f"checkpoint:{policy_checkpoint_type(path)}:{Path(path)}"
    except Exception as exc:
        return None, f"fallback_heuristic:{type(exc).__name__}"


def _aggregate_timeline(timeline: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    buckets: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for row in timeline:
        key = f"{row.get('disease', 'unknown')}:{row.get('stage', 'unknown')}"
        buckets[key]["composite_efficiency"].append(float(row.get("composite_efficiency", 0.0)))
        buckets[key]["total_reward"].append(float(row.get("total_reward", 0.0)))
        buckets[key]["correction_trigger_count"].append(float(row.get("correction_trigger_count", 0.0)))
    return {
        key: {
            metric: (sum(values) / len(values) if values else 0.0)
            for metric, values in metric_map.items()
        }
        for key, metric_map in buckets.items()
    }


def run_benchmark(episodes: int = 50, trained_checkpoint: str | None = None, output_dir: str | None = None) -> list[PolicyResult]:
    config = default_config()
    policies = ["random", "heuristic", "trained"]
    results: list[PolicyResult] = []
    trained_policy, trained_source = _load_trained_policy(trained_checkpoint)
    disease_values = list(DiseaseType)
    episodes_per_disease = max(1, episodes // len(disease_values))

    policy_rows: list[dict[str, Any]] = []
    disease_metrics: dict[str, dict[str, dict[str, float]]] = {}
    phase_metrics: dict[str, dict[str, dict[str, float]]] = {}
    correction_summary: dict[str, float] = {}
    timeline_rows: list[dict[str, Any]] = []

    for policy in policies:
        overall_rows: list[EpisodeMetrics] = []
        per_disease: dict[str, list[EpisodeMetrics]] = {}
        per_stage: dict[str, list[float]] = defaultdict(list)
        correction_counts: list[float] = []

        for disease_index, disease in enumerate(disease_values):
            env = TrialEnv(config.model_copy(update={"disease": disease}))
            disease_rows: list[EpisodeMetrics] = []
            for episode_index in range(episodes_per_disease):
                run = run_episode(env, seed=1000 + disease_index * 100 + episode_index, policy_name=policy, trained_policy=trained_policy)
                disease_rows.append(run.metrics)
                overall_rows.append(run.metrics)
                correction_counts.append(float(run.metrics.correction_triggers))
                timeline_rows.extend(run.timeline)
                for point in run.timeline:
                    per_stage[str(point.get("stage", "unknown"))].append(float(point.get("composite_efficiency", 0.0)))
            per_disease[disease.value] = disease_rows

        source = "builtin" if policy != "trained" else trained_source
        overall_metrics = mean_metrics(overall_rows)
        results.append(PolicyResult(name=policy, metrics=overall_metrics, source=source))
        policy_rows.append({"policy": policy, "source": source, **overall_metrics})
        disease_metrics[policy] = {disease_name: mean_metrics(rows) for disease_name, rows in per_disease.items()}
        phase_metrics[policy] = {
            stage_name: {
                "composite_efficiency": (sum(values) / len(values) if values else 0.0),
                "support": float(len(values)),
            }
            for stage_name, values in per_stage.items()
        }
        correction_summary[policy] = sum(correction_counts) / len(correction_counts) if correction_counts else 0.0

    report = {
        "generated_at": current_timestamp(),
        "overall": {"episodes": episodes, "policies": [row["policy"] for row in policy_rows]},
        "stage_config": {
            "stage1": config.stage1.model_dump(),
            "stage2": config.stage2.model_dump(),
            "stage3": config.stage3.model_dump(),
        },
        "policy_rows": policy_rows,
        "disease_metrics": disease_metrics,
        "phase_metrics": phase_metrics,
        "correction_summary": correction_summary,
        "timeline": timeline_rows,
        "timeline_summary": _aggregate_timeline(timeline_rows),
    }
    save_benchmark_report(report, output_dir)
    return results


def compare_trained_vs_heuristic(
    episodes: int,
    trained_checkpoint: str,
    output_dir: str | None = None,
) -> dict[str, float | bool]:
    rows = run_benchmark(episodes=episodes, trained_checkpoint=trained_checkpoint, output_dir=output_dir)
    by_name = {row.name: row.metrics for row in rows}
    trained_total = float(by_name.get("trained", {}).get("total_reward", 0.0))
    heuristic_total = float(by_name.get("heuristic", {}).get("total_reward", 0.0))
    return {
        "episodes": float(episodes),
        "trained_total_reward": trained_total,
        "heuristic_total_reward": heuristic_total,
        "trained_worse_than_heuristic": trained_total < heuristic_total,
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run benchmark across random/heuristic/trained policies")
    parser.add_argument("--episodes", type=int, default=50)
    parser.add_argument("--trained-checkpoint", default="artifacts/policy/latest.json")
    parser.add_argument("--output-dir", default="artifacts/benchmark")
    args = parser.parse_args()

    table = run_benchmark(episodes=args.episodes, trained_checkpoint=args.trained_checkpoint, output_dir=args.output_dir)
    for row in table:
        print(f"{row.name:10s} {row.metrics} source={row.source}")
