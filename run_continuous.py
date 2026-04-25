import subprocess
import sys
import traceback

command = [
    sys.executable,
    "scripts/continuous_neural_training.py",
    "--config", "training/configs/grpo_medium.yaml",
    "--checkpoint", "artifacts/policy/latest_llm.json",
    "--backend", "lightweight",
    "--max-steps-per-cycle", "5",
    "--max-cycles", "1"
]

try:
    print(f"Running command: {' '.join(command)}")
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"FAILED with exit code {result.returncode}")
        print("--- STDOUT ---")
        print(result.stdout)
        print("--- STDERR ---")
        print(result.stderr)
    else:
        print("SUCCESS!")
        print(result.stdout)
except Exception as e:
    traceback.print_exc()
