from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class EpisodeTrace:
    episode_id: str
    initial_cohort: list[dict]
    steps: list[dict] = field(default_factory=list)
    final_outcomes: dict[str, float] = field(default_factory=dict)


@dataclass
class HindsightReplayExample:
    original_state: dict
    original_action: dict
    outcome: dict
    better_counterfactual_action: dict
    counterfactual_reward: float
    rationale: str
    evidence_ids: list[str] = field(default_factory=list)


class ReplayBuffer:
    def __init__(self, storage_path: str = "artifacts/replay/buffer.jsonl") -> None:
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

    def store_episode(self, trace: EpisodeTrace) -> None:
        with self.storage_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(trace)) + "\n")

    def generate_hindsight_examples(self, trace: EpisodeTrace) -> list[HindsightReplayExample]:
        examples: list[HindsightReplayExample] = []
        outcomes = trace.final_outcomes
        
        # Example logic: if safety failed, suggest a safer action at key points
        if outcomes.get("serious_adverse_event_rate", 0.0) > 0.15:
            for step in trace.steps:
                if step["action"]["type"] == "recruit" and step["action"]["magnitude"] > 5:
                    examples.append(HindsightReplayExample(
                        original_state=step["state"],
                        original_action=step["action"],
                        outcome=outcomes,
                        better_counterfactual_action={"type": "hold_enrollment", "magnitude": 0.0},
                        counterfactual_reward=0.8,
                        rationale="High serious adverse event rate detected; holding enrollment earlier would have improved safety.",
                        evidence_ids=[]
                    ))
        
        return examples
