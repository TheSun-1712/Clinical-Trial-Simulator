import os
from huggingface_hub import HfApi

def deploy():
    token = os.getenv("HF_TOKEN")
    if not token:
        print("Error: HF_TOKEN environment variable not set.")
        return

    api = HfApi(token=token)
    repo_id = "Helix2003/cts-cloud-training"
    
    print(f"1. Creating private Space: {repo_id}...")
    api.create_repo(
        repo_id=repo_id,
        repo_type="space",
        space_sdk="docker",
        private=True,
        exist_ok=True
    )
    
    print("2. Uploading repository files (ignoring artifacts, .git, and .venv)...", flush=True)
    # Upload everything except heavy/unnecessary folders
    api.upload_folder(
        folder_path=".",
        repo_id=repo_id,
        repo_type="space",
        ignore_patterns=["artifacts/*", ".git/*", "__pycache__/*", "*.pyc", ".venv*", ".pytest_cache/*", "deploy_to_hf_cloud.py"]
    )
    
    print("3. Requesting A10G Small GPU upgrade (This uses your HF credits!)...")
    try:
        api.request_space_hardware(repo_id=repo_id, hardware="a10g-small")
        print("Hardware upgrade requested successfully!")
    except Exception as e:
        print(f"Warning: Could not automatically upgrade hardware: {e}")
        print("You may need to manually select the A10G GPU in the Space settings at:")
        print(f"https://huggingface.co/spaces/{repo_id}/settings")

    print("\n✅ Deployment Complete!")
    print(f"Your training job is now building on the cloud: https://huggingface.co/spaces/{repo_id}")
    print("Once it finishes training, it will automatically upload the final model to Helix2003/cts-simulation-v1.")

if __name__ == "__main__":
    deploy()
