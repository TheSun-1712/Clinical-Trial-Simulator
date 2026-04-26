from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ActionType(str, Enum):
    RECRUIT = "recruit"
    ADJUST_DOSE = "adjust_dose"
    UPDATE_COMPOSITION = "update_composition"
    HOLD_ENROLLMENT = "hold_enrollment"
    FILE_INTERIM_REPORT = "file_interim_report"
    IMPLEMENT_AMENDMENT = "implement_amendment"
    REQUEST_DSMB_REVIEW = "request_dsmb_review"
    ACTIVATE_SITE = "activate_site"
    ORDER_DRUG_SUPPLY = "order_drug_supply"
    REQUEST_FDA_MEETING = "request_fda_meeting"
    IMPLEMENT_ADAPTIVE_RANDOMIZATION = "implement_adaptive_randomization"
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


class ManagerGoal(str, Enum):
    RECRUIT_PHASE = "recruit_phase"
    SAFETY_PHASE = "safety_phase"
    EFFICACY_PHASE = "efficacy_phase"
    REGULATORY_PHASE = "regulatory_phase"


@dataclass
class Action:
    type: ActionType
    magnitude: float = 0.0
    composition: Dict[str, float] = field(default_factory=dict)
    manager_goal: ManagerGoal = ManagerGoal.RECRUIT_PHASE


@dataclass
class TrialState:
    # ── Core trial state ──────────────────────────────────────────────────────
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
    drug_concentration: float = 0.0
    cumulative_toxicity: float = 0.0
    disease_progression: float = 1.0
    disease: DiseaseType = DiseaseType.TYPE2_DIABETES
    current_goal: ManagerGoal = ManagerGoal.RECRUIT_PHASE
    composition: Dict[str, float] = field(default_factory=lambda: {"a": 0.34, "b": 0.33, "c": 0.33})
    composite_efficiency: float = 0.0
    stage_transition_count: int = 0
    stage_transition_log: List[dict] = field(default_factory=list)
    phase_reward_history: List[float] = field(default_factory=list)
    phase_hold_history: List[bool] = field(default_factory=list)
    correction_recommendations: List[dict] = field(default_factory=list)
    last_transition_reason: str = ""
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
    patient_states: List[Any] = field(default_factory=list)

    # ── Pharmacokinetics (2-compartment) ──────────────────────────────────────
    pk_central_concentration: float = 0.0
    pk_peripheral_concentration: float = 0.0
    pk_auc: float = 0.0
    pk_cmax: float = 0.0
    pk_cmin: float = 0.0
    pk_half_life: float = 0.0
    pk_therapeutic_range: str = "sub_therapeutic"  # sub_therapeutic | therapeutic | toxic
    pk_timeseries: List[dict] = field(default_factory=list)

    # ── RCT Control Arm ───────────────────────────────────────────────────────
    control_arm_size: int = 0
    randomization_ratio: float = 0.5          # fraction assigned to treatment
    control_efficacy: float = 0.25            # placebo response
    control_ae_rate: float = 0.02

    # ── Statistical state ─────────────────────────────────────────────────────
    current_power: float = 0.0
    current_pvalue: float = 1.0
    current_effect_size: float = 0.0
    alpha_spent: float = 0.0
    ci_lower: float = -1.0
    ci_upper: float = 1.0
    stat_recommendation: str = ""

    # ── Multi-site ────────────────────────────────────────────────────────────
    sites: List[dict] = field(default_factory=list)

    # ── Drug supply chain ─────────────────────────────────────────────────────
    drug_supply_available: int = 0
    drug_supply_in_transit: int = 0
    drug_supply_dispensed: int = 0
    drug_supply_wasted: int = 0
    supply_stockout: bool = False
    supply_weeks_remaining: float = 0.0

    # ── Regulatory milestones ─────────────────────────────────────────────────
    milestones: Dict[str, bool] = field(default_factory=lambda: {
        "ind_filed": False,
        "phase1_start": False,
        "phase1_complete": False,
        "eop2_meeting": False,
        "phase3_start": False,
        "phase3_complete": False,
        "nda_filed": False,
    })
    sae_log: List[dict] = field(default_factory=list)
    amendment_count: int = 0

    # ── Pharmacoeconomics ─────────────────────────────────────────────────────
    total_trial_cost: float = 0.0
    cost_per_patient: float = 0.0
    icer: float = 0.0
    nda_probability: float = 0.0
    incremental_qaly: float = 0.0

    # ── Agent outputs ─────────────────────────────────────────────────────────
    cmo_briefing: str = ""
    cmo_status: str = "on_track"
    cmo_urgency: int = 0
    agent_signals: Dict[str, Any] = field(default_factory=dict)
    dsmb_decisions: List[dict] = field(default_factory=list)
    dsmb_latest: Optional[dict] = None
    pk_dose_recommendation: float = 1.0
    retention_high_risk: int = 0
    retention_interventions: List[str] = field(default_factory=list)
    regulatory_next_milestone: str = "phase1_start"
    regulatory_recommendation: str = ""
    economics_recommendation: str = ""

    # ── Primary endpoint ─────────────────────────────────────────────────────
    primary_endpoint_value: float = 0.0
    secondary_endpoint_values: Dict[str, float] = field(default_factory=dict)


@dataclass
class Observation:
    week: int
    stage_name: str
    enrolled: int
    active: int
    completed: int
    adverse_events: int
    serious_adverse_events: int
    budget_spent: float
    dose_level: float
    drug_concentration: float
    cumulative_toxicity: float
    disease_progression: float
    efficacy_signal_estimate: float
    biomarker_improvement_estimate: float
    composite_efficiency: float
    stage_transition_count: int
    recommendation_count: int
    reaction_histogram: Dict[str, float]
    disease: DiseaseType
    composition: Dict[str, float]
    fda_sentiment: float
    fda_flag: str
    # Extended fields exposed in observation
    control_arm_size: int = 0
    current_power: float = 0.0
    current_pvalue: float = 1.0
    pk_central_concentration: float = 0.0
    pk_cmax: float = 0.0
    pk_auc: float = 0.0
    supply_stockout: bool = False
    cmo_status: str = "on_track"
    cmo_urgency: int = 0
    nda_probability: float = 0.0
    icer: float = 0.0


@dataclass
class StepResult:
    observation: Observation
    state: TrialState
    terminated: bool
    truncated: bool
    info: dict
