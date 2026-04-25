from __future__ import annotations

import json
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

DEFAULT_BENCHMARK_DIR = Path("artifacts/benchmark")
LATEST_BENCHMARK_FILE = "latest.json"
LATEST_SUMMARY_FILE = "latest_summary.json"
LATEST_TIMELINE_FILE = "latest_timeline.json"


def to_jsonable(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [to_jsonable(item) for item in value]
    if hasattr(value, "model_dump"):
        return to_jsonable(value.model_dump())
    if hasattr(value, "__dict__") and not isinstance(value, type):
        return to_jsonable(value.__dict__)
    return value


def latest_benchmark_dir(output_dir: str | Path | None = None) -> Path:
    return Path(output_dir) if output_dir is not None else DEFAULT_BENCHMARK_DIR


def save_benchmark_report(report: dict[str, Any], output_dir: str | Path | None = None) -> Path:
    target_dir = latest_benchmark_dir(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    latest_path = target_dir / LATEST_BENCHMARK_FILE
    summary_path = target_dir / LATEST_SUMMARY_FILE
    timeline_path = target_dir / LATEST_TIMELINE_FILE

    latest_path.write_text(json.dumps(to_jsonable(report), indent=2), encoding="utf-8")

    summary_payload = {
        "generated_at": report.get("generated_at"),
        "overall": report.get("overall", {}),
        "policy_rows": report.get("policy_rows", []),
        "disease_metrics": report.get("disease_metrics", {}),
        "phase_metrics": report.get("phase_metrics", {}),
        "correction_summary": report.get("correction_summary", {}),
        "stage_config": report.get("stage_config", {}),
    }
    summary_path.write_text(json.dumps(to_jsonable(summary_payload), indent=2), encoding="utf-8")
    timeline_path.write_text(json.dumps(to_jsonable(report.get("timeline", [])), indent=2), encoding="utf-8")
    return latest_path


def load_latest_benchmark_report(output_dir: str | Path | None = None) -> dict[str, Any] | None:
    latest_path = latest_benchmark_dir(output_dir) / LATEST_BENCHMARK_FILE
    if not latest_path.exists():
        return None
    return json.loads(latest_path.read_text(encoding="utf-8"))


def current_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()
