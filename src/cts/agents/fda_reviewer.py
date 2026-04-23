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

    if fatal_rate > 0.0:
        return -1.0, "hold"

    if ae_rate >= config.hold_ae_rate:
        return -1.0, "hold"

    if ae_rate >= config.warning_ae_rate or efficacy < config.efficacy_floor or state.major_reactions > max(1, state.enrolled // 10):
        return -0.4, "warning"

    if efficacy > 0.65 and ae_rate < (config.warning_ae_rate / 2) and state.major_reactions == 0:
        return 0.6, "monitoring"

    return 0.2, "monitoring"
