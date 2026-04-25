from pathlib import Path

from cts.policy import init_zero_policy, save_policy_checkpoint
from eval.analytics import load_latest_benchmark_report
from eval.run_benchmark import run_benchmark


def test_benchmark_writes_rich_artifacts(tmp_path: Path) -> None:
    checkpoint = tmp_path / "policy.json"
    save_policy_checkpoint(init_zero_policy(), str(checkpoint))

    output_dir = tmp_path / "benchmark"
    rows = run_benchmark(episodes=2, trained_checkpoint=str(checkpoint), output_dir=str(output_dir))
    report = load_latest_benchmark_report(str(output_dir))

    assert {row.name for row in rows} == {"random", "heuristic", "trained"}
    assert report is not None
    assert report["policy_rows"]
    assert report["disease_metrics"]
    assert report["phase_metrics"]
    assert report["timeline"]
    assert report["timeline_summary"]
    assert (output_dir / "latest.json").exists()
    assert (output_dir / "latest_summary.json").exists()
    assert (output_dir / "latest_timeline.json").exists()
