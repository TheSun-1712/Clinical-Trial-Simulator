from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class EvidenceRecord:
    evidence_id: str
    source_type: str
    source_url: str
    title: str
    disease: str
    intervention: str
    endpoint: str
    phase: str = ""
    safety_terms: list[str] = field(default_factory=list)
    summary: str = ""
    retrieved_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    confidence: float = 0.5
    source_quality: str = "unknown"


class EvidenceStore:
    def __init__(self, path: str = "artifacts/knowledge/evidence.jsonl") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def add(self, record: EvidenceRecord) -> None:
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(record)) + "\n")

    def all(self) -> list[EvidenceRecord]:
        if not self.path.exists():
            return []
        rows: list[EvidenceRecord] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rows.append(EvidenceRecord(**json.loads(line)))
        return rows

    def retrieve(
        self,
        disease: str = "",
        intervention: str = "",
        safety_issue: str = "",
        endpoint: str = "",
        phase: str = "",
    ) -> list[EvidenceRecord]:
        disease_l = disease.lower().strip()
        intervention_l = intervention.lower().strip()
        safety_l = safety_issue.lower().strip()
        endpoint_l = endpoint.lower().strip()
        phase_l = phase.lower().strip()
        
        records = self.all()
        out: list[EvidenceRecord] = []
        for rec in records:
            if disease_l and disease_l not in rec.disease.lower():
                continue
            if intervention_l and intervention_l not in rec.intervention.lower():
                continue
            if endpoint_l and endpoint_l not in rec.endpoint.lower():
                continue
            if safety_l and not any(safety_l in term.lower() for term in rec.safety_terms):
                continue
            if phase_l and phase_l not in getattr(rec, "phase", "").lower():
                continue
            out.append(rec)
        return out

