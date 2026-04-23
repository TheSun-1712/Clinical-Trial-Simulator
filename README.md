# Clinical Trial Simulator

Deterministic RL environment for a trial coordinator policy with verifiable, weighted rewards.

## MVP floor

- Seeded deterministic environment
- Independent reward component logs
- Random baseline vs heuristic vs trained policy benchmark table
- Streamlit demo with interactive and benchmark tabs

## Quickstart

```bash
python -m venv .venv
. .venv/Scripts/activate
pip install -e .[test]
pytest -q
python -m eval.run_benchmark --trained-checkpoint artifacts/policy/latest.json
streamlit run demo/app.py
```

## Training

```bash
python training/train_grpo.py --config training/configs/grpo_medium.yaml
```

The default path runs a lightweight grouped-relative policy optimization loop and writes
`artifacts/policy/latest.json`. This checkpoint is loaded by benchmark and demo as the trained policy.

Optional GPU path:

```bash
pip install -e .[train]
python training/train_grpo.py --backend trl-unsloth --config training/configs/grpo_medium.yaml
```

Notes:

- On Windows (especially Python 3.14), install of `. [train]` uses TRL stack without Unsloth.
- Strict `trl-unsloth` backend is intended for Linux GPU environments.
- For local Windows execution, use `--backend lightweight` or `--allow-fallback`.

Strict mode is default for trl-unsloth backend. If dependencies are missing and you still
want local execution, add --allow-fallback.

```bash
python training/train_grpo.py --backend trl-unsloth --allow-fallback --config training/configs/grpo_medium.yaml --max-steps 100
```

## End-to-end pipeline

```bash
python scripts/run_pipeline.py --train --episodes 50 --checkpoint artifacts/policy/latest.json
```

PowerShell helper:

```powershell
./run.ps1 -Train -Episodes 50 -Checkpoint artifacts/policy/latest.json
```

## API and OpenEnv integration

```bash
uvicorn server.openenv_api:app --reload
```

OpenEnv endpoints:

- `GET /openenv/metadata`
- `POST /openenv/reset`
- `POST /openenv/step`

Client smoke example:

```bash
python server/openenv_client_example.py
```

## Spaces deployment

Build from Docker:

```bash
docker build -f docker/Dockerfile.openenv -t clinical-trial-openenv .
docker run -p 8000:8000 clinical-trial-openenv
```

Space descriptor for Docker runtime is provided at `server/openenv.space.yaml`.
