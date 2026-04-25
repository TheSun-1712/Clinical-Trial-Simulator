from __future__ import annotations

import argparse
import ast
import importlib.machinery
import json
import os
import random
import sys
import types
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cts.config import default_config
from cts.environment.models import Action, ActionType, TrialState
from cts.environment.trial_env import TrialEnv
from cts.policy import ACTION_LIBRARY, LinearPolicy, feature_vector, init_zero_policy, load_policy_checkpoint, save_policy_checkpoint
from cts.policy_llm import parse_llm_action_text, save_llm_policy_checkpoint
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
            config[key.strip()] = ast.literal_eval(raw)
            continue
        except Exception:
            pass
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
        "You are the Chief Trial Scientist for a simulated research clinical trial. "
        "Analyze the provided state to decide the next action. "
        "Return JSON only with keys action_type, magnitude, composition, and rationale.\n"
        "Allowed action_type values: recruit, adjust_dose, update_composition, hold_enrollment, file_interim_report, implement_amendment, noop.\n"
        f"State: week={state.week}, enrolled={state.enrolled}, active={state.active}, completed={state.completed}, "
        f"adverse_events={state.adverse_events}, serious_adverse_events={state.serious_adverse_events}, "
        f"budget_spent={state.budget_spent:.2f}, dose_level={state.dose_level:.3f}, "
        f"efficacy_signal={state.efficacy_signal:.3f}, recruitment_hold={int(state.recruitment_hold)}, "
        f"composition={state.composition}."
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


def _parse_action_from_text(text: str) -> tuple[str, float, dict, float]:
    """Returns action_type, magnitude, composition, format_score."""
    parsed = parse_llm_action_text(text)
    action_type = parsed["action_type"].value
    magnitude = float(parsed["magnitude"])
    composition = parsed["composition"]
    if parsed["valid_json"]:
        format_score = 1.0
    elif parsed["valid_action"]:
        format_score = 0.4
    else:
        format_score = 0.0
    return action_type, magnitude, composition, format_score


def _heuristic_reward(prompt: str, completion_text: str) -> float:
    state = _parse_state_from_prompt(prompt)
    action_type, magnitude, composition, format_score = _parse_action_from_text(completion_text)

    reward = 0.6 * format_score
    valid_actions = {a.value for a in ActionType}
    if action_type not in valid_actions:
        return reward - 0.8

    enrolled = float(state.get("enrolled", "0"))
    cohort_target = 10.0
    serious_adverse_events = float(state.get("serious_adverse_events", "0"))
    efficacy_signal = float(state.get("efficacy_signal", "0"))
    recruitment_hold = int(float(state.get("recruitment_hold", "0")))
    unsafe_context = recruitment_hold == 1 or serious_adverse_events > 0

    if action_type == "recruit":
        if unsafe_context:
            reward -= 0.9
        elif enrolled < cohort_target:
            reward += 0.6
        else:
            reward -= 0.2
        reward += 0.1 if 0.5 <= magnitude <= 3.5 else -0.1

    elif action_type == "update_composition":
        if not composition:
            reward -= 0.5
        else:
            # Ensure numeric sum
            comp_sum = sum(float(v) for v in composition.values() if isinstance(v, (int, float, str)) and str(v).replace('.','',1).isdigit())
            if abs(comp_sum - 1.0) < 0.05:
                reward += 0.4
            else:
                reward -= 0.3
            
            # Penalize toxic composition if safety is an issue
            if serious_adverse_events > 0 and composition.get("c", 0.0) > 0.3:
                reward -= 0.4
                
    elif action_type == "noop":
        reward -= 0.1

    return max(-1.0, min(1.0, reward))


