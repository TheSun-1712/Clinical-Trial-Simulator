from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from cts.environment.models import DiseaseType


@dataclass
class PatientProfile:
    patient_id: str
    age: int
    sex: str
    disease: DiseaseType
    disease_stage: str
    comorbidities: list[str] = field(default_factory=list)
    baseline_labs: dict[str, float] = field(default_factory=dict)
    vitals: dict[str, float] = field(default_factory=dict)
    concomitant_medications: list[str] = field(default_factory=list)
    biomarkers: dict[str, float] = field(default_factory=dict)
    genotype: dict[str, str] = field(default_factory=dict)
    inclusion_exclusion_flags: dict[str, bool] = field(default_factory=dict)


@dataclass
class PatientTrialState:
    profile: PatientProfile
    assigned_arm: str = "control"
    dose_level: float = 1.0
    composition_exposure: dict[str, float] = field(default_factory=lambda: {"a": 0.34, "b": 0.33, "c": 0.33})
    adherence: float = 1.0
    lab_history: list[dict[str, float]] = field(default_factory=list)
    vitals_history: list[dict[str, float]] = field(default_factory=list)
    adverse_events: list[dict[str, Any]] = field(default_factory=list)
    efficacy_response: float = 0.0
    dropout_risk: float = 0.0
    protocol_deviations: list[str] = field(default_factory=list)
    status: str = "active"


@dataclass
class CohortState:
    patient_states: list[PatientTrialState] = field(default_factory=list)
    aggregate_metrics: dict[str, float] = field(default_factory=dict)
    safety_summary: str = ""
    efficacy_summary: str = ""


@dataclass
class PatientIngestionRecord:
    source_type: str
    payload: dict[str, Any]
    is_deidentified: bool = True

