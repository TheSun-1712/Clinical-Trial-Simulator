from __future__ import annotations

import random
from dataclasses import dataclass

from cts.config import EventRates
from cts.environment.models import ReactionSeverity, TrialState


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

    def step(self, state: TrialState, rng: random.Random, disease_profile: dict | None = None) -> TrialState:
        next_state = TrialState(**state.__dict__)
        profile = disease_profile or {
            "baseline_response": 0.55,
            "toxicity_sensitivity": 0.4,
            "fatality_floor": 0.001,
            "major_threshold": 0.58,
            "fatal_threshold": 0.82,
        }

        if next_state.active > 0:
            dropped = 0
            aes = 0
            serious = 0
            fatal = 0
            minor = 0
            major = 0
            improvement_sum = 0.0
            for _ in range(min(next_state.active, next_state.sample_batch_size)):
                latent = self._sample_patient_latent(rng)
                efficacy, toxicity = self._simulate_response(latent, next_state.composition, profile, rng)
                reaction = self._classify_reaction(toxicity, profile)

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

                if rng.random() < self.rates.dropout_prob:
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
            efficacy_delta = max(0.0, next_state.biomarker_improvement * 0.06 - (serious * 0.002) - (fatal * 0.02))
            next_state.efficacy_signal = min(1.0, next_state.efficacy_signal + efficacy_delta)

        return next_state

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
        )
        toxicity = (
            tox_sensitivity
            + 0.35 * c_c * (0.6 + latent.immune_reactivity)
            + 0.18 * c_b * latent.age_factor
            + 0.12 * latent.comorbidity
            - 0.08 * c_a
            + rng.gauss(0.0, 0.035)
        )

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
