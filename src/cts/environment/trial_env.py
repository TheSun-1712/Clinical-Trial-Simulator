from __future__ import annotations

import copy
import random
from dataclasses import asdict
from typing import Optional

from cts.agents.correction_agent import recommend_corrections
from cts.agents.fda_reviewer import evaluate_fda_reviewer
from cts.config import TrialConfig
from cts.data.priors import load_live_priors_or_snapshot
from cts.environment.event_engine import EventEngine
from cts.environment.models import Action, ActionType, Observation, StepResult, TrialState
from cts.curriculum.scheduler import CurriculumTracker
from cts.rewards.anti_cheat import validate_transition
from cts.rewards.verifiers import reward_breakdown
from cts.patient.generator import generate_synthetic_patients


class TrialEnv:
    """Deterministic, seeded trial simulator environment."""

    def __init__(self, config: TrialConfig):
        self.config = config
        self._rng = random.Random(config.seed)
        self._event_engine = EventEngine(config.stage_config.event_rates)
        self._disease_profiles = load_live_priors_or_snapshot(use_live=config.use_live_data_api)
        self._curriculum = CurriculumTracker(current_stage=config.stage_config.name)
        self._state: Optional[TrialState] = None

    @property
    def state(self) -> TrialState:
        if self._state is None:
            raise RuntimeError("Environment must be reset before stepping")
        return self._state

    def reset(self, seed: Optional[int] = None) -> StepResult:
        if seed is None:
            seed = self.config.seed
        self._rng = random.Random(seed)
        stage = self.config.stage_config
        self._event_engine = EventEngine(stage.event_rates)
        self._curriculum = CurriculumTracker(current_stage=stage.name)
        self._state = TrialState(
            week=0,
            stage_name=stage.name,
            cohort_target=stage.cohort_size,
            disease=self.config.disease,
            composition=dict(self.config.initial_composition),
            composite_efficiency=0.0,
            stage_transition_count=0,
            stage_transition_log=[],
            phase_reward_history=[],
            phase_hold_history=[],
            correction_recommendations=[],
        )
        observation = self._to_observation(self._state)
        return StepResult(observation=observation, state=self._state, terminated=False, truncated=False, info={"seed": seed, "stage": stage.name})

    def step(self, action: Action) -> StepResult:
        state = self.state
        next_state = copy.deepcopy(state)
        next_state.week += 1

        self._apply_action(next_state, action)
        
        if hasattr(action, "manager_goal") and action.manager_goal:
            next_state.current_goal = action.manager_goal
            
        disease_profile = self._disease_profiles.get(next_state.disease, self.config.disease_profiles[next_state.disease])
        # 2. Global transitions (PK/PD and drift)
        self._state = self._event_engine.step(next_state, self._rng, config=self.config)
        next_state = self._state

        # 3. Patient-level transitions
        updated_patients = []
        for p in next_state.patient_states:
            if p.status == "active":
                updated = self._event_engine.transition_patient(p, next_state.composition)
                updated_patients.append(updated)
            else:
                updated_patients.append(p)
        next_state.patient_states = updated_patients
        
        # Aggregate metrics from patients
        next_state.active = sum(1 for p in next_state.patient_states if p.status == "active")
        next_state.dropped_out = sum(1 for p in next_state.patient_states if p.status == "dropped_out")
        next_state.completed = sum(1 for p in next_state.patient_states if p.status == "completed")
        # Adverse events are already handled by event_engine.step but we ensure consistency here
        
        # Biomarker update from patients (now also influenced by disease_progression in event_engine)
        active_eff = [p.efficacy_response for p in next_state.patient_states if p.status == "active"]
        if active_eff:
            next_state.biomarker_improvement = sum(active_eff) / len(active_eff)

        next_state.budget_spent += next_state.active * self.config.weekly_active_patient_cost

        fda_sentiment, fda_flag = evaluate_fda_reviewer(next_state, self.config.fda)
        next_state.fda_sentiment = fda_sentiment
        next_state.fda_flag = fda_flag
        if fda_flag == "hold":
            next_state.recruitment_hold = True

        rewards = reward_breakdown(self.config.reward_weights, state, action, next_state)
        next_state.composite_efficiency = rewards["composite_efficiency"]

        had_hold = fda_flag == "hold" or next_state.recruitment_hold
        self._curriculum.update(rewards["total"], had_hold)
        stage_transition = None
        if self._curriculum.can_promote(self.config):
            promoted = self._curriculum.promote()
            if promoted:
                promoted_stage = getattr(self.config, self._curriculum.current_stage)
                stage_transition = {
                    "from_stage": state.stage_name,
                    "to_stage": promoted_stage.name,
                    "week": next_state.week,
                    "window_mean_reward": sum(self._curriculum.reward_history[-promoted_stage.promotion_window :])
                    / min(len(self._curriculum.reward_history), promoted_stage.promotion_window),
                    "had_hold": had_hold,
                }
                next_state.stage_name = promoted_stage.name
                next_state.cohort_target = promoted_stage.cohort_size
                next_state.stage_transition_count += 1
                next_state.last_transition_reason = "curriculum_threshold"
                next_state.stage_transition_log = [*next_state.stage_transition_log, stage_transition]
                self._event_engine = EventEngine(promoted_stage.event_rates)
        next_state.phase_reward_history = list(self._curriculum.reward_history)
        next_state.phase_hold_history = list(self._curriculum.safety_hold_history)

        correction = recommend_corrections(state, action, next_state)
        next_state.correction_recommendations = list(correction["recommendations"])

        validation = validate_transition(state, action, next_state)
        terminated = False
        info = {
            "validation": asdict(validation),
            "reward": rewards,
            "phase": {"stage": next_state.stage_name, "composite_efficiency": next_state.composite_efficiency},
            "correction": correction,
        }
        if stage_transition is not None:
            info["stage_transition"] = stage_transition

        stage = self.config.stage_config if next_state.stage_name == self.config.stage_config.name else getattr(self.config, next_state.stage_name)
        if validation.terminate:
            terminated = True
        if next_state.serious_adverse_events >= stage.max_adverse_events:
            terminated = True
            info["termination_reason"] = "safety_breach"
        if next_state.fatal_reactions > 0:
            terminated = True
            info["termination_reason"] = "fatal_reaction_detected"
        if next_state.completed >= next_state.cohort_target:
            terminated = True
            info["termination_reason"] = "success"
        truncated = next_state.week >= stage.max_weeks

        self._state = next_state
        obs = self._to_observation(next_state)
        return StepResult(observation=obs, state=next_state, terminated=terminated, truncated=truncated, info=info)

    def _apply_action(self, state: TrialState, action: Action) -> None:
        if action.type == ActionType.RECRUIT and not state.recruitment_hold:
            remaining = max(0, state.cohort_target - state.enrolled)
            desired = max(0, int(round(action.magnitude)))
            base = min(remaining, desired)
            recruited_count = self._event_engine.sample_recruitment(base, self._rng)
            recruited_count = min(remaining, recruited_count)
            
            if recruited_count > 0:
                new_patients = generate_synthetic_patients(recruited_count, seed=self._rng.randint(0, 1000000), disease=state.disease)
                state.patient_states.extend(new_patients)
                state.enrolled += recruited_count
                state.active += recruited_count
                state.budget_spent += recruited_count * self.config.recruitment_cost_per_patient
            return

        if action.type == ActionType.ADJUST_DOSE:
            state.dose_level = max(0.5, min(1.5, state.dose_level + action.magnitude))
            if abs(action.magnitude) > 0.3:
                state.compliance_incidents += 1
            comp = dict(state.composition)
            comp["a"] = max(0.0, min(1.0, comp.get("a", 0.0) + (0.04 * action.magnitude)))
            comp["c"] = max(0.0, min(1.0, comp.get("c", 0.0) - (0.03 * action.magnitude)))
            total = max(1e-9, sum(comp.values()))
            state.composition = {k: v / total for k, v in comp.items()}
            state.composition_iteration += 1
            return

        if action.type == ActionType.UPDATE_COMPOSITION:
            if action.composition:
                normalized = self._normalize_composition(action.composition)
                state.composition = normalized
                state.composition_iteration += 1
            else:
                state.compliance_incidents += 1
            return

        if action.type == ActionType.HOLD_ENROLLMENT:
            state.recruitment_hold = True
            return

        if action.type == ActionType.FILE_INTERIM_REPORT:
            state.interim_reports_filed += 1
            if state.fda_flag == "warning":
                state.compliance_incidents = max(0, state.compliance_incidents - 1)
            return

        if action.type == ActionType.IMPLEMENT_AMENDMENT:
            state.compliance_incidents += 1
            state.budget_spent += 12000
            return

    def _to_observation(self, state: TrialState) -> Observation:
        noise = self._rng.uniform(-0.05, 0.05)
        estimate = max(0.0, min(1.0, state.efficacy_signal + noise))
        total_reactions = max(1, state.minor_reactions + state.major_reactions + state.fatal_reactions)
        histogram = {
            "minor": state.minor_reactions / total_reactions,
            "major": state.major_reactions / total_reactions,
            "fatal": state.fatal_reactions / total_reactions,
        }
        return Observation(
            week=state.week,
            stage_name=state.stage_name,
            enrolled=state.enrolled,
            active=state.active,
            completed=state.completed,
            adverse_events=state.adverse_events,
            serious_adverse_events=state.serious_adverse_events,
            budget_spent=state.budget_spent,
            dose_level=state.dose_level,
            drug_concentration=state.drug_concentration,
            cumulative_toxicity=state.cumulative_toxicity,
            disease_progression=state.disease_progression,
            efficacy_signal_estimate=estimate,
            biomarker_improvement_estimate=max(0.0, min(1.0, state.biomarker_improvement + self._rng.uniform(-0.03, 0.03))),
            composite_efficiency=state.composite_efficiency,
            stage_transition_count=state.stage_transition_count,
            recommendation_count=len(state.correction_recommendations),
            reaction_histogram=histogram,
            disease=state.disease,
            composition=state.composition,
            fda_sentiment=state.fda_sentiment,
            fda_flag=state.fda_flag,
        )

    def _normalize_composition(self, composition: dict[str, float]) -> dict[str, float]:
        bounded: dict[str, float] = {}
        for key, value in composition.items():
            lo, hi = self.config.composition_bounds.get(key, (0.0, 1.0))
            bounded[key] = max(lo, min(hi, value))
        total = max(1e-9, sum(bounded.values()))
        return {k: v / total for k, v in bounded.items()}