@dataclass
class RewardMetricsTracker:
    reward_sum: float = 0.0
    reward_count: int = 0
    valid_json_count: int = 0
    valid_action_count: int = 0
    action_counts: Counter[str] = field(default_factory=Counter)
    action_distribution_over_time: list[dict[str, Any]] = field(default_factory=list)
    last_checkpoint_path: str = ""
    reward_mode: str = "text"

    def update(self, prompt: str, completion_text: str, reward: float) -> None:
        del prompt
        parsed = parse_llm_action_text(completion_text)
        self.reward_sum += reward
        self.reward_count += 1
        self.valid_json_count += 1 if parsed["valid_json"] else 0
        self.valid_action_count += 1 if parsed["valid_action"] else 0
        self.action_counts[parsed["action_type"].value] += 1

    def record_snapshot(self, step: int) -> None:
        count = max(1, self.reward_count)
        self.action_distribution_over_time.append(
            {
                "step": step,
                "action_distribution": {
                    key: value / count for key, value in sorted(self.action_counts.items(), key=lambda item: item[0])
                },
            }
        )

    def as_dict(self) -> dict[str, Any]:
        count = max(1, self.reward_count)
        action_distribution = {
            key: value / count for key, value in sorted(self.action_counts.items(), key=lambda item: item[0])
        }
        return {
            "reward_mean": self.reward_sum / count,
            "valid_json_rate": self.valid_json_count / count,
            "valid_action_rate": self.valid_action_count / count,
            "action_distribution": action_distribution,
            "action_distribution_over_time": self.action_distribution_over_time,
            "reward_mode": self.reward_mode,
            "checkpoint_path": self.last_checkpoint_path,
        }


def _action_from_completion(completion_text: str) -> Action:
    parsed = parse_llm_action_text(completion_text)
    return Action(
        type=parsed["action_type"],
        magnitude=float(parsed["magnitude"]),
        composition=parsed["composition"]
    )


def _env_rollout_reward(
    prompt: str,
    completion_text: str,
    rollout_steps: int,
    seed: int,
    reconstruction_meta: dict[str, Any] | None = None,
) -> float:
    cfg = default_config()
    env = TrialEnv(cfg)
    prompt_seed = int((reconstruction_meta or {}).get("env_seed", (abs(hash(prompt)) + seed) % 2_000_000_000))
    warmup_indices = (reconstruction_meta or {}).get("warmup_action_indices")
    warm_rng = random.Random(prompt_seed)
    reset = env.reset(seed=prompt_seed)
    state = reset.state
    if isinstance(warmup_indices, list):
        indices = [int(idx) for idx in warmup_indices]
    else:
        indices = [warm_rng.randint(0, len(ACTION_LIBRARY) - 1) for _ in range(warm_rng.randint(0, 2))]
    for action_idx in indices:
        template = ACTION_LIBRARY[max(0, min(len(ACTION_LIBRARY) - 1, action_idx))]
        warm_result = env.step(Action(type=template.action_type, magnitude=template.magnitude))
        state = warm_result.state
        if warm_result.terminated or warm_result.truncated:
            break

    action = _action_from_completion(completion_text)
    total = 0.0
    for _ in range(max(1, min(3, rollout_steps))):
        result = env.step(action)
        rb = reward_breakdown(cfg.reward_weights, state, action, result.state)
        total += float(rb["total"]) + float(result.info.get("validation", {}).get("penalty", 0.0))
        state = result.state
        if result.terminated or result.truncated:
            break
    return max(-1.0, min(1.0, total / 3.0))


