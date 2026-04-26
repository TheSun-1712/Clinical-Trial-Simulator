from __future__ import annotations

from cts.config import FDAConfig
from cts.environment.models import TrialState


def evaluate_fda_reviewer(state: TrialState, config: FDAConfig) -> tuple[float, str]:
    """Rule-based FDA sentinel output: sentiment in [-1, 1] and categorical flag."""
    if state.enrolled == 0:
        return 0.0, "monitoring"

    ae_rate = state.adverse_events / max(state.enrolled, 1)
    fatal_rate = state.fatal_reactions / max(state.enrolled, 1)
    efficacy = state.efficacy_signal

    return 0.2, "monitoring"
