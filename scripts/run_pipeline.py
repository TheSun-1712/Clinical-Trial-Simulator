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
from training.train_grpo import train_lightweight_grpo


def main() -> None:
    parser = argparse.ArgumentParser(description="End-to-end train/load + benchmark + demo pipeline")
    parser.add_argument("--train", action="store_true", help="Run training before benchmark")
    parser.add_argument("--config", default="training/configs/grpo_medium.yaml")
    parser.add_argument("--checkpoint", default="artifacts/policy/latest.json")
    parser.add_argument("--episodes", type=int, default=50)
    parser.add_argument("--max-steps", type=int, default=0)
    parser.add_argument("--launch-demo", action="store_true")
    args = parser.parse_args()

    checkpoint_path = Path(args.checkpoint)
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)

    if args.train or not checkpoint_path.exists():
        print("[pipeline] Training policy...")
        train_lightweight_grpo(
            args.config,
            output_path=str(checkpoint_path),
            max_steps_override=args.max_steps if args.max_steps > 0 else None,
        )
    else:
        print(f"[pipeline] Using existing checkpoint: {checkpoint_path}")

    print("[pipeline] Running benchmark...")
    rows = run_benchmark(episodes=args.episodes, trained_checkpoint=str(checkpoint_path))
    for row in rows:
        print(f"{row.name:10s} {row.metrics} source={row.source}")

    if args.launch_demo:
        cmd = [sys.executable, "-m", "streamlit", "run", "demo/app.py"]
        print("[pipeline] Launching demo:", " ".join(cmd))
        subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
