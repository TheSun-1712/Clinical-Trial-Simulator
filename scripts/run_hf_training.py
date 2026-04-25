from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _run(cmd: list[str], cwd: Path | None = None) -> None:
    printable = " ".join(cmd)
    print(f"[run] {printable}")
    subprocess.run(cmd, cwd=str(cwd or ROOT), check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Hugging Face oriented GRPO training runner")
    parser.add_argument("--config", default="training/configs/grpo_gpu_8gb.yaml")
    parser.add_argument("--output", default="artifacts/policy/latest_llm.json")
    parser.add_argument("--episodes", type=int, default=12)
    parser.add_argument("--skip-install", action="store_true")
    parser.add_argument("--upload-manifest-repo", default="")
    parser.add_argument("--upload-private", action="store_true")
    args = parser.parse_args()

    python = sys.executable
    if not args.skip_install:
        _run([python, "-m", "pip", "install", "-e", ".[train]"])

    _run(
        [
            python,
            "training/train_grpo.py",
            "--backend",
            "trl",
            "--config",
            args.config,
            "--output",
            args.output,
        ]
    )
    _run(
        [
            python,
            "-m",
            "eval.run_benchmark",
            "--episodes",
            str(args.episodes),
            "--trained-checkpoint",
            args.output,
            "--output-dir",
            "artifacts/benchmark",
        ]
    )

    repo_id = args.upload_manifest_repo.strip()
    hf_token = os.environ.get("HF_TOKEN", "").strip()
    if repo_id:
        if not hf_token:
            raise RuntimeError("HF_TOKEN is required to upload manifest artifacts")
        _run([python, "-m", "pip", "install", "huggingface_hub>=0.24"])
        from huggingface_hub import HfApi  # type: ignore

        api = HfApi(token=hf_token)
        api.create_repo(repo_id=repo_id, private=args.upload_private, exist_ok=True)
        api.upload_file(
            path_or_fileobj=str(ROOT / args.output),
            path_in_repo=Path(args.output).name,
            repo_id=repo_id,
            token=hf_token,
        )
        metrics_path = ROOT / "artifacts/training/latest_metrics.json"
        if metrics_path.exists():
            api.upload_file(
                path_or_fileobj=str(metrics_path),
                path_in_repo=metrics_path.name,
                repo_id=repo_id,
                token=hf_token,
            )
        print(f"[upload] uploaded manifest artifacts to {repo_id}")

    print("[done] HF training workflow completed.")


if __name__ == "__main__":
    main()
