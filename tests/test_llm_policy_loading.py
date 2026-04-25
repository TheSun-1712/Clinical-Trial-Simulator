from __future__ import annotations

import sys
import types
from pathlib import Path

from cts.policy_llm import parse_llm_action_text, save_llm_policy_checkpoint
from cts.policy_loader import describe_policy_checkpoint, load_any_policy_checkpoint
from eval.run_benchmark import run_benchmark


def test_llm_action_parsing_json_and_fallback() -> None:
    parsed_json = parse_llm_action_text('{"action_type":"recruit","magnitude":2.0}')
    assert parsed_json["valid_json"] is True
    assert parsed_json["valid_action"] is True
    assert parsed_json["action_type"].value == "recruit"

    parsed_text = parse_llm_action_text("action_type=hold_enrollment magnitude=0")
    assert parsed_text["valid_json"] is False
    assert parsed_text["valid_action"] is True
    assert parsed_text["action_type"].value == "hold_enrollment"


def test_checkpoint_loader_reads_llm_manifest(monkeypatch, tmp_path: Path) -> None:
    checkpoint = tmp_path / "llm_checkpoint.json"
    save_llm_policy_checkpoint(
        str(checkpoint),
        model_dir=str(tmp_path / "model"),
        model_name="Qwen/Qwen2.5-1.5B-Instruct",
        adapter_dir=str(tmp_path / "adapter"),
        metadata={"max_new_tokens": 48},
    )

    class FakeLLMPolicy:
        def __init__(self, model_dir: str, model_name: str, max_new_tokens: int = 64, adapter_dir: str | None = None):
            self.model_dir = model_dir
            self.model_name = model_name
            self.max_new_tokens = max_new_tokens
            self.adapter_dir = adapter_dir

    monkeypatch.setattr("cts.policy_llm.LLMPolicy", FakeLLMPolicy)
    loaded = load_any_policy_checkpoint(str(checkpoint))
    assert loaded.model_name == "Qwen/Qwen2.5-1.5B-Instruct"
    assert loaded.adapter_dir == str(tmp_path / "adapter")

    description = describe_policy_checkpoint(str(checkpoint))
    assert description["policy_type"] == "llm_causal"
    assert description["adapter_dir"] == str(tmp_path / "adapter")


def test_benchmark_accepts_llm_checkpoint_source(monkeypatch, tmp_path: Path) -> None:
    checkpoint = tmp_path / "llm_checkpoint.json"
    save_llm_policy_checkpoint(
        str(checkpoint),
        model_dir=str(tmp_path / "model"),
        model_name="Qwen/Qwen2.5-1.5B-Instruct",
    )

    class FakePolicy:
        def select_action(self, state, config, rng, stochastic=False):  # noqa: ANN001, ANN201
            from cts.environment.models import Action, ActionType

            return Action(type=ActionType.NOOP, magnitude=0.0)

    monkeypatch.setattr("eval.run_benchmark.load_any_policy_checkpoint", lambda _path: FakePolicy())

    rows = run_benchmark(episodes=3, trained_checkpoint=str(checkpoint), output_dir=str(tmp_path / "benchmark"))
    trained = [row for row in rows if row.name == "trained"][0]
    assert "llm_causal" in trained.source


def test_llm_policy_loads_base_then_peft_adapter(monkeypatch, tmp_path: Path) -> None:
    adapter = tmp_path / "adapter"
    adapter.mkdir(parents=True, exist_ok=True)
    checkpoint = tmp_path / "llm_checkpoint.json"
    save_llm_policy_checkpoint(
        str(checkpoint),
        model_dir=str(tmp_path / "legacy_model_dir"),
        model_name="Qwen/Qwen2.5-1.5B-Instruct",
        adapter_dir=str(adapter),
    )

    class FakeTokenizer:
        pad_token = None
        eos_token = "<eos>"
        eos_token_id = 1
        pad_token_id = 1

    class FakeModel:
        def eval(self) -> None:
            return None

    loaded_sources: list[str] = []
    attached_adapters: list[str] = []

    auto_module = types.ModuleType("transformers")
    auto_module.AutoTokenizer = types.SimpleNamespace(
        from_pretrained=lambda source: loaded_sources.append(source) or FakeTokenizer()
    )
    auto_module.AutoModelForCausalLM = types.SimpleNamespace(
        from_pretrained=lambda source: loaded_sources.append(source) or FakeModel()
    )
    peft_module = types.ModuleType("peft")
    peft_module.PeftModel = types.SimpleNamespace(
        from_pretrained=lambda model, adapter_dir: attached_adapters.append(adapter_dir) or model
    )
    monkeypatch.setitem(sys.modules, "transformers", auto_module)
    monkeypatch.setitem(sys.modules, "peft", peft_module)

    _ = load_any_policy_checkpoint(str(checkpoint))
    assert loaded_sources[0] == "Qwen/Qwen2.5-1.5B-Instruct"
    assert str(adapter) in attached_adapters

