from __future__ import annotations

import copy
import random
from dataclasses import dataclass
from datetime import datetime, timezone

from cts.config import EventRates
from cts.environment.models import ReactionSeverity, TrialState
from cts.patient.models import PatientTrialState


@dataclass
class PatientLatent:
    metabolism: float
    immune_reactivity: float
    age_factor: float
    comorbidity: float


class EventEngine:
    """Seeded event engine for adverse events, dropout, and recruitment variation."""

    def __init__(self, rates: EventRates):
        self.rates = rates

    def transition_patient(self, state: PatientTrialState, global_composition: dict[str, float]) -> PatientTrialState:
        # Update composition exposure
        state.composition_exposure = dict(global_composition)
        
        # Calculate efficacy probability
        eff_prob = 0.4 * state.composition_exposure.get("a", 0.0) + 0.2 * state.composition_exposure.get("b", 0.0)
        if state.profile.disease_stage == "severe":
            eff_prob *= 0.8
        eff_prob += 0.1 * state.profile.biomarkers.get("marker_a", 0.5)
        
        state.efficacy_response = min(1.0, eff_prob + random.uniform(-0.05, 0.05))
        
        # Calculate toxicity probability
        tox_prob = 0.5 * state.composition_exposure.get("c", 0.0) + 0.1 * state.composition_exposure.get("b", 0.0)
        if state.profile.age > 65:
            tox_prob *= 1.2
        if state.profile.genotype.get("cyp2d6") == "poor":
            tox_prob *= 1.5
            
        if random.random() < tox_prob:
            grade = 1
            if tox_prob > 0.4 and random.random() < 0.2:
                grade = 3
            elif tox_prob > 0.6 and random.random() < 0.1:
                grade = 4
                
            ae = {
                "term": "Neutropenia" if random.random() < 0.5 else "Nausea",
                "grade": grade,
                "is_serious": grade >= 3,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            state.adverse_events.append(ae)
            
        # Calculate dropout risk
        base_dropout = 0.05
        if state.adverse_events and any(ae["grade"] >= 3 for ae in state.adverse_events):
            base_dropout += 0.3
        if state.efficacy_response < 0.1:
            base_dropout += 0.1
            
        state.dropout_risk = min(1.0, base_dropout)
        if random.random() < state.dropout_risk:
            state.status = "dropped_out"
            
        state.lab_history.append({"alt": 25.0 + random.uniform(-5, 5)})
        return state

    def step(self, state: TrialState, rng: random.Random, config: TrialConfig | None = None) -> TrialState:
        next_state = copy.deepcopy(state)
        # Handle config fallback for legacy calls
        from cts.config import default_config
        cfg = config or default_config()
        
        disease_profile = cfg.disease_profiles.get(next_state.disease, {})
        phase_profile = self._phase_profile(next_state.stage_name)
        
        # 1. Update Pharmacokinetics (Concentration)
        # Absorption of the current dose level
        absorbed = next_state.dose_level * cfg.pk_absorption_rate
        # Elimination of existing concentration
        next_state.drug_concentration = (next_state.drug_concentration * (1.0 - cfg.pk_elimination_rate)) + absorbed
        
        # 2. Update Disease Progression (Drift)
        # Base drift (biomarkers getting worse)
        drift = disease_profile.get("drift_rate", cfg.disease_drift_base)
        # PD effect: Drug concentration reduces disease progression
        # Emax model: effect = (Emax * C) / (EC50 + C)
        concentration = next_state.drug_concentration
        pd_effect = (cfg.pd_emax * concentration) / (cfg.pd_ec50 + concentration)
        
        # Update disease progression state (e.g. tumor size decreases with effect, HbA1c decreases with effect)
        # We model progression as a value that increases with drift and decreases with pd_effect
        next_state.disease_progression = max(0.1, next_state.disease_progression + drift - (pd_effect * 0.15))

        if next_state.active > 0:
            dropped = 0
            aes = 0
            serious = 0
            fatal = 0
            minor = 0
            major = 0
            improvement_sum = 0.0
            
            # Toxicity also follows a PK/PD relationship
            # Cumulative toxicity increases if concentration is high
            tox_spike = max(0.0, next_state.drug_concentration - 0.7) * 0.1
            next_state.cumulative_toxicity = max(0.0, next_state.cumulative_toxicity * 0.9 + tox_spike)

            for _ in range(min(next_state.active, next_state.sample_batch_size)):
                latent = self._sample_patient_latent(rng)
                
                # Efficacy and Toxicity are now influenced by the PK/PD state
                efficacy, toxicity = self._simulate_response_pkpd(
                    latent,
                    next_state.composition,
                    next_state.drug_concentration,
                    next_state.cumulative_toxicity,
                    disease_profile,
                    rng,
                    phase_boost=phase_profile["response_boost"],
                    phase_tox_scale=phase_profile["toxicity_scale"],
                )
                
                reaction = self._classify_reaction(toxicity, disease_profile)

                if reaction != ReactionSeverity.NONE:
                    aes += 1
                if reaction in {ReactionSeverity.MAJOR, ReactionSeverity.FATAL}:
                    serious += 1
                if reaction == ReactionSeverity.MINOR:
                    minor += 1
                if reaction == ReactionSeverity.MAJOR:
                    major += 1
                if reaction == ReactionSeverity.FATAL:
                    fatal += 1

                improvement_sum += efficacy

                if rng.random() < min(1.0, self.rates.dropout_prob * phase_profile["dropout_scale"] * (1.0 + next_state.cumulative_toxicity)):
                    dropped += 1

            next_state.active = max(0, next_state.active - dropped)
            next_state.dropped_out += dropped
            next_state.adverse_events += aes
            next_state.serious_adverse_events += serious
            next_state.fatal_reactions += fatal
            next_state.minor_reactions += minor
            next_state.major_reactions += major
            next_state.adverse_event_log.append(aes)

            completed_candidates = max(0, int(0.12 * next_state.active))
            next_state.completed += completed_candidates
            next_state.active = max(0, next_state.active - completed_candidates)

            sampled = max(1, min(next_state.enrolled, next_state.sample_batch_size))
            avg_improvement = improvement_sum / sampled
            next_state.biomarker_improvement = max(0.0, min(1.0, avg_improvement))
            
            # Efficacy signal is a rolling estimate influenced by progression
            efficacy_delta = max(0.0, (1.0 - next_state.disease_progression) * 0.1 - (serious * 0.002))
            next_state.efficacy_signal = min(1.0, next_state.efficacy_signal * 0.9 + efficacy_delta)

        return next_state

    def _simulate_response_pkpd(
        self,
        latent: PatientLatent,
        composition: dict[str, float],
        concentration: float,
        cumulative_toxicity: float,
        disease_profile: dict,
        rng: random.Random,
        phase_boost: float = 1.0,
        phase_tox_scale: float = 1.0,
    ) -> tuple[float, float]:
        c_a = composition.get("a", 0.0)
        c_b = composition.get("b", 0.0)
        c_c = composition.get("c", 0.0)

        # Base efficacy derived from concentration and composition
        # Composition 'a' and 'b' are active, 'c' is toxic
        efficacy_potency = (0.4 * c_a + 0.3 * c_b - 0.1 * c_c)
        efficacy = (
            disease_profile.get("baseline_response", 0.5)
            + (efficacy_potency * concentration * (1.0 - latent.comorbidity))
            + rng.gauss(0.0, 0.04)
        ) * phase_boost

        # Toxicity derived from concentration, cumulative burden, and composition 'c'
        tox_sensitivity = disease_profile.get("toxicity_sensitivity", 0.4)
        toxicity = (
            tox_sensitivity
            + (0.5 * c_c * concentration)
            + (0.2 * cumulative_toxicity)
            + (0.1 * latent.age_factor)
            + rng.gauss(0.0, 0.05)
        ) * phase_tox_scale

        return (max(0.0, min(1.0, efficacy)), max(0.0, min(1.0, toxicity)))

    def _phase_profile(self, stage_name: str) -> dict[str, float]:
        if stage_name == "stage1":
            return {"response_boost": 0.95, "toxicity_scale": 1.08, "dropout_scale": 1.05}
        if stage_name == "stage2":
            return {"response_boost": 1.0, "toxicity_scale": 1.0, "dropout_scale": 1.0}
        return {"response_boost": 1.05, "toxicity_scale": 0.92, "dropout_scale": 0.94}

    def _sample_patient_latent(self, rng: random.Random) -> PatientLatent:
        return PatientLatent(
            metabolism=min(1.0, max(0.0, rng.gauss(0.55, 0.2))),
            immune_reactivity=min(1.0, max(0.0, rng.gauss(0.50, 0.2))),
            age_factor=min(1.0, max(0.0, rng.gauss(0.52, 0.22))),
            comorbidity=min(1.0, max(0.0, rng.gauss(0.45, 0.24))),
        )

    def _simulate_response(
        self,
        latent: PatientLatent,
        composition: dict[str, float],
        disease_profile: dict,
        rng: random.Random,
        phase_response_boost: float = 1.0,
        phase_toxicity_scale: float = 1.0,
    ) -> tuple[float, float]:
        c_a = composition.get("a", 0.0)
        c_b = composition.get("b", 0.0)
        c_c = composition.get("c", 0.0)

        efficacy_base = disease_profile["baseline_response"]
        tox_sensitivity = disease_profile["toxicity_sensitivity"]

        efficacy = (
            efficacy_base
            + 0.30 * c_a * (1.0 - latent.comorbidity)
            + 0.18 * c_b * latent.metabolism
            - 0.10 * c_c * latent.immune_reactivity
            + rng.gauss(0.0, 0.03)
        ) * phase_response_boost
        toxicity = (
            tox_sensitivity
            + 0.35 * c_c * (0.6 + latent.immune_reactivity)
            + 0.18 * c_b * latent.age_factor
            + 0.12 * latent.comorbidity
            - 0.08 * c_a
            + rng.gauss(0.0, 0.035)
        ) * phase_toxicity_scale

        return (max(0.0, min(1.0, efficacy)), max(0.0, min(1.0, toxicity)))

    def _classify_reaction(self, toxicity: float, disease_profile: dict) -> ReactionSeverity:
        if toxicity >= disease_profile["fatal_threshold"]:
            return ReactionSeverity.FATAL
        if toxicity >= disease_profile["major_threshold"]:
            return ReactionSeverity.MAJOR
        if toxicity >= self.rates.adverse_event_prob:
            return ReactionSeverity.MINOR
        return ReactionSeverity.NONE

    def sample_recruitment(self, base_count: int, rng: random.Random) -> int:
        jitter = self.rates.recruit_variation
        factor = 1.0 + rng.uniform(-jitter, jitter)
        return max(0, int(round(base_count * factor)))
