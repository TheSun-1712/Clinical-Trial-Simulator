from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from eval.run_benchmark import run_benchmark
from eval.analytics import load_latest_benchmark_report
from training.train_grpo import train_with_trl_unsloth


def main() -> None:
    parser = argparse.ArgumentParser(description="End-to-end train/load + benchmark + demo pipeline")
    parser.add_argument("--train", action="store_true", help="Run training before benchmark")
    parser.add_argument("--config", default="training/configs/grpo_medium.yaml")
    parser.add_argument("--checkpoint", default="artifacts/policy/latest.json")
    parser.add_argument("--episodes", type=int, default=50)
    parser.add_argument("--max-steps", type=int, default=0)
    parser.add_argument("--iterations", type=int, default=2)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--artifact-dir", default="artifacts/benchmark")
    parser.add_argument("--allow-fallback", action="store_true")
    parser.add_argument("--launch-demo", action="store_true")
    args = parser.parse_args()

    checkpoint_path = Path(args.checkpoint)
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)

    iterations = max(1, args.iterations)
    previous_trained_efficiency: float | None = None

    if args.train or not checkpoint_path.exists():
        for iteration in range(iterations):
            print(f"[pipeline] Training policy iteration {iteration + 1}/{iterations}...")
            benchmark_summary = load_latest_benchmark_report(args.artifact_dir) or {}
            metadata = {
                "iteration": iteration + 1,
                "benchmark_previous": benchmark_summary.get("overall", {}),
                "disease_metrics": benchmark_summary.get("disease_metrics", {}),
                "phase_metrics": benchmark_summary.get("phase_metrics", {}),
                "correction_summary": benchmark_summary.get("correction_summary", {}),
            }
            train_with_trl_unsloth(
                args.config,
                output_path=str(checkpoint_path),
                max_steps_override=args.max_steps if args.max_steps > 0 else None,
                resume_from_checkpoint=str(checkpoint_path) if args.resume and checkpoint_path.exists() else None,
                metadata_overrides=metadata,
                strict=not args.allow_fallback,
            )

            print(f"[pipeline] Evaluating iteration {iteration + 1}/{iterations}...")
            rows = run_benchmark(episodes=args.episodes, trained_checkpoint=str(checkpoint_path), output_dir=args.artifact_dir)
            for row in rows:
                print(f"{row.name:10s} {row.metrics} source={row.source}")

            trained_row = next((row for row in rows if row.name == "trained"), None)
            current_efficiency = trained_row.metrics.get("composite_efficiency", 0.0) if trained_row else 0.0
            if previous_trained_efficiency is not None:
                delta = current_efficiency - previous_trained_efficiency
                print(f"[pipeline] Trained composite efficiency delta: {delta:+.4f}")
            if previous_trained_efficiency is not None and current_efficiency <= previous_trained_efficiency:
                print("[pipeline] No improvement detected; keeping the same checkpoint and extending the next iteration.")
            previous_trained_efficiency = current_efficiency
    else:
        print(f"[pipeline] Using existing checkpoint: {checkpoint_path}")
        print("[pipeline] Running benchmark...")
        rows = run_benchmark(episodes=args.episodes, trained_checkpoint=str(checkpoint_path), output_dir=args.artifact_dir)
        for row in rows:
            print(f"{row.name:10s} {row.metrics} source={row.source}")

    if args.launch_demo:
        cmd = [sys.executable, "-m", "streamlit", "run", "demo/app.py"]
        print("[pipeline] Launching demo:", " ".join(cmd))
        subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
