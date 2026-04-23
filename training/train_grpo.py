from __future__ import annotations

import argparse
import ast
import json
import random
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cts.config import default_config
from cts.environment.models import Action, ActionType, TrialState
from cts.environment.trial_env import TrialEnv
from cts.policy import ACTION_LIBRARY, LinearPolicy, feature_vector, init_zero_policy, save_policy_checkpoint
from cts.rewards.verifiers import reward_breakdown


@dataclass
class Transition:
    features: list[float]
    action_index: int


@dataclass
class EpisodeRollout:
    total_reward: float
    transitions: list[Transition]


def _load_config_file(path: str) -> dict[str, Any]:
    config: dict[str, Any] = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        key, _, value = stripped.partition(":")
        if not _:
            continue
        raw = value.strip()
        if raw.lower() in {"true", "false"}:
            config[key.strip()] = raw.lower() == "true"
            continue
        try:
            if "." in raw or "e" in raw.lower():
                config[key.strip()] = float(raw)
            else:
                config[key.strip()] = int(raw)
            continue
        except ValueError:
            config[key.strip()] = raw
    return config


def _state_to_prompt(state: TrialState) -> str:
    return (
        "You are a clinical trial coordinator. "
        "Return JSON only with keys action_type and magnitude.\n"
        "Allowed action_type values: recruit, adjust_dose, hold_enrollment, file_interim_report, implement_amendment, noop.\n"
        f"State: week={state.week}, enrolled={state.enrolled}, active={state.active}, completed={state.completed}, "
        f"adverse_events={state.adverse_events}, serious_adverse_events={state.serious_adverse_events}, "
        f"budget_spent={state.budget_spent:.2f}, dose_level={state.dose_level:.3f}, "
        f"efficacy_signal={state.efficacy_signal:.3f}, recruitment_hold={int(state.recruitment_hold)}, "
        f"fda_flag={state.fda_flag}, fda_sentiment={state.fda_sentiment:.3f}."
    )


def _parse_state_from_prompt(prompt: str) -> dict[str, str]:
    state_marker = "State:"
    if state_marker not in prompt:
        return {}
    raw = prompt.split(state_marker, 1)[1]
    parts = [chunk.strip() for chunk in raw.split(",")]
    parsed: dict[str, str] = {}
    for part in parts:
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        parsed[key.strip()] = value.strip().rstrip(".")
    return parsed


def _parse_action_from_text(text: str) -> tuple[str, float, float]:
    """Returns action_type, magnitude, format_score."""
    body = text.strip()
    format_score = 0.0
    if body.startswith("```"):
        body = body.strip("`")
    action_type = "noop"
    magnitude = 0.0
    try:
        candidate = ast.literal_eval(body)
        if isinstance(candidate, dict):
            action_type = str(candidate.get("action_type", "noop")).strip().lower()
            magnitude = float(candidate.get("magnitude", 0.0))
            format_score = 1.0
    except Exception:
        match_type = re.search(r"action_type\s*[:=]\s*([a-z_]+)", body.lower())
        match_mag = re.search(r"magnitude\s*[:=]\s*(-?\d+(?:\.\d+)?)", body.lower())
        if match_type:
            action_type = match_type.group(1)
            format_score = 0.4
        if match_mag:
            magnitude = float(match_mag.group(1))
            format_score = max(format_score, 0.4)
    return action_type, magnitude, format_score


