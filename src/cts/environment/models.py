from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List


class ActionType(str, Enum):
    RECRUIT = "recruit"
    ADJUST_DOSE = "adjust_dose"
    UPDATE_COMPOSITION = "update_composition"
    HOLD_ENROLLMENT = "hold_enrollment"
    FILE_INTERIM_REPORT = "file_interim_report"
    IMPLEMENT_AMENDMENT = "implement_amendment"
    NOOP = "noop"


class PatientStatus(str, Enum):
    ACTIVE = "active"
    DROPPED_OUT = "dropped_out"
    COMPLETED = "completed"


class DiseaseType(str, Enum):
    TYPE2_DIABETES = "type2_diabetes"
    HYPERTENSION = "hypertension"
    NSCLC = "nsclc"


class ReactionSeverity(str, Enum):
    NONE = "none"
    MINOR = "minor"
    MAJOR = "major"
    FATAL = "fatal"


@dataclass
class Action:
    type: ActionType
    magnitude: float = 0.0
    composition: Dict[str, float] = field(default_factory=dict)


@dataclass
class TrialState:
    week: int = 0
    stage_name: str = "stage1"
    cohort_target: int = 10
    enrolled: int = 0
    active: int = 0
    completed: int = 0
    dropped_out: int = 0
    adverse_events: int = 0
    serious_adverse_events: int = 0
    budget_spent: float = 0.0
    dose_level: float = 1.0
    disease: DiseaseType = DiseaseType.TYPE2_DIABETES
    composition: Dict[str, float] = field(default_factory=lambda: {"a": 0.34, "b": 0.33, "c": 0.33})
    virtual_population_size: int = 1_000_000
    sample_batch_size: int = 2048
    composition_iteration: int = 0
    efficacy_signal: float = 0.0
    biomarker_improvement: float = 0.0
    fatal_reactions: int = 0
    minor_reactions: int = 0
    major_reactions: int = 0
    compliance_incidents: int = 0
    interim_reports_filed: int = 0
    recruitment_hold: bool = False
    fda_sentiment: float = 0.0
    fda_flag: str = "monitoring"
    adverse_event_log: List[int] = field(default_factory=list)


@dataclass
class Observation:
    week: int
    enrolled: int
    active: int
    completed: int
    adverse_events: int
    serious_adverse_events: int
    budget_spent: float
    dose_level: float
    efficacy_signal_estimate: float
    biomarker_improvement_estimate: float
    reaction_histogram: Dict[str, float]
    disease: DiseaseType
    composition: Dict[str, float]
    fda_sentiment: float
    fda_flag: str


@dataclass
class StepResult:
    observation: Observation
    state: TrialState
    terminated: bool
    truncated: bool
    info: dict
