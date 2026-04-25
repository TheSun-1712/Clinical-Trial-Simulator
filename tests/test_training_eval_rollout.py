from __future__ import annotations

import json
import sys
import types
from pathlib import Path

from cts.policy import ACTION_LIBRARY
from training.train_grpo import _build_prompt_dataset, _env_rollout_reward, train_with_trl_unsloth


def test_prompt_dataset_rows_include_reconstruction_metadata() -> None:
    rows = _build_prompt_dataset(num_samples=3, seed=17)
    assert rows
    first = rows[0]
    assert "prompt" in first
    assert "env_seed" in first
    assert "warmup_action_indices" in first
    assert isinstance(first["env_seed"], int)
    assert isinstance(first["warmup_action_indices"], list)


def test_env_rollout_reward_uses_reconstruction_metadata(monkeypatch) -> None:
    class FakeEnv:
        last_reset_seed: int | None = None
        actions: list[tuple[str, float]] = []

        def __init__(self, _cfg):  # noqa: ANN001
            return None

        def reset(self, seed: int):  # noqa: ANN201
            FakeEnv.last_reset_seed = seed
            FakeEnv.actions = []
            return types.SimpleNamespace(state=types.SimpleNamespace())

        def step(self, action):  # noqa: ANN001, ANN201
            FakeEnv.actions.append((action.type.value, float(action.magnitude)))
            return types.SimpleNamespace(
                state=types.SimpleNamespace(),
                terminated=False,
                truncated=False,
                info={"validation": {"penalty": 0.0}},
            )

    monkeypatch.setattr("training.train_grpo.TrialEnv", FakeEnv)
    monkeypatch.setattr("training.train_grpo.reward_breakdown", lambda *args, **kwargs: {"total": 0.3})
    score = _env_rollout_reward(
        prompt="State: week=1.",
        completion_text='{"action_type":"hold_enrollment","magnitude":0.0}',
        rollout_steps=1,
        seed=17,
        reconstruction_meta={"env_seed": 123, "warmup_action_indices": [0, 1]},
    )
    assert FakeEnv.last_reset_seed == 123
    assert FakeEnv.actions[0] == (ACTION_LIBRARY[0].action_type.value, ACTION_LIBRARY[0].magnitude)
    assert FakeEnv.actions[1] == (ACTION_LIBRARY[1].action_type.value, ACTION_LIBRARY[1].magnitude)
    assert -1.0 <= score <= 1.0


def test_env_rollout_reward_fallback_without_metadata(monkeypatch) -> None:
    class FakeEnv:
        last_reset_seed: int | None = None

        def __init__(self, _cfg):  # noqa: ANN001
            return None

        def reset(self, seed: int):  # noqa: ANN201
            FakeEnv.last_reset_seed = seed
            return types.SimpleNamespace(state=types.SimpleNamespace())

        def step(self, _action):  # noqa: ANN001, ANN201
            return types.SimpleNamespace(
                state=types.SimpleNamespace(),
                terminated=False,
                truncated=False,
                info={"validation": {"penalty": 0.0}},
            )

    monkeypatch.setattr("training.train_grpo.TrialEnv", FakeEnv)
    monkeypatch.setattr("training.train_grpo.reward_breakdown", lambda *args, **kwargs: {"total": 0.1})
    score = _env_rollout_reward(
        prompt="State: week=4, enrolled=2.",
        completion_text='{"action_type":"noop","magnitude":0.0}',
        rollout_steps=1,
        seed=17,
        reconstruction_meta=None,
    )
    assert isinstance(FakeEnv.last_reset_seed, int)
    assert -1.0 <= score <= 1.0


def test_eval_summary_persists_to_manifest(monkeypatch, tmp_path: Path) -> None:
    cfg_path = tmp_path / "grpo_eval.yaml"
    output_manifest = tmp_path / "latest_llm.json"
    trl_output_dir = tmp_path / "trl_output"
    cfg_path.write_text(
        "\n".join(
            [
                "model_name: fake/base-model",
                "learning_rate: 2.0e-5",
                "batch_size: 1",
                "gradient_accumulation_steps: 1",
                "num_generations: 1",
                "max_prompt_length: 128",
                "max_completion_length: 32",
                "lora_rank: 4",
                "lora_alpha: 8",
                "lora_dropout: 0.05",
                "lora_target_modules: ['q_proj']",
                "max_steps: 1",
                "trl_prompt_samples: 1",
                f"trl_output_dir: {trl_output_dir.as_posix()}",
                "reward_mode: text",
                "eval_after_train: true",
                "eval_episodes: 5",
                f"metrics_output_path: {(tmp_path / 'metrics.json').as_posix()}",
            ]
        ),
        encoding="utf-8",
    )

    torch_module = types.ModuleType("torch")
    torch_module.float32 = "float32"
    torch_module.bfloat16 = "bfloat16"
    torch_module.__version__ = "test-torch"
    torch_module.version = types.SimpleNamespace(cuda="test-cuda")
    torch_module.cuda = types.SimpleNamespace(
        is_available=lambda: False,
        get_device_name=lambda _idx: "",
        get_device_properties=lambda _idx: types.SimpleNamespace(total_memory=0),
    )
    datasets_module = types.ModuleType("datasets")
    datasets_module.Dataset = types.SimpleNamespace(from_list=lambda rows: rows)

    class FakeModel:
        def print_trainable_parameters(self) -> None:
            return None

        def save_pretrained(self, path: str) -> None:
            Path(path).mkdir(parents=True, exist_ok=True)

    class FakeTokenizer:
        pad_token = None
        eos_token = "<eos>"

        def push_to_hub(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
            return None

    transformers_module = types.ModuleType("transformers")
    transformers_module.AutoModelForCausalLM = types.SimpleNamespace(from_pretrained=lambda *_args, **_kwargs: FakeModel())
    transformers_module.AutoTokenizer = types.SimpleNamespace(from_pretrained=lambda *_args, **_kwargs: FakeTokenizer())

    peft_module = types.ModuleType("peft")
    peft_module.LoraConfig = lambda **kwargs: kwargs
    peft_module.get_peft_model = lambda model, _cfg: model

    class FakeTrainer:
        def __init__(self, *args, **kwargs):  # noqa: ANN002, ANN003
            return None

        def train(self) -> None:
            return None

        def save_model(self, path: str) -> None:
            Path(path).mkdir(parents=True, exist_ok=True)

    trl_module = types.ModuleType("trl")
    trl_module.GRPOConfig = lambda **kwargs: kwargs
    trl_module.GRPOTrainer = FakeTrainer

    monkeypatch.setitem(sys.modules, "torch", torch_module)
    monkeypatch.setitem(sys.modules, "datasets", datasets_module)
    monkeypatch.setitem(sys.modules, "transformers", transformers_module)
    monkeypatch.setitem(sys.modules, "peft", peft_module)
    monkeypatch.setitem(sys.modules, "trl", trl_module)
    monkeypatch.setattr(
        "eval.run_benchmark.compare_trained_vs_heuristic",
        lambda episodes, trained_checkpoint, output_dir=None: {
            "episodes": float(episodes),
            "trained_total_reward": 0.2,
            "heuristic_total_reward": 0.1,
            "trained_worse_than_heuristic": False,
        },
    )

    train_with_trl_unsloth(
        config_path=str(cfg_path),
        output_path=str(output_manifest),
        strict=True,
    )
    payload = json.loads(output_manifest.read_text(encoding="utf-8"))
    assert payload["metadata"]["eval_summary"]["enabled"] is True
    assert payload["metadata"]["eval_summary"]["trained_worse_than_heuristic"] is False