def _heuristic_reward(prompt: str, completion_text: str) -> float:
    state = _parse_state_from_prompt(prompt)
    action_type, magnitude, format_score = _parse_action_from_text(completion_text)

    reward = 0.2 * format_score
    valid_actions = {a.value for a in ActionType}
    if action_type not in valid_actions:
        return reward - 0.8

    enrolled = float(state.get("enrolled", "0"))
    cohort_target = 10.0
    adverse_events = float(state.get("adverse_events", "0"))
    serious_adverse_events = float(state.get("serious_adverse_events", "0"))
    efficacy_signal = float(state.get("efficacy_signal", "0"))
    recruitment_hold = int(float(state.get("recruitment_hold", "0")))
    fda_flag = state.get("fda_flag", "monitoring")

    if action_type == "recruit":
        if recruitment_hold == 1:
            reward -= 0.7
        elif enrolled < cohort_target:
            reward += 0.5
        else:
            reward -= 0.2
        reward += 0.1 if 0.5 <= magnitude <= 3.5 else -0.1

    elif action_type == "hold_enrollment":
        if adverse_events > 0 or serious_adverse_events > 0 or fda_flag == "warning":
            reward += 0.5
        else:
            reward -= 0.2

    elif action_type == "file_interim_report":
        reward += 0.3 if fda_flag in {"warning", "hold"} else 0.1

    elif action_type == "adjust_dose":
        if serious_adverse_events > 0:
            reward += 0.3 if magnitude < 0 else -0.3
        elif efficacy_signal < 0.5:
            reward += 0.3 if magnitude > 0 else -0.2
        else:
            reward += 0.05

    elif action_type == "implement_amendment":
        reward += 0.15 if fda_flag == "hold" else -0.1

    elif action_type == "noop":
        reward -= 0.1

    return max(-1.0, min(1.0, reward))


