from __future__ import annotations

import random
from dataclasses import asdict
from typing import Optional

from cts.agents.fda_reviewer import evaluate_fda_reviewer
from cts.config import TrialConfig
from cts.environment.event_engine import EventEngine
from cts.environment.models import Action, ActionType, Observation, StepResult, TrialState
from cts.rewards.anti_cheat import validate_transition


class TrialEnv:
    """Deterministic, seeded trial simulator environment."""

    def __init__(self, config: TrialConfig):
        self.config = config
        self._rng = random.Random(config.seed)
        self._event_engine = EventEngine(config.stage_config.event_rates)
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
        self._state = TrialState(
            week=0,
            stage_name=stage.name,
            cohort_target=stage.cohort_size,
        )
        observation = self._to_observation(self._state)
        return StepResult(observation=observation, state=self._state, terminated=False, truncated=False, info={"seed": seed})

    def step(self, action: Action) -> StepResult:
        state = self.state
        next_state = TrialState(**state.__dict__)
        next_state.week += 1

        self._apply_action(next_state, action)
        next_state = self._event_engine.step(next_state, self._rng)
        next_state.budget_spent += next_state.active * self.config.weekly_active_patient_cost

        fda_sentiment, fda_flag = evaluate_fda_reviewer(next_state, self.config.fda)
        next_state.fda_sentiment = fda_sentiment
        next_state.fda_flag = fda_flag
        if fda_flag == "hold":
            next_state.recruitment_hold = True

        validation = validate_transition(state, action, next_state)
        terminated = False
        info = {"validation": asdict(validation)}

        stage = self.config.stage_config
        if validation.terminate:
            terminated = True
        if next_state.serious_adverse_events >= stage.max_adverse_events:
            terminated = True
            info["termination_reason"] = "safety_breach"
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
            recruited = self._event_engine.sample_recruitment(base, self._rng)
            recruited = min(remaining, recruited)
            state.enrolled += recruited
            state.active += recruited
            state.budget_spent += recruited * self.config.recruitment_cost_per_patient
            return

        if action.type == ActionType.ADJUST_DOSE:
            state.dose_level = max(0.5, min(1.5, state.dose_level + action.magnitude))
            if abs(action.magnitude) > 0.3:
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
        return Observation(
            week=state.week,
            enrolled=state.enrolled,
            active=state.active,
            completed=state.completed,
            adverse_events=state.adverse_events,
            serious_adverse_events=state.serious_adverse_events,
            budget_spent=state.budget_spent,
            dose_level=state.dose_level,
            efficacy_signal_estimate=estimate,
            fda_sentiment=state.fda_sentiment,
            fda_flag=state.fda_flag,
        )
