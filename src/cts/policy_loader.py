from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Protocol

from cts.config import TrialConfig
from cts.environment.models import Action, TrialState
from cts.policy import LinearPolicy, load_policy_checkpoint
from cts.policy_llm import LLMPolicy, load_llm_policy_checkpoint


class PolicyLike(Protocol):
    def select_action(
        self,
        state: TrialState,
        config: TrialConfig,
        rng: random.Random,
        stochastic: bool = False,
    ) -> Action:
        ...


def checkpoint_exists(path: str | None) -> bool:
    return bool(path) and Path(path).exists()


def load_policy_payload(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def policy_checkpoint_type(path: str) -> str:
    payload = load_policy_payload(path)
    return str(payload.get("policy_type", "unknown"))


def describe_policy_checkpoint(path: str | None) -> dict:
    if not path or not Path(path).exists():
        return {"exists": False, "policy_type": "missing"}

    payload = load_policy_payload(path)
    return {
        "exists": True,
        "policy_type": str(payload.get("policy_type", "unknown")),
        "format_version": payload.get("format_version"),
        "metadata": payload.get("metadata", {}),
        "model_dir": payload.get("model_dir"),
        "model_name": payload.get("model_name"),
        "adapter_dir": payload.get("adapter_dir"),
    }


def load_any_policy_checkpoint(path: str) -> PolicyLike:
    policy_type = policy_checkpoint_type(path)
    if policy_type == "linear_softmax":
        return load_policy_checkpoint(path)
    if policy_type == "llm_causal":
        return load_llm_policy_checkpoint(path)
    raise ValueError(f"Unsupported checkpoint policy type: {policy_type}")


__all__ = [
    "LLMPolicy",
    "LinearPolicy",
    "PolicyLike",
    "checkpoint_exists",
    "describe_policy_checkpoint",
    "load_any_policy_checkpoint",
    "load_policy_payload",
    "policy_checkpoint_type",
]
