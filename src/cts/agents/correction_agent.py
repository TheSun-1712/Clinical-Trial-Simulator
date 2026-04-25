from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from cts.environment.models import Action, ActionType, TrialState


@dataclass(frozen=True)
class CorrectionRecommendation:
    action: str
    reason: str
    confidence: float
    rule_id: str


def _clamp_confidence(value: float) -> float:
    return max(0.0, min(1.0, value))


def _build_recommendation(action: ActionType, reason: str, confidence: float, rule_id: str) -> CorrectionRecommendation:
    return CorrectionRecommendation(
        action=action.value,
        reason=reason,
        confidence=_clamp_confidence(confidence),
        rule_id=rule_id,
    )


def recommend_corrections(state: TrialState, action: Action, next_state: TrialState) -> dict:
    recommendations: list[CorrectionRecommendation] = []

    ae_rate = next_state.adverse_events / max(next_state.enrolled, 1)
    severe_rate = next_state.serious_adverse_events / max(next_state.enrolled, 1)
    efficacy_gap = max(0.0, 0.55 - next_state.efficacy_signal)

    if next_state.fda_flag == "hold" or severe_rate > 0.03:
        recommendations.append(
            _build_recommendation(
                ActionType.HOLD_ENROLLMENT,
                "Safety signal is elevated and enrollment should be paused until the review clears.",
                0.96 if next_state.fda_flag == "hold" else 0.82,
                "SAFETY_HOLD",
            )
        )
        recommendations.append(
            _build_recommendation(
                ActionType.FILE_INTERIM_REPORT,
                "Escalate the safety review with an interim filing before additional recruitment.",
                0.88 if next_state.fda_flag == "hold" else 0.74,
                "FILE_INTERIM_ON_SAFETY",
            )
        )

    if next_state.fda_flag == "warning" and next_state.compliance_incidents > 0:
        recommendations.append(
            _build_recommendation(
                ActionType.FILE_INTERIM_REPORT,
                "FDA warning and compliance incidents both point to an interim report.",
                0.78,
                "FDA_WARNING_REPORT",
            )
        )

    if efficacy_gap > 0.08 and next_state.fda_flag != "hold":
        if action.type == ActionType.NOOP:
            recommendations.append(
                _build_recommendation(
                    ActionType.ADJUST_DOSE,
                    "Observed efficacy is lagging, so dose adjustment should be considered.",
                    0.71,
                    "LOW_EFFICACY_DOSE",
                )
            )
        recommendations.append(
            _build_recommendation(
                ActionType.RECRUIT,
                "Efficacy is below target and the phase can still absorb more recruitment.",
                0.62,
                "LOW_EFFICACY_RECRUIT",
            )
        )

    if ae_rate > 0.08 and next_state.fda_flag == "monitoring":
        recommendations.append(
            _build_recommendation(
                ActionType.HOLD_ENROLLMENT,
                "Adverse-event rate is drifting up even though the reviewer has not escalated yet.",
                0.67,
                "AE_TREND_HOLD",
            )
        )

    if not recommendations and next_state.composite_efficiency > 0.75:
        recommendations.append(
            _build_recommendation(
                ActionType.RECRUIT,
                "No corrective action is required; continue with the current recruitment strategy.",
                0.41,
                "STABLE_CONTINUE",
            )
        )

    payload = {
        "recommendations": [recommendation.__dict__ for recommendation in recommendations],
        "primary_rule_id": recommendations[0].rule_id if recommendations else None,
        "trigger_count": len(recommendations),
    }
    return payload


def recommendation_rule_ids(payload: dict) -> Iterable[str]:
    for recommendation in payload.get("recommendations", []):
        rule_id = recommendation.get("rule_id")
        if isinstance(rule_id, str):
            yield rule_id
