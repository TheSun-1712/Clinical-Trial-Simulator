from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cts.environment.models import DiseaseType


def load_snapshot_priors(snapshot_path: str = "data/snapshots/disease_priors.json") -> dict[DiseaseType, dict[str, Any]]:
    path = Path(snapshot_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {DiseaseType(key): value for key, value in payload.items()}


def load_live_priors_or_snapshot(use_live: bool, snapshot_path: str = "data/snapshots/disease_priors.json") -> dict[DiseaseType, dict[str, Any]]:
    """Live refresh hook.

    For hackathon reproducibility, this currently uses snapshot data by default.
    If use_live is enabled, this function can be extended with public API calls.
    """
    _ = use_live
    return load_snapshot_priors(snapshot_path=snapshot_path)
