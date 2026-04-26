from __future__ import annotations

import copy
import random
from dataclasses import asdict
from typing import Optional

from cts.agents.correction_agent import recommend_corrections
from cts.agents.fda_reviewer import evaluate_fda_reviewer
from cts.agents.chief_medical_officer_agent import ChiefMedicalOfficerAgent
from cts.config import TrialConfig
from cts.data.priors import load_live_priors_or_snapshot
from cts.environment.event_engine import EventEngine
from cts.environment.models import Action, ActionType, Observation, StepResult, TrialState
from cts.curriculum.scheduler import CurriculumTracker
from cts.pk import TwoCompartmentPK, PKParameters
from cts.rewards.anti_cheat import validate_transition
from cts.rewards.verifiers import reward_breakdown
from cts.patient.generator import generate_synthetic_patients
from cts.site.site_manager import SiteManager
from cts.supply.drug_supply import DrugSupplyChain
from cts.statistics.power_analysis import InterimAnalysis, required_sample_size


class TrialEnv:
    """
    Comprehensive clinical trial simulator.
    Includes: RCT control arm, 2-compartment PK, multi-site,
    drug supply chain, DSMB, biostatistician, PK agent,
    patient advocate, regulatory affairs, and pharmacoeconomics.
    """

    N_SITES = 8
    INITIAL_SUPPLY_UNITS = 500

    def __init__(self, config: TrialConfig):
        self.config = config
        self._rng = random.Random(config.seed)
        self._event_engine = EventEngine(config.stage_config.event_rates)
        self._disease_profiles = load_live_priors_or_snapshot(use_live=config.use_live_data_api)
        self._curriculum = CurriculumTracker(current_stage=config.stage_config.name)
        self._state: Optional[TrialState] = None

        # New subsystems
        self._pk_model = TwoCompartmentPK()
        self._site_manager = SiteManager(n_sites=self.N_SITES, rng=self._rng)
        self._supply = DrugSupplyChain()
        self._cmo = ChiefMedicalOfficerAgent()

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
        self._pk_model = TwoCompartmentPK()
        self._site_manager = SiteManager(n_sites=self.N_SITES, rng=self._rng)
        self._supply = DrugSupplyChain()
        self._cmo = ChiefMedicalOfficerAgent()

        # Schedule site activations over first 3rd of trial
        self._site_manager.schedule_activations(stage.max_weeks)

        # Initial drug supply order
        self._supply.order(self.INITIAL_SUPPLY_UNITS, current_week=0)

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
            drug_supply_available=self.INITIAL_SUPPLY_UNITS,
            milestones={"ind_filed": True, "phase1_start": False,
                        "phase1_complete": False, "eop2_meeting": False,
                        "phase3_start": False, "phase3_complete": False, "nda_filed": False},
        )
        observation = self._to_observation(self._state)
        return StepResult(
            observation=observation, state=self._state,
            terminated=False, truncated=False,
            info={"seed": seed, "stage": stage.name}
        )

    def step(self, action: Action) -> StepResult:
        state = self.state
        next_state = copy.deepcopy(state)
        next_state.week += 1

        # 1. Apply agent action
        self._apply_action(next_state, action)

        if hasattr(action, "manager_goal") and action.manager_goal:
            next_state.current_goal = action.manager_goal

        # 2. Multi-site step → recruits patients
        site_new_patients, site_snapshots = self._site_manager.step(next_state.week)
        next_state.sites = site_snapshots

        # 3. Auto-recruit from sites if not on hold
        if site_new_patients > 0 and not next_state.recruitment_hold:
            remaining = max(0, next_state.cohort_target - next_state.enrolled)
            recruited = min(remaining, site_new_patients)
            if recruited > 0:
                new_pats = generate_synthetic_patients(
                    recruited, seed=self._rng.randint(0, 1_000_000), disease=next_state.disease
                )
                # RCT randomization: assign to treatment or control arm
                for p in new_pats:
                    if self._rng.random() < next_state.randomization_ratio:
                        p.assigned_arm = "treatment"
                    else:
                        p.assigned_arm = "control"
                        next_state.control_arm_size += 1
                next_state.patient_states.extend(new_pats)
                next_state.enrolled += recruited
                next_state.active += recruited
                next_state.budget_spent += recruited * self.config.recruitment_cost_per_patient

        # 4. PK model step — dose the drug
        self._pk_model.dose(next_state.dose_level * 100, cyp_genotype="normal")
        pk_summary = self._pk_model.step()
        next_state.pk_central_concentration = pk_summary["c_central"]
        next_state.pk_peripheral_concentration = pk_summary["c_peripheral"]
        next_state.pk_auc = pk_summary["auc"]
        next_state.pk_cmax = pk_summary["cmax"]
        next_state.pk_cmin = pk_summary["cmin"]
        next_state.pk_half_life = pk_summary["t_half_weeks"]
        next_state.pk_therapeutic_range = self._pk_model.therapeutic_range()
        # Update drug_concentration used by event engine from PK model
        next_state.drug_concentration = pk_summary["c_central"]
        next_state.pk_timeseries = next_state.pk_timeseries[-50:] + [pk_summary]

        # 5. Global event engine step (disease progression, aggregate PK/PD)
        disease_profile = self._disease_profiles.get(next_state.disease, self.config.disease_profiles[next_state.disease])
        self._state = self._event_engine.step(next_state, self._rng, config=self.config)
        next_state = self._state

        # 6. Per-patient transitions
        updated_patients = []
        for p in next_state.patient_states:
            if p.status == "active":
                updated = self._event_engine.transition_patient(p, next_state.composition)
                updated_patients.append(updated)
            else:
                updated_patients.append(p)
        next_state.patient_states = updated_patients

        # 7. Aggregate patient metrics
        next_state.active = sum(1 for p in next_state.patient_states if p.status == "active")
        next_state.dropped_out = sum(1 for p in next_state.patient_states if p.status == "dropped_out")
        next_state.completed = sum(1 for p in next_state.patient_states if p.status == "completed")

        # 8. Biomarker improvement from treatment arm only (RCT)
        treatment_pats = [p for p in next_state.patient_states
                          if p.status == "active" and getattr(p, "assigned_arm", "treatment") == "treatment"]
        control_pats = [p for p in next_state.patient_states
                        if p.status == "active" and getattr(p, "assigned_arm", "treatment") == "control"]
        if treatment_pats:
            next_state.biomarker_improvement = sum(p.efficacy_response for p in treatment_pats) / len(treatment_pats)
        if control_pats:
            next_state.control_efficacy = sum(p.efficacy_response for p in control_pats) / len(control_pats)

        # 9. Drug supply step
        supply_result = self._supply.step(n_active_patients=next_state.active, current_week=next_state.week)
        supply_snap = self._supply.snapshot(next_state.week)
        next_state.drug_supply_available = supply_snap["available_units"]
        next_state.drug_supply_in_transit = supply_snap["in_transit_units"]
        next_state.drug_supply_dispensed = supply_snap["total_dispensed"]
        next_state.drug_supply_wasted = supply_snap["total_wasted"]
        next_state.supply_stockout = supply_result["stockout"]
        next_state.supply_weeks_remaining = supply_snap["weeks_of_supply"]

        # Auto-reorder if supply drops below 8 weeks
        if self._supply.weeks_of_supply_remaining(max(1, next_state.active), next_state.week) < 8:
            self._supply.order(units=next_state.active * 12, current_week=next_state.week)

        # 10. Budget
        next_state.budget_spent += next_state.active * self.config.weekly_active_patient_cost

        # 11. FDA review
        fda_sentiment, fda_flag = evaluate_fda_reviewer(next_state, self.config.fda)
        next_state.fda_sentiment = fda_sentiment
        next_state.fda_flag = fda_flag
        if fda_flag == "hold":
            next_state.recruitment_hold = True

        # 12. Rewards
        rewards = reward_breakdown(self.config.reward_weights, state, action, next_state)
        next_state.composite_efficiency = rewards["composite_efficiency"]

        # 13. Curriculum
        had_hold = fda_flag == "hold" or next_state.recruitment_hold
        self._curriculum.update(rewards["total"], had_hold)
        stage_transition = None
        if self._curriculum.can_promote(self.config):
            promoted = self._curriculum.promote()
            if promoted:
                promoted_stage = getattr(self.config, self._curriculum.current_stage)
                stage_transition = {
                    "from_stage": state.stage_name, "to_stage": promoted_stage.name,
                    "week": next_state.week,
                    "window_mean_reward": sum(self._curriculum.reward_history[-promoted_stage.promotion_window:])
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

        # 14. Correction agent
        correction = recommend_corrections(state, action, next_state)
        next_state.correction_recommendations = list(correction["recommendations"])

        # 15. CMO + all specialized agents
        try:
            briefing = self._cmo.run(next_state)
            next_state.cmo_briefing = briefing.full_briefing
            next_state.cmo_status = briefing.overall_status
            next_state.cmo_urgency = briefing.urgency_level
            next_state.agent_signals = briefing.agent_signals
            next_state.dsmb_decisions = self._cmo.dsmb.all_decisions()
            next_state.dsmb_latest = self._cmo.dsmb.latest()

            # Surface key agent outputs to state
            pk_rec = briefing.agent_signals.get("Pharmacokineticist", {})
            next_state.pk_dose_recommendation = pk_rec.get("dose_recommendation", next_state.dose_level)
            adv = briefing.agent_signals.get("PatientAdvocate", {})
            next_state.retention_high_risk = adv.get("high_risk_count", 0)
            next_state.retention_interventions = adv.get("interventions", [])
            reg = briefing.agent_signals.get("RegulatoryAffairs", {})
            next_state.regulatory_next_milestone = reg.get("next_milestone", "")
            next_state.regulatory_recommendation = reg.get("recommendation", "")
            econ = briefing.agent_signals.get("PharmacoEconomics", {})
            next_state.icer = econ.get("icer", 0)
            next_state.nda_probability = econ.get("nda_probability", 0)
            next_state.economics_recommendation = econ.get("recommendation", "")
            stat = briefing.agent_signals.get("Biostatistician", {})
            next_state.current_power = stat.get("power", 0)
            next_state.current_pvalue = stat.get("p_value", 1.0)
            next_state.stat_recommendation = stat.get("recommendation", "")
            milestones = reg.get("milestones", {})
            if milestones:
                next_state.milestones = milestones
        except Exception as e:
            next_state.cmo_briefing = f"Agent error: {e}"

        # 16. Validation & termination
        validation = validate_transition(state, action, next_state)
        terminated = False
        info = {
            "validation": asdict(validation),
            "reward": rewards,
            "phase": {"stage": next_state.stage_name, "composite_efficiency": next_state.composite_efficiency},
            "correction": correction,
            "pk": pk_summary,
            "supply": supply_result,
            "cmo_status": next_state.cmo_status,
        }
        if stage_transition is not None:
            info["stage_transition"] = stage_transition

        stage = self.config.stage_config if next_state.stage_name == self.config.stage_config.name \
            else getattr(self.config, next_state.stage_name)
        if validation.terminate:
            terminated = True
        if next_state.serious_adverse_events >= stage.max_adverse_events:
            terminated = True; info["termination_reason"] = "safety_breach"
        if next_state.fatal_reactions > 0:
            terminated = True; info["termination_reason"] = "fatal_reaction_detected"
        if next_state.completed >= next_state.cohort_target and next_state.week >= stage.max_weeks:
            terminated = True; info["termination_reason"] = "success"
        if next_state.cmo_status == "stopped":
            terminated = True; info["termination_reason"] = "dsmb_stop"
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
                new_patients = generate_synthetic_patients(
                    recruited_count, seed=self._rng.randint(0, 1_000_000), disease=state.disease
                )
                for p in new_patients:
                    p.assigned_arm = "treatment" if self._rng.random() < state.randomization_ratio else "control"
                    if p.assigned_arm == "control":
                        state.control_arm_size += 1
                state.patient_states.extend(new_patients)
                state.enrolled += recruited_count
                state.active += recruited_count
                state.budget_spent += recruited_count * self.config.recruitment_cost_per_patient
            return

        if action.type == ActionType.ADJUST_DOSE:
            state.dose_level = max(0.3, min(2.0, state.dose_level + action.magnitude))
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
                state.composition = self._normalize_composition(action.composition)
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
            state.budget_spent += 12_000
            self._cmo.regulatory.log_amendment("Protocol amendment", state.week)
            state.amendment_count += 1
            return

        if action.type == ActionType.ORDER_DRUG_SUPPLY:
            units = max(100, int(action.magnitude) if action.magnitude > 0 else 200)
            self._supply.order(units, current_week=state.week)
            return

        if action.type == ActionType.REQUEST_DSMB_REVIEW:
            # Force an out-of-schedule DSMB review
            dec = self._cmo.dsmb.review(state)
            if dec:
                state.dsmb_decisions = self._cmo.dsmb.all_decisions()
                state.dsmb_latest = self._cmo.dsmb.latest()
            return

        if action.type == ActionType.REQUEST_FDA_MEETING:
            state.fda_sentiment = min(1.0, state.fda_sentiment + 0.05)
            state.budget_spent += 50_000
            return

        if action.type == ActionType.IMPLEMENT_ADAPTIVE_RANDOMIZATION:
            # Shift randomization toward treatment if efficacy signal is strong
            if state.biomarker_improvement > 0.5:
                state.randomization_ratio = min(0.80, state.randomization_ratio + 0.05)
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
            control_arm_size=state.control_arm_size,
            current_power=state.current_power,
            current_pvalue=state.current_pvalue,
            pk_central_concentration=state.pk_central_concentration,
            pk_cmax=state.pk_cmax,
            pk_auc=state.pk_auc,
            supply_stockout=state.supply_stockout,
            cmo_status=state.cmo_status,
            cmo_urgency=state.cmo_urgency,
            nda_probability=state.nda_probability,
            icer=state.icer,
        )

    def _normalize_composition(self, composition: dict[str, float]) -> dict[str, float]:
        bounded = {}
        for key, value in composition.items():
            lo, hi = self.config.composition_bounds.get(key, (0.0, 1.0))
            bounded[key] = max(lo, min(hi, value))
        total = max(1e-9, sum(bounded.values()))
        return {k: v / total for k, v in bounded.items()}

    def agent_outputs(self) -> dict:
        """Return latest outputs from all agents for API endpoints."""
        signals = self._cmo.latest_signals()
        state = self._state
        if state is None:
            return signals
        return {
            **signals,
            "pk_snapshot": {
                "c_central": state.pk_central_concentration,
                "c_peripheral": state.pk_peripheral_concentration,
                "auc": state.pk_auc,
                "cmax": state.pk_cmax,
                "cmin": state.pk_cmin,
                "t_half": state.pk_half_life,
                "therapeutic_range": state.pk_therapeutic_range,
                "timeseries": state.pk_timeseries[-30:],
            },
            "supply_snapshot": self._supply.snapshot(state.week) if state else {},
            "sites_snapshot": self._site_manager.snapshot(),
            "dsmb_decisions": self._cmo.dsmb.all_decisions(),
            "agent_signals": state.agent_signals if state else {},
        }
