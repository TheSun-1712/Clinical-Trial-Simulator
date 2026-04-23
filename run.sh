#!/usr/bin/env bash
set -euo pipefail

python -m pip install -e .[test]
pytest -q
python scripts/run_pipeline.py --episodes 50 --checkpoint artifacts/policy/latest.json

if [[ "${LAUNCH_DEMO:-0}" == "1" ]]; then
	streamlit run demo/app.py
fi