def _build_prompt_dataset(num_samples: int, seed: int) -> list[dict[str, str]]:
    cfg = default_config()
    rng = random.Random(seed)
    dataset: list[dict[str, str]] = []
    for idx in range(num_samples):
        env = TrialEnv(cfg)
        reset = env.reset(seed=seed + idx)
        state = reset.state
        for _ in range(rng.randint(1, max(2, cfg.stage_config.max_weeks // 2))):
            template = ACTION_LIBRARY[rng.randint(0, len(ACTION_LIBRARY) - 1)]
            result = env.step(Action(type=template.action_type, magnitude=template.magnitude))
            state = result.state
            if result.terminated or result.truncated:
                break
        dataset.append({"prompt": _state_to_prompt(state)})
    return dataset


def _rollout_episode(policy: LinearPolicy, seed: int) -> EpisodeRollout:
    cfg = default_config()
    env = TrialEnv(cfg)
    reset = env.reset(seed=seed)
    state = reset.state
    rng = random.Random(seed)

    total_reward = 0.0
    transitions: list[Transition] = []

    for _ in range(cfg.stage_config.max_weeks):
        features = feature_vector(state, cfg)
        action_index = policy.select_index(features, rng, stochastic=True)
        action_template = ACTION_LIBRARY[action_index]
        action = Action(type=action_template.action_type, magnitude=action_template.magnitude)
        result = env.step(action)

        rb = reward_breakdown(cfg.reward_weights, state, action, result.state)
        step_reward = rb["total"] + result.info["validation"]["penalty"]
        total_reward += step_reward

        transitions.append(Transition(features=features, action_index=action_index))
        state = result.state
        if result.terminated or result.truncated:
            break

    return EpisodeRollout(total_reward=total_reward, transitions=transitions)


def _update_policy_grpo(policy: LinearPolicy, rollouts: list[EpisodeRollout], learning_rate: float) -> None:
    if not rollouts:
        return

    baseline = sum(r.total_reward for r in rollouts) / len(rollouts)

    for rollout in rollouts:
        advantage = rollout.total_reward - baseline
        if abs(advantage) < 1e-12:
            continue
        for transition in rollout.transitions:
            probs = policy.probabilities(transition.features)
            for action_idx, prob in enumerate(probs):
                coeff = (1.0 if action_idx == transition.action_index else 0.0) - prob
                for feature_idx, feature_value in enumerate(transition.features):
                    policy.weights[action_idx][feature_idx] += learning_rate * advantage * coeff * feature_value


def train_lightweight_grpo(config_path: str, output_path: str | None = None, max_steps_override: int | None = None) -> str:
    cfg_dict = _load_config_file(config_path)
    learning_rate = float(cfg_dict.get("learning_rate", 2.0e-5))
    max_steps = max_steps_override if max_steps_override is not None else int(cfg_dict.get("max_steps", 1000))
    checkpoint_every = int(cfg_dict.get("checkpoint_every", 100))
    early_stop_window = int(cfg_dict.get("early_stop_window", 500))
    early_stop_min_improvement = float(cfg_dict.get("early_stop_min_improvement", 0.10))
    group_size = int(cfg_dict.get("group_size", 8))
    seed = int(cfg_dict.get("seed", 17))

    final_output = output_path or str(cfg_dict.get("output_checkpoint", "artifacts/policy/latest.json"))
    checkpoints_dir = Path(str(cfg_dict.get("checkpoints_dir", "artifacts/policy/checkpoints")))
    checkpoints_dir.mkdir(parents=True, exist_ok=True)

    policy = init_zero_policy()
    rng = random.Random(seed)

    reward_history: list[float] = []
    best_window_mean: float | None = None

    for step in range(1, max_steps + 1):
        step_rollouts = [_rollout_episode(policy, seed=rng.randint(0, 2_000_000_000)) for _ in range(group_size)]
        _update_policy_grpo(policy, step_rollouts, learning_rate)

        mean_reward = sum(r.total_reward for r in step_rollouts) / len(step_rollouts)
        reward_history.append(mean_reward)

        if step % checkpoint_every == 0:
            ckpt_path = checkpoints_dir / f"step_{step:05d}.json"
            save_policy_checkpoint(policy, str(ckpt_path), metadata={"step": step, "mean_reward": mean_reward})
            print(f"[checkpoint] step={step} mean_reward={mean_reward:.4f} path={ckpt_path}")

        if step >= early_stop_window:
            recent_mean = sum(reward_history[-early_stop_window:]) / early_stop_window
            if best_window_mean is None or recent_mean > best_window_mean:
                best_window_mean = recent_mean
            elif best_window_mean is not None and best_window_mean > 0:
                required = best_window_mean * (1.0 + early_stop_min_improvement)
                if recent_mean < required:
                    print(
                        "[early-stop] No sufficient improvement over window: "
                        f"recent={recent_mean:.4f} required={required:.4f}."
                    )
                    break

    save_policy_checkpoint(
        policy,
        final_output,
        metadata={
            "algorithm": "grouped_relative_policy_optimization",
            "seed": seed,
            "steps_ran": len(reward_history),
            "last_mean_reward": reward_history[-1] if reward_history else 0.0,
        },
    )
    print(f"[done] Saved policy checkpoint: {final_output}")
    return final_output


def train_with_trl_unsloth(
    config_path: str,
    output_path: str | None = None,
    max_steps_override: int | None = None,
    strict: bool = True,
) -> str:
    """TRL + Unsloth training path.

    strict=True: fail fast if TRL/Unsloth stack is unavailable.
    strict=False: fallback to lightweight trainer.
    """
    cfg_dict = _load_config_file(config_path)
    final_output = output_path or str(cfg_dict.get("output_checkpoint", "artifacts/policy/latest.json"))

    try:
        import torch  # type: ignore
        from datasets import Dataset  # type: ignore
        from transformers import AutoTokenizer  # type: ignore
        from trl import GRPOTrainer  # type: ignore
        from trl import GRPOConfig  # type: ignore
        from unsloth import FastLanguageModel  # type: ignore
    except Exception as exc:  # pragma: no cover
        if strict:
            raise RuntimeError(
                "TRL + Unsloth backend requested but dependencies are unavailable. "
                "Install train extras in a GPU-ready environment."
            ) from exc
        print("[trl-unsloth] Missing deps, fallback to lightweight trainer.")
        return train_lightweight_grpo(config_path, output_path=output_path, max_steps_override=max_steps_override)

    model_name = str(cfg_dict.get("model_name", "Qwen/Qwen2.5-1.5B-Instruct"))
    learning_rate = float(cfg_dict.get("learning_rate", 2.0e-5))
    max_steps = max_steps_override if max_steps_override is not None else int(cfg_dict.get("max_steps", 500))
    seed = int(cfg_dict.get("seed", 17))
    per_device_batch = int(cfg_dict.get("batch_size", 4))
    grad_accum = int(cfg_dict.get("gradient_accumulation_steps", 1))
    prompt_samples = int(cfg_dict.get("trl_prompt_samples", 256))
    trl_output_dir = str(cfg_dict.get("trl_output_dir", "artifacts/trl_unsloth"))

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=model_name,
        max_seq_length=1024,
        dtype=None,
        load_in_4bit=True,
    )
    if tokenizer is None:
        tokenizer = AutoTokenizer.from_pretrained(model_name)
    if getattr(tokenizer, "pad_token", None) is None:
        tokenizer.pad_token = tokenizer.eos_token

    if hasattr(FastLanguageModel, "get_peft_model"):
        model = FastLanguageModel.get_peft_model(
            model,
            r=16,
            target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
            lora_alpha=16,
            lora_dropout=0.0,
            bias="none",
            use_gradient_checkpointing=True,
            random_state=seed,
        )

    prompt_ds = Dataset.from_list(_build_prompt_dataset(prompt_samples, seed=seed))

    def reward_fn(completions: list[str], prompts: list[str], **_: Any) -> list[float]:
        values: list[float] = []
        for prompt, completion in zip(prompts, completions):
            values.append(_heuristic_reward(prompt, completion))
        return values

    training_args = GRPOConfig(
        output_dir=trl_output_dir,
        learning_rate=learning_rate,
        per_device_train_batch_size=per_device_batch,
        gradient_accumulation_steps=grad_accum,
        max_steps=max_steps,
        bf16=torch.cuda.is_available(),
        fp16=not torch.cuda.is_available(),
        logging_steps=10,
        report_to=[],
        save_steps=max(25, min(100, max_steps)),
    )

    trainer = GRPOTrainer(
        model=model,
        processing_class=tokenizer,
        reward_funcs=[reward_fn],
        args=training_args,
        train_dataset=prompt_ds,
    )
    trainer.train()

    output_dir = Path(trl_output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    trainer.save_model(str(output_dir / "final_model"))

    # Keep benchmark/demo pipeline consistent by exporting a runtime policy checkpoint.
    # This checkpoint can be replaced later with a model-backed policy adapter.
    save_policy_checkpoint(
        init_zero_policy(),
        final_output,
        metadata={
            "algorithm": "trl_grpo_unsloth",
            "model_name": model_name,
            "max_steps": max_steps,
            "note": "runtime policy adapter checkpoint",
        },
    )
    print(f"[done] TRL training finished. Model saved under {trl_output_dir}. Runtime checkpoint: {final_output}")
    return final_output


def main() -> None:
    parser = argparse.ArgumentParser(description="GRPO training entrypoint")
    parser.add_argument("--config", default="training/configs/grpo_medium.yaml")
    parser.add_argument("--backend", choices=["auto", "lightweight", "trl-unsloth"], default="auto")
    parser.add_argument("--output", default="")
    parser.add_argument("--max-steps", type=int, default=0)
    parser.add_argument("--allow-fallback", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    cfg = default_config()
    print("Loaded trial config stage:", cfg.stage)
    print("Training config path:", args.config)

    if args.dry_run:
        parsed = _load_config_file(args.config)
        print(json.dumps(parsed, indent=2))
        print("Dry run complete.")
        return

    config_values = _load_config_file(args.config)
    backend = str(config_values.get("backend", args.backend)) if args.backend == "auto" else args.backend

    if backend == "trl-unsloth":
        output_path = args.output.strip() or None
        max_steps_override = args.max_steps if args.max_steps > 0 else None
        train_with_trl_unsloth(
            args.config,
            output_path=output_path,
            max_steps_override=max_steps_override,
            strict=not args.allow_fallback,
        )
        return

    output_path = args.output.strip() or None
    max_steps_override = args.max_steps if args.max_steps > 0 else None
    train_lightweight_grpo(args.config, output_path=output_path, max_steps_override=max_steps_override)


if __name__ == "__main__":
    main()
