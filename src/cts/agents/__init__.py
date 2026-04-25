"""Agent modules."""

from cts.agents.correction_agent import CorrectionRecommendation, recommend_corrections
from cts.agents.specialized import (
    AgentOutput,
    ChiefTrialScientistAgent,
    DrugCompositionAgent,
    EfficacyAgent,
    HindsightReplayAgent,
    LiteratureEvidenceAgent,
    PatientSafetyAgent,
    RegulatoryAgent,
    TrialOpsAgent,
)

__all__ = [
    "CorrectionRecommendation",
    "recommend_corrections",
    "AgentOutput",
    "PatientSafetyAgent",
    "EfficacyAgent",
    "TrialOpsAgent",
    "RegulatoryAgent",
    "LiteratureEvidenceAgent",
    "DrugCompositionAgent",
    "HindsightReplayAgent",
    "ChiefTrialScientistAgent",
]
