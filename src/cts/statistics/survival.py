"""Competing-risks survival model for clinical trial patient outcomes."""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import List


@dataclass
class PatientSurvivalState:
    patient_id: str
    entry_week: int = 0
    # Weibull shape/scale per risk
    shape_dropout: float = 1.5
    scale_dropout: float = 40.0
    shape_ae_serious: float = 2.0
    scale_ae_serious: float = 52.0
    shape_completion: float = 1.0
    scale_completion: float = 48.0
    # Observed
    event: str = "censored"   # dropout | ae_serious | completed | censored
    event_week: int | None = None


def weibull_hazard(t: float, shape: float, scale: float) -> float:
    """Weibull instantaneous hazard h(t) = (shape/scale) * (t/scale)^(shape-1)."""
    if t <= 0:
        return 0.0
    return (shape / scale) * ((t / scale) ** (shape - 1))


def competing_risks_step(
    patient: PatientSurvivalState,
    current_week: int,
    cumulative_toxicity: float,
    efficacy_signal: float,
    rng: random.Random,
) -> PatientSurvivalState:
    """
    Apply one-week step of competing-risks hazard model.
    Toxicity increases dropout/SAE hazard; good efficacy decreases dropout.
    """
    if patient.event != "censored":
        return patient

    t = current_week - patient.entry_week + 1e-3

    # Covariate adjustments
    tox_mult = 1.0 + 3.0 * cumulative_toxicity
    efficacy_mult = max(0.2, 1.0 - 0.5 * efficacy_signal)  # better efficacy → less dropout

    h_dropout = weibull_hazard(t, patient.shape_dropout, patient.scale_dropout) * tox_mult * efficacy_mult
    h_ae = weibull_hazard(t, patient.shape_ae_serious, patient.scale_ae_serious) * tox_mult
    h_complete = weibull_hazard(t, patient.shape_completion, patient.scale_completion)

    total_h = h_dropout + h_ae + h_complete
    prob_event = 1 - math.exp(-total_h)

    if rng.random() < prob_event:
        # Determine which competing risk fired (cause-specific)
        r = rng.random() * total_h
        if r < h_dropout:
            patient.event = "dropout"
        elif r < h_dropout + h_ae:
            patient.event = "ae_serious"
        else:
            patient.event = "completed"
        patient.event_week = current_week

    return patient


def kaplan_meier(event_weeks: List[int], total_n: int) -> List[dict]:
    """Simple KM curve for a single risk."""
    sorted_weeks = sorted(set(event_weeks))
    at_risk = total_n
    survival = 1.0
    curve = []
    events_map = {}
    for w in event_weeks:
        events_map[w] = events_map.get(w, 0) + 1
    for w in sorted_weeks:
        d = events_map[w]
        survival *= (1 - d / at_risk) if at_risk > 0 else survival
        curve.append({"week": w, "survival": round(survival, 4), "at_risk": at_risk, "events": d})
        at_risk = max(0, at_risk - d)
    return curve
