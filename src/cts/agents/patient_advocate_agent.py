"""Patient Advocate Agent — dropout risk stratification and retention planning."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass
class RetentionPlan:
    week: int
    high_risk_count: int
    mean_dropout_risk: float
    adherence_rate: float
    recommended_interventions: List[str]
    estimated_retention_gain: float
    at_risk_patients: List[dict]


class PatientAdvocateAgent:
    """
    Identifies patients at high dropout risk and proposes targeted retention strategies.
    """
    HIGH_RISK_THRESHOLD = 0.35
    CRITICAL_RISK_THRESHOLD = 0.60

    INTERVENTIONS = {
        "digital_checkin":    ("📱 Digital symptom diary + weekly check-in call", 0.05),
        "transport_assist":   ("🚗 Transport reimbursement for clinic visits", 0.04),
        "visit_compress":     ("🗓 Compress remaining visits into fewer trips", 0.06),
        "adherence_coaching": ("🎓 Medication adherence coaching session", 0.07),
        "financial_support":  ("💰 Trial participation stipend increase", 0.03),
        "peer_support":       ("👥 Patient peer-support group enrollment", 0.04),
        "caregiver_engage":   ("👨‍👩‍👧 Caregiver engagement program", 0.04),
    }

    def __init__(self):
        self.history: List[dict] = []

    def analyze(self, state) -> RetentionPlan:
        patients = getattr(state, "patient_states", [])
        active = [p for p in patients if getattr(p, "status", "active") == "active"]

        if not active:
            return RetentionPlan(
                week=state.week, high_risk_count=0, mean_dropout_risk=0.0,
                adherence_rate=1.0, recommended_interventions=[],
                estimated_retention_gain=0.0, at_risk_patients=[],
            )

        risks = [getattr(p, "dropout_risk", 0.0) for p in active]
        adherences = [getattr(p, "adherence", 1.0) for p in active]
        mean_risk = sum(risks) / len(risks)
        adherence_rate = sum(adherences) / len(adherences)

        high_risk = [p for p, r in zip(active, risks) if r >= self.HIGH_RISK_THRESHOLD]
        critical_risk = [p for p, r in zip(active, risks) if r >= self.CRITICAL_RISK_THRESHOLD]

        # Select interventions based on observed patterns
        interventions = []
        total_gain = 0.0
        n = len(active)

        if adherence_rate < 0.80:
            name, gain = self.INTERVENTIONS["adherence_coaching"]
            interventions.append(name); total_gain += gain
        if len(critical_risk) > 0:
            name, gain = self.INTERVENTIONS["digital_checkin"]
            interventions.append(name); total_gain += gain
        if len(high_risk) > n * 0.20:
            name, gain = self.INTERVENTIONS["visit_compress"]
            interventions.append(name); total_gain += gain
        if mean_risk > 0.25:
            name, gain = self.INTERVENTIONS["financial_support"]
            interventions.append(name); total_gain += gain
        if state.week > 20:
            name, gain = self.INTERVENTIONS["peer_support"]
            interventions.append(name); total_gain += gain

        at_risk_list = [
            {
                "patient_id": getattr(p, "profile", None) and p.profile.patient_id or f"P{i}",
                "dropout_risk": round(getattr(p, "dropout_risk", 0), 3),
                "adherence": round(getattr(p, "adherence", 1.0), 3),
                "ae_count": len(getattr(p, "adverse_events", [])),
            }
            for i, (p, r) in enumerate(zip(active, risks))
            if r >= self.HIGH_RISK_THRESHOLD
        ]

        plan = RetentionPlan(
            week=state.week,
            high_risk_count=len(high_risk),
            mean_dropout_risk=round(mean_risk, 4),
            adherence_rate=round(adherence_rate, 4),
            recommended_interventions=interventions,
            estimated_retention_gain=round(min(0.25, total_gain), 4),
            at_risk_patients=at_risk_list[:10],  # top 10
        )
        self.history.append({"week": state.week, "high_risk": len(high_risk), "mean_risk": mean_risk})
        return plan
