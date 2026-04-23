from pathlib import Path

from cts.policy import checkpoint_exists, init_zero_policy, load_policy_checkpoint, save_policy_checkpoint
from eval.run_benchmark import run_benchmark


def test_policy_checkpoint_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "policy.json"
    policy = init_zero_policy()
    save_policy_checkpoint(policy, str(path), metadata={"unit_test": True})

    assert checkpoint_exists(str(path))
    loaded = load_policy_checkpoint(str(path))
    assert loaded.weights == policy.weights


def test_benchmark_uses_checkpoint_source(tmp_path: Path) -> None:
    path = tmp_path / "policy.json"
    save_policy_checkpoint(init_zero_policy(), str(path))

    rows = run_benchmark(episodes=2, trained_checkpoint=str(path))
    trained = [row for row in rows if row.name == "trained"][0]
    assert trained.source.startswith("checkpoint:")
