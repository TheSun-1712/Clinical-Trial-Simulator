from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

import os
import sys

root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(root, "src"))
sys.path.insert(0, root)

from training.train_grpo import train_lightweight_grpo, train_with_trl_unsloth


def _read_metadata(path: str) -> dict[str, Any]:
    checkpoint = Path(path)
    if not checkpoint.exists():
        return {}
    try:
        payload = json.loads(checkpoint.read_text(encoding="utf-8"))
    except Exception:
        return {}
    metadata = payload.get("metadata", {})
    return metadata if isinstance(metadata, dict) else {}


def run_continuous_training(
    config: str,
    checkpoint: str,
    backend: str,
    max_steps_per_cycle: int,
    interval_seconds: float,
    max_cycles: int,
) -> None:
    cycle = 0
    while max_cycles <= 0 or cycle < max_cycles:
        cycle += 1
        resume_from = checkpoint if Path(checkpoint).exists() else None
        metadata = {
            "continuous_cycle": cycle,
            "continuous_training": True,
            "previous_metadata": _read_metadata(checkpoint),
        }
        if backend in {"trl", "trl-unsloth"}:
            train_with_trl_unsloth(
                config,
                output_path=checkpoint,
                max_steps_override=max_steps_per_cycle,
                strict=True,
                resume_from_checkpoint=resume_from,
                metadata_overrides=metadata,
            )
        elif backend == "lightweight":
            train_lightweight_grpo(
                config,
                output_path=checkpoint,
                max_steps_override=max_steps_per_cycle,
                resume_from_checkpoint=resume_from,
                metadata_overrides=metadata,
            )
        else:
            raise ValueError(f"Unsupported backend: {backend}")

        if interval_seconds > 0:
            time.sleep(interval_seconds)


def main() -> None:
    parser = argparse.ArgumentParser(description="Continuously improve a neural/LLM clinical-trial policy.")
    parser.add_argument("--config", default="training/configs/grpo_medium.yaml")
    parser.add_argument("--checkpoint", default="artifacts/policy/latest_llm.json")
    parser.add_argument("--backend", choices=["trl-unsloth", "trl", "lightweight"], default="trl-unsloth")
    parser.add_argument("--max-steps-per-cycle", type=int, default=100)
    parser.add_argument("--interval-seconds", type=float, default=5.0)
    parser.add_argument("--max-cycles", type=int, default=0, help="0 means run until stopped.")
    args = parser.parse_args()

    run_continuous_training(
        config=args.config,
        checkpoint=args.checkpoint,
        backend=args.backend,
        max_steps_per_cycle=args.max_steps_per_cycle,
        interval_seconds=args.interval_seconds,
        max_cycles=args.max_cycles,
    )


if __name__ == "__main__":
    main()
