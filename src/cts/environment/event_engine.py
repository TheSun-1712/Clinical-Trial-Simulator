from __future__ import annotations

import random

from cts.config import EventRates
from cts.environment.models import TrialState


class EventEngine:
    """Seeded event engine for adverse events, dropout, and recruitment variation."""

    def __init__(self, rates: EventRates):
        self.rates = rates

    def step(self, state: TrialState, rng: random.Random) -> TrialState:
        next_state = TrialState(**state.__dict__)

        if next_state.active > 0:
            dropped = 0
            aes = 0
            serious = 0
            for _ in range(next_state.active):
                if rng.random() < self.rates.dropout_prob:
                    dropped += 1
                if rng.random() < self.rates.adverse_event_prob:
                    aes += 1
                    if rng.random() < self.rates.serious_adverse_event_prob:
                        serious += 1

            next_state.active = max(0, next_state.active - dropped)
            next_state.dropped_out += dropped
            next_state.adverse_events += aes
            next_state.serious_adverse_events += serious
            next_state.adverse_event_log.append(aes)

            completed_candidates = max(0, int(0.12 * next_state.active))
            next_state.completed += completed_candidates
            next_state.active = max(0, next_state.active - completed_candidates)

            efficacy_delta = max(0.0, (next_state.dose_level * 0.03) - (serious * 0.01))
            next_state.efficacy_signal = min(1.0, next_state.efficacy_signal + efficacy_delta)

        return next_state

    def sample_recruitment(self, base_count: int, rng: random.Random) -> int:
        jitter = self.rates.recruit_variation
        factor = 1.0 + rng.uniform(-jitter, jitter)
        return max(0, int(round(base_count * factor)))
