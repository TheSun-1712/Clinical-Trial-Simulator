param(
  [switch]$Train,
  [int]$Episodes = 50,
  [string]$Checkpoint = "artifacts/policy/latest.json",
  [int]$MaxSteps = 0,
  [switch]$LaunchDemo
)

$ErrorActionPreference = "Stop"

python -m pip install -e .[test]
python -m pytest -q

$argsList = @("scripts/run_pipeline.py", "--episodes", "$Episodes", "--checkpoint", "$Checkpoint")
if ($Train) { $argsList += "--train" }
if ($MaxSteps -gt 0) { $argsList += @("--max-steps", "$MaxSteps") }
if ($LaunchDemo) { $argsList += "--launch-demo" }

python @argsList
