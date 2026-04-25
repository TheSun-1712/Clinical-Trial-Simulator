FROM python:3.11-slim

WORKDIR /app

# Install git for cloning and system deps
RUN apt-get update && apt-get install -y git build-essential

# Copy the repository
COPY . /app/

# Install the project and dependencies
RUN pip install --no-cache-dir -e .[train]

# Start the training script. 
# It will train, evaluate, and then upload the final artifacts back to your HF account.
CMD ["python", "scripts/run_hf_training.py", "--config", "training/configs/grpo_medium.yaml", "--upload-manifest-repo", "Helix2003/cts-simulation-v1", "--upload-private", "--skip-install"]