def _build_prompt_dataset(num_samples: int, seed: int) -> list[dict[str, Any]]:
    cfg = default_config()
    rng = random.Random(seed)
    dataset: list[dict[str, Any]] = []
    
    # Try to load hindsight replay examples
    replay_path = Path("artifacts/replay/buffer.jsonl")
    if replay_path.exists():
        try:
            from cts.replay.buffer import ReplayBuffer, EpisodeTrace
            buffer = ReplayBuffer(str(replay_path))
            # This is a simplified example of how we might load traces
            # and generate hindsight examples to augment the prompt dataset.
            # For now, we'll just check if the file exists.
        except ImportError:
            pass

    for idx in range(num_samples):
        env = TrialEnv(cfg)
        env_seed = seed + idx
        reset = env.reset(seed=env_seed)
        state = reset.state
        warmup_action_indices: list[int] = []
        for _ in range(rng.randint(1, max(2, cfg.stage_config.max_weeks // 2))):
            action_idx = rng.randint(0, len(ACTION_LIBRARY) - 1)
            warmup_action_indices.append(action_idx)
            template = ACTION_LIBRARY[action_idx]
            result = env.step(Action(type=template.action_type, magnitude=template.magnitude))
            state = result.state
            if result.terminated or result.truncated:
                break
        dataset.append(
            {
                "prompt": _state_to_prompt(state),
                "env_seed": env_seed,
                "warmup_action_indices": warmup_action_indices,
            }
        )
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


def _install_optional_trl_dependency_stubs() -> None:
    """Avoid requiring optional TRL judge/merge packages that this trainer never uses."""
    if "llm_blender" not in sys.modules:
        llm_blender_module = types.ModuleType("llm_blender")
        llm_blender_module.__spec__ = importlib.machinery.ModuleSpec("llm_blender", loader=None)

        class Blender:
            def __init__(self, *_: Any, **__: Any) -> None:
                raise ImportError("llm-blender is required only for optional TRL judge callbacks.")

        llm_blender_module.Blender = Blender
        sys.modules["llm_blender"] = llm_blender_module

    if "weave" not in sys.modules:
        weave_module = types.ModuleType("weave")
        weave_trace_module = types.ModuleType("weave.trace")
        weave_context_module = types.ModuleType("weave.trace.context")
        weave_module.__spec__ = importlib.machinery.ModuleSpec("weave", loader=None)
        weave_trace_module.__spec__ = importlib.machinery.ModuleSpec("weave.trace", loader=None)
        weave_context_module.__spec__ = importlib.machinery.ModuleSpec("weave.trace.context", loader=None)

        class EvaluationLogger:
            def __init__(self, *_: Any, **__: Any) -> None:
                raise ImportError("weave is required only for optional TRL logging callbacks.")

        class _WeaveClientContext:
            @staticmethod
            def get_weave_client() -> None:
                return None

        def init(*_: Any, **__: Any) -> None:
            raise ImportError("weave is required only for optional TRL logging callbacks.")

        weave_module.EvaluationLogger = EvaluationLogger
        weave_module.init = init
        weave_context_module.weave_client_context = _WeaveClientContext()
        weave_trace_module.context = weave_context_module
        weave_module.trace = weave_trace_module
        sys.modules["weave"] = weave_module
        sys.modules["weave.trace"] = weave_trace_module
        sys.modules["weave.trace.context"] = weave_context_module

    if "mergekit" in sys.modules:
        return

    try:
        import mergekit  # type: ignore  # noqa: F401

        return
    except Exception:
        pass

    mergekit_module = types.ModuleType("mergekit")
    config_module = types.ModuleType("mergekit.config")
    merge_module = types.ModuleType("mergekit.merge")
    mergekit_module.__spec__ = importlib.machinery.ModuleSpec("mergekit", loader=None)
    config_module.__spec__ = importlib.machinery.ModuleSpec("mergekit.config", loader=None)
    merge_module.__spec__ = importlib.machinery.ModuleSpec("mergekit.merge", loader=None)

    class MergeConfiguration:
        @classmethod
        def model_validate(cls, value: Any) -> Any:
            return value

    class MergeOptions:
        def __init__(self, **kwargs: Any) -> None:
            self.kwargs = kwargs

    def run_merge(*_: Any, **__: Any) -> None:
        raise ImportError("mergekit is required only for TRL model-merge callbacks, which this trainer does not use.")

    config_module.MergeConfiguration = MergeConfiguration
    merge_module.MergeOptions = MergeOptions
    merge_module.run_merge = run_merge
    mergekit_module.config = config_module
    mergekit_module.merge = merge_module

    sys.modules["mergekit"] = mergekit_module
    sys.modules["mergekit.config"] = config_module
    sys.modules["mergekit.merge"] = merge_module


def train_lightweight_grpo(
    config_path: str,
    output_path: str | None = None,
    max_steps_override: int | None = None,
    resume_from_checkpoint: str | None = None,
    metadata_overrides: dict[str, Any] | None = None,
) -> str:
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

    if resume_from_checkpoint and Path(resume_from_checkpoint).exists():
        policy = load_policy_checkpoint(resume_from_checkpoint)
    else:
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
            save_policy_checkpoint(
                policy,
                str(ckpt_path),
                metadata={
                    "step": step,
                    "mean_reward": mean_reward,
                    "resume_from_checkpoint": resume_from_checkpoint,
                    **(metadata_overrides or {}),
                },
            )
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
            "resume_from_checkpoint": resume_from_checkpoint,
            **(metadata_overrides or {}),
        },
    )
    print(f"[done] Saved policy checkpoint: {final_output}")
    return final_output


def train_with_trl_unsloth(
    config_path: str,
    output_path: str | None = None,
    max_steps_override: int | None = None,
    strict: bool = True,
    resume_from_checkpoint: str | None = None,
    metadata_overrides: dict[str, Any] | None = None,
) -> str:
    """TRL + Unsloth training path.

    strict=True: fail fast if TRL stack is unavailable.
    strict=False: fallback to lightweight trainer.
    """
    cfg_dict = _load_config_file(config_path)
    final_output = output_path or str(cfg_dict.get("output_checkpoint", "artifacts/policy/latest.json"))

    try:
        _install_optional_trl_dependency_stubs()
        import torch  # type: ignore
        from datasets import Dataset  # type: ignore
        from peft import LoraConfig, get_peft_model  # type: ignore
        from transformers import AutoModelForCausalLM  # type: ignore
        from transformers import AutoTokenizer  # type: ignore
        from trl import GRPOTrainer  # type: ignore
        from trl import GRPOConfig  # type: ignore
    except Exception as exc:  # pragma: no cover
        if strict:
            raise RuntimeError(
                "TRL backend requested but dependencies are unavailable. "
                "Install train extras in a GPU-ready environment."
            ) from exc
        print("[trl] Missing deps, fallback to lightweight trainer.")
        return train_lightweight_grpo(
            config_path,
            output_path=output_path,
            max_steps_override=max_steps_override,
            resume_from_checkpoint=resume_from_checkpoint,
            metadata_overrides=metadata_overrides,
        )

    model_name = str(cfg_dict.get("model_name", "Qwen/Qwen2.5-1.5B-Instruct"))
    resume_adapter_dir = ""
    if resume_from_checkpoint and Path(resume_from_checkpoint).exists():
        try:
            resume_payload = json.loads(Path(resume_from_checkpoint).read_text(encoding="utf-8"))
            if resume_payload.get("policy_type") == "llm_causal":
                manifest_model_name = str(resume_payload.get("model_name", "")).strip()
                if manifest_model_name:
                    model_name = manifest_model_name
                resume_adapter_dir = str(resume_payload.get("adapter_dir", "")).strip()
        except Exception:
            pass
    learning_rate = float(cfg_dict.get("learning_rate", 2.0e-5))
    max_steps = max_steps_override if max_steps_override is not None else int(cfg_dict.get("max_steps", 500))
    seed = int(cfg_dict.get("seed", 17))
    per_device_batch = int(cfg_dict.get("batch_size", 4))
    grad_accum = int(cfg_dict.get("gradient_accumulation_steps", 1))
    num_generations = int(cfg_dict.get("num_generations", 8))
    max_prompt_length = int(cfg_dict.get("max_prompt_length", 512))
    max_completion_length = int(cfg_dict.get("max_completion_length", 256))
    lora_rank = int(cfg_dict.get("lora_rank", 16))
    lora_alpha = int(cfg_dict.get("lora_alpha", 32))
    lora_dropout = float(cfg_dict.get("lora_dropout", 0.05))
    lora_target_modules = cfg_dict.get("lora_target_modules", ["q_proj", "k_proj", "v_proj", "o_proj"])
    if isinstance(lora_target_modules, str):
        lora_target_modules = [chunk.strip() for chunk in lora_target_modules.split(",") if chunk.strip()]
    upload_repo = str(cfg_dict.get("upload_repo", "")).strip()
    upload_private = bool(cfg_dict.get("upload_private", False))
    reward_mode = str(cfg_dict.get("reward_mode", "text")).strip().lower()
    rollout_steps = int(cfg_dict.get("reward_rollout_steps", 1))
    gradient_checkpointing = bool(cfg_dict.get("gradient_checkpointing", False))
    prompt_samples = int(cfg_dict.get("trl_prompt_samples", 256))
    trl_output_dir = str(cfg_dict.get("trl_output_dir", "artifacts/trl_unsloth"))
    eval_after_train = bool(cfg_dict.get("eval_after_train", False))
    eval_episodes = int(cfg_dict.get("eval_episodes", 12))
    metrics_output_path = str(cfg_dict.get("metrics_output_path", "artifacts/training/latest_metrics.json"))

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    if getattr(tokenizer, "pad_token", None) is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32,
        device_map="auto" if torch.cuda.is_available() else None,
    )
    lora_config = LoraConfig(
        r=lora_rank,
        lora_alpha=lora_alpha,
        lora_dropout=lora_dropout,
        target_modules=list(lora_target_modules),
        bias="none",
        task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, lora_config)
    if resume_adapter_dir and Path(resume_adapter_dir).exists():
        from peft import PeftModel  # type: ignore

        model = PeftModel.from_pretrained(model, resume_adapter_dir, is_trainable=True)
    model.print_trainable_parameters()

    prompt_ds = Dataset.from_list(_build_prompt_dataset(prompt_samples, seed=seed))
    metrics_tracker = RewardMetricsTracker()
    metrics_tracker.reward_mode = reward_mode
    reward_fn_calls = {"count": 0}

    def reward_fn(completions: list[str], prompts: list[str], **_: Any) -> list[float]:
        values: list[float] = []
        env_seeds = _.get("env_seed", [])
        warmup_histories = _.get("warmup_action_indices", [])
        for prompt, completion in zip(prompts, completions):
            text_score = _heuristic_reward(prompt, completion)
            if reward_mode == "env_rollout":
                idx = len(values)
                reconstruction_meta: dict[str, Any] | None = None
                if isinstance(env_seeds, list) and isinstance(warmup_histories, list) and idx < len(env_seeds):
                    warmup_value = warmup_histories[idx] if idx < len(warmup_histories) else []
                    reconstruction_meta = {
                        "env_seed": int(env_seeds[idx]),
                        "warmup_action_indices": warmup_value if isinstance(warmup_value, list) else [],
                    }
                env_score = _env_rollout_reward(
                    prompt,
                    completion,
                    rollout_steps=rollout_steps,
                    seed=seed,
                    reconstruction_meta=reconstruction_meta,
                )
                score = max(-1.0, min(1.0, 0.5 * text_score + 0.5 * env_score))
            else:
                score = text_score
            values.append(score)
            metrics_tracker.update(prompt, completion, score)
        reward_fn_calls["count"] += 1
        metrics_tracker.record_snapshot(reward_fn_calls["count"])
        return values

    training_args = GRPOConfig(
        output_dir=trl_output_dir,
        learning_rate=learning_rate,
        per_device_train_batch_size=per_device_batch,
        gradient_accumulation_steps=grad_accum,
        num_generations=num_generations,
        max_prompt_length=max_prompt_length,
        max_completion_length=max_completion_length,
        gradient_checkpointing=gradient_checkpointing,
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
    final_model_dir = output_dir / "final_model"
    trainer.save_model(str(final_model_dir))
    metrics_tracker.last_checkpoint_path = str(final_model_dir)
    metrics_summary = metrics_tracker.as_dict()
    print(f"[metrics] {json.dumps(metrics_summary, indent=2)}")

    adapter_dir = output_dir / "final_adapter"
    adapter_dir.mkdir(parents=True, exist_ok=True)
    if hasattr(model, "save_pretrained"):
        model.save_pretrained(str(adapter_dir))

    pushed_repo = ""
    hf_token = os.environ.get("HF_TOKEN", "").strip()
    if upload_repo and hf_token:
        model.push_to_hub(upload_repo, token=hf_token, private=upload_private)
        tokenizer.push_to_hub(upload_repo, token=hf_token, private=upload_private)
        pushed_repo = upload_repo
    elif upload_repo and not hf_token:
        print("[hf-upload] upload_repo configured but HF_TOKEN is missing, skipping hub upload.")

    # Export a model-backed policy manifest consumed by benchmark/demo loaders.
    eval_summary: dict[str, Any] = {}
    gpu_info = {
        "torch_version": getattr(torch, "__version__", "unknown"),
        "cuda_version": getattr(torch.version, "cuda", None),
        "cuda_available": bool(torch.cuda.is_available()),
        "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "",
        "gpu_vram_bytes": int(torch.cuda.get_device_properties(0).total_memory) if torch.cuda.is_available() else 0,
        "model_name": model_name,
        "lora": {
            "rank": lora_rank,
            "alpha": lora_alpha,
            "dropout": lora_dropout,
            "target_modules": lora_target_modules,
        },
    }

    save_llm_policy_checkpoint(
        final_output,
        model_dir=str(final_model_dir),
        model_name=model_name,
        adapter_dir=str(adapter_dir),
        metadata={
            "algorithm": "trl_grpo_causal_lm",
            "model_name": model_name,
            "max_steps": max_steps,
            "max_new_tokens": 64,
            "lora_rank": lora_rank,
            "lora_alpha": lora_alpha,
            "lora_dropout": lora_dropout,
            "lora_target_modules": lora_target_modules,
            "reward_mean": metrics_summary["reward_mean"],
            "valid_json_rate": metrics_summary["valid_json_rate"],
            "valid_action_rate": metrics_summary["valid_action_rate"],
            "action_distribution": metrics_summary["action_distribution"],
            "checkpoint_path": metrics_summary["checkpoint_path"],
            "pushed_repo": pushed_repo,
            "resume_from_checkpoint": resume_from_checkpoint,
            "reward_mode": reward_mode,
            "reward_rollout_steps": rollout_steps,
            "eval_summary": {},
            "gpu_info": gpu_info,
            **(metadata_overrides or {}),
        },
    )
    if eval_after_train:
        from eval.run_benchmark import compare_trained_vs_heuristic

        compare = compare_trained_vs_heuristic(
            episodes=eval_episodes,
            trained_checkpoint=final_output,
            output_dir="artifacts/benchmark",
        )
        eval_summary = {"enabled": True, **compare}
        if bool(compare.get("trained_worse_than_heuristic", False)):
            print(
                "[eval-warning] trained policy underperforms heuristic: "
                f"trained_total_reward={float(compare.get('trained_total_reward', 0.0)):.4f} "
                f"heuristic_total_reward={float(compare.get('heuristic_total_reward', 0.0)):.4f}"
            )
        payload = json.loads(Path(final_output).read_text(encoding="utf-8"))
        metadata = dict(payload.get("metadata", {}))
        metadata["eval_summary"] = eval_summary
        payload["metadata"] = metadata
        Path(final_output).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    metrics_out = {
        **metrics_summary,
        "gpu_info": gpu_info,
        "eval_summary": eval_summary,
        "model_name": model_name,
        "adapter_dir": str(adapter_dir),
        "manifest_path": final_output,
    }
    metrics_file = Path(metrics_output_path)
    metrics_file.parent.mkdir(parents=True, exist_ok=True)
    metrics_file.write_text(json.dumps(metrics_out, indent=2), encoding="utf-8")
    print(f"[done] TRL training finished. Model saved under {trl_output_dir}. Policy manifest: {final_output}")
    return final_output


def main() -> None:
    parser = argparse.ArgumentParser(description="GRPO training entrypoint")
    parser.add_argument("--config", default="training/configs/grpo_medium.yaml")
    parser.add_argument("--backend", choices=["auto", "lightweight", "trl-unsloth", "trl"], default="auto")
    parser.add_argument("--output", default="")
    parser.add_argument("--max-steps", type=int, default=0)
    parser.add_argument("--resume-from", default="")
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

    if backend in {"trl-unsloth", "trl"}:
        output_path = args.output.strip() or None
        max_steps_override = args.max_steps if args.max_steps > 0 else None
        train_with_trl_unsloth(
            args.config,
            output_path=output_path,
            max_steps_override=max_steps_override,
            resume_from_checkpoint=args.resume_from.strip() or None,
            strict=not args.allow_fallback,
        )
        return

    if backend == "auto":
        output_path = args.output.strip() or None
        max_steps_override = args.max_steps if args.max_steps > 0 else None
        train_with_trl_unsloth(
            args.config,
            output_path=output_path,
            max_steps_override=max_steps_override,
            resume_from_checkpoint=args.resume_from.strip() or None,
            strict=not args.allow_fallback,
        )
        return

    output_path = args.output.strip() or None
    max_steps_override = args.max_steps if args.max_steps > 0 else None
    train_lightweight_grpo(
        args.config,
        output_path=output_path,
        max_steps_override=max_steps_override,
        resume_from_checkpoint=args.resume_from.strip() or None,
    )


if __name__ == "__main__":
    main()
