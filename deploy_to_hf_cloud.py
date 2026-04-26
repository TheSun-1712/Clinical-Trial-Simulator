from __future__ import annotations

import argparse
import os

from huggingface_hub import HfApi


def deploy(repo_id: str, private: bool, hardware: str = "") -> None:
    token = os.getenv("HF_TOKEN", "").strip()
    if not token:
        raise RuntimeError("HF_TOKEN environment variable is required")

    api = HfApi(token=token)

    visibility = "private" if private else "public"
    print(f"1) Creating {visibility} Space: {repo_id}")
    api.create_repo(
        repo_id=repo_id,
        repo_type="space",
        space_sdk="docker",
        private=private,
        exist_ok=True,
    )

    print("2) Uploading repository files to the Space")
    api.upload_folder(
        folder_path=".",
        repo_id=repo_id,
        repo_type="space",
        ignore_patterns=[
            ".git/*",
            "**/__pycache__/*",
            "*.pyc",
            ".venv*",
            "**/node_modules/*",
            "**/dist/*",
            ".pytest_cache/*",
            "artifacts/trl_*/*",
            "artifacts/api_cache/*",
        ],
    )

    if hardware:
        print(f"3) Requesting hardware upgrade: {hardware}")
        try:
            api.request_space_hardware(repo_id=repo_id, hardware=hardware)
            print("Hardware upgrade requested successfully")
        except Exception as exc:
            print(f"Warning: could not request hardware automatically: {exc}")

    print("\nDeployment complete")
    print(f"Space URL: https://huggingface.co/spaces/{repo_id}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Deploy this repository to a Hugging Face Space")
    parser.add_argument("--repo-id", required=True, help="Example: your-hf-username/clinical-trial-simulator-v2")
    parser.add_argument("--private", action="store_true", help="Create private Space (default: public)")
    parser.add_argument("--hardware", default="", help="Optional hardware tier, e.g. cpu-basic, t4-small, a10g-small")
    args = parser.parse_args()
    deploy(repo_id=args.repo_id.strip(), private=args.private, hardware=args.hardware.strip())


if __name__ == "__main__":
    main()
