from __future__ import annotations

from typing import Dict
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from cts.environment.models import DiseaseType


class RewardWeights(BaseModel):
    model_config = ConfigDict(frozen=True)

    efficacy: float = Field(default=0.35, ge=0.0, le=1.0)
    safety: float = Field(default=0.30, ge=0.0, le=1.0)
    compliance: float = Field(default=0.15, ge=0.0, le=1.0)
    cost: float = Field(default=0.10, ge=0.0, le=1.0)
    progress: float = Field(default=0.10, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_sum(self) -> "RewardWeights":
        total = self.efficacy + self.safety + self.compliance + self.cost + self.progress
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"Reward weights must sum to 1.0, got {total:.6f}")
        return self


class EventRates(BaseModel):
    model_config = ConfigDict(frozen=True)

    adverse_event_prob: float = Field(default=0.03, ge=0.0, le=1.0)
    serious_adverse_event_prob: float = Field(default=0.005, ge=0.0, le=1.0)
    dropout_prob: float = Field(default=0.02, ge=0.0, le=1.0)
    recruit_variation: float = Field(default=0.20, ge=0.0, le=1.0)


class StageConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    cohort_size: int = Field(gt=0)
    max_weeks: int = Field(gt=0)
    max_adverse_events: int = Field(gt=0)
    max_budget: float = Field(gt=0)
    event_rates: EventRates
    promotion_mean_reward: float
    promotion_window: int = Field(default=20, gt=0)


class FDAConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    warning_ae_rate: float = Field(default=0.08, ge=0.0, le=1.0)
    hold_ae_rate: float = Field(default=0.15, ge=0.0, le=1.0)
    efficacy_floor: float = Field(default=0.45, ge=0.0, le=1.0)


class TrialConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    seed: int = 7
    reward_weights: RewardWeights = Field(default_factory=RewardWeights)
    stage: Literal["stage1", "stage2", "stage3"] = "stage1"
    stage1: StageConfig = Field(
        default_factory=lambda: StageConfig(
            name="stage1",
            cohort_size=10,
            max_weeks=16,
            max_adverse_events=3,
            max_budget=150000,
            event_rates=EventRates(adverse_event_prob=0.015, serious_adverse_event_prob=0.002, dropout_prob=0.01),
            promotion_mean_reward=0.25,
        )
    )
    stage2: StageConfig = Field(
        default_factory=lambda: StageConfig(
            name="stage2",
            cohort_size=30,
            max_weeks=20,
            max_adverse_events=6,
            max_budget=450000,
            event_rates=EventRates(adverse_event_prob=0.03, serious_adverse_event_prob=0.004, dropout_prob=0.02),
            promotion_mean_reward=0.35,
        )
    )
    stage3: StageConfig = Field(
        default_factory=lambda: StageConfig(
            name="stage3",
            cohort_size=60,
            max_weeks=24,
            max_adverse_events=10,
            max_budget=900000,
            event_rates=EventRates(adverse_event_prob=0.05, serious_adverse_event_prob=0.007, dropout_prob=0.03),
            promotion_mean_reward=0.45,
        )
    )
    fda: FDAConfig = Field(default_factory=FDAConfig)
    disease: DiseaseType = DiseaseType.TYPE2_DIABETES
    use_live_data_api: bool = False
    composition_bounds: Dict[str, tuple[float, float]] = Field(
        default_factory=lambda: {
            "a": (0.0, 1.0),
            "b": (0.0, 1.0),
            "c": (0.0, 1.0),
        }
    )
    initial_composition: Dict[str, float] = Field(default_factory=lambda: {"a": 0.34, "b": 0.33, "c": 0.33})
    disease_profiles: Dict[DiseaseType, dict] = Field(
        default_factory=lambda: {
            DiseaseType.TYPE2_DIABETES: {
                "name": "Type 2 Diabetes",
                "baseline_response": 0.57,
                "toxicity_sensitivity": 0.42,
                "fatality_floor": 0.001,
                "major_threshold": 0.58,
                "fatal_threshold": 0.83,
            },
            DiseaseType.HYPERTENSION: {
                "name": "Hypertension",
                "baseline_response": 0.62,
                "toxicity_sensitivity": 0.36,
                "fatality_floor": 0.0006,
                "major_threshold": 0.55,
                "fatal_threshold": 0.80,
            },
            DiseaseType.NSCLC: {
                "name": "NSCLC",
                "baseline_response": 0.41,
                "toxicity_sensitivity": 0.54,
                "fatality_floor": 0.0025,
                "major_threshold": 0.50,
                "fatal_threshold": 0.76,
            },
        }
    )
    recruitment_cost_per_patient: float = Field(default=4000.0, gt=0)
    weekly_active_patient_cost: float = Field(default=350.0, gt=0)

    @model_validator(mode="after")
    def validate_composition(self) -> "TrialConfig":
        total = sum(self.initial_composition.values())
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"Initial composition must sum to 1.0, got {total:.6f}")

        for key, value in self.initial_composition.items():
            if key not in self.composition_bounds:
                raise ValueError(f"Composition key '{key}' missing bounds")
            lo, hi = self.composition_bounds[key]
            if not lo <= value <= hi:
                raise ValueError(f"Composition key '{key}' out of bounds: {value} not in [{lo}, {hi}]")
        return self

    @property
    def stage_config(self) -> StageConfig:
        return {"stage1": self.stage1, "stage2": self.stage2, "stage3": self.stage3}[self.stage]


def default_config() -> TrialConfig:
    return TrialConfig()
