"""Pharmacoeconomics Agent — QALY, ICER, cost-effectiveness analysis."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List


# Standard of care benchmarks (disease-specific)
SOC_BENCHMARKS = {
    "type2_diabetes": {"soc_efficacy": 0.40, "soc_cost_per_week": 85, "soc_qaly_weight": 0.72},
    "hypertension":   {"soc_efficacy": 0.45, "soc_cost_per_week": 60, "soc_qaly_weight": 0.75},
    "nsclc":          {"soc_efficacy": 0.20, "soc_cost_per_week": 1200, "soc_qaly_weight": 0.55},
}

WTP_THRESHOLD = 100_000   # Willingness-to-pay (USD/QALY) — common US threshold


@dataclass
class CEAReport:
    week: int
    total_trial_cost: float
    cost_per_patient: float
    drug_cost_per_week: float
    incremental_cost: float
    incremental_qaly: float
    icer: float             # Incremental cost-effectiveness ratio (USD/QALY)
    wtp_acceptable: bool
    nda_approval_probability: float
    cost_breakdown: dict
    recommendation: str


class PharmacoeconomicsAgent:
    """
    Computes ICER = ΔCost / ΔQALY vs. standard of care.
    Models trial cost build-up and forecasts NDA probability.
    """
    DRUG_COST_PER_UNIT = 450   # USD per patient-week
    SITE_COST_PER_WEEK = 12_000
    REGULATORY_COST = 2_500_000   # Fixed regulatory submission cost
    RECRUITMENT_COST_PER_PATIENT = 8_500

    def __init__(self):
        self.history: List[dict] = []

    def analyze(self, state) -> CEAReport:
        disease = str(getattr(state, "disease", "type2_diabetes")).split(".")[-1]
        soc = SOC_BENCHMARKS.get(disease, SOC_BENCHMARKS["type2_diabetes"])

        n_enrolled = max(1, state.enrolled)
        weeks = max(1, state.week)
        n_sites = len(getattr(state, "sites", [{"status": "active"}]))

        # Cost build-up
        drug_cost = state.active * self.DRUG_COST_PER_UNIT * weeks
        site_cost = n_sites * self.SITE_COST_PER_WEEK * weeks
        recruitment_cost = n_enrolled * self.RECRUITMENT_COST_PER_PATIENT
        overhead = (drug_cost + site_cost + recruitment_cost) * 0.20
        regulatory_cost = self.REGULATORY_COST
        total_cost = drug_cost + site_cost + recruitment_cost + overhead + regulatory_cost

        # QALY calculation
        # QoL weight improved by drug efficacy signal
        qaly_weight_trt = soc["soc_qaly_weight"] + 0.15 * state.biomarker_improvement
        qaly_weight_soc = soc["soc_qaly_weight"]
        years = weeks / 52
        delta_qaly = (qaly_weight_trt - qaly_weight_soc) * n_enrolled * years
        delta_cost = total_cost - (soc["soc_cost_per_week"] * weeks * n_enrolled)

        icer = delta_cost / max(0.001, delta_qaly)
        wtp_ok = icer <= WTP_THRESHOLD

        # NDA probability heuristic
        efficacy_ok = state.biomarker_improvement > soc["soc_efficacy"] * 1.15
        safety_ok = state.serious_adverse_events < state.enrolled * 0.10
        power_proxy = min(1.0, (n_enrolled / max(1, state.cohort_target)) * 0.9)
        nda_prob = round(
            0.40 * float(efficacy_ok) + 0.30 * float(safety_ok) + 0.30 * power_proxy, 3
        )

        if not wtp_ok and icer > WTP_THRESHOLD * 2:
            rec = f"🔴 ICER ${icer:,.0f}/QALY — exceeds WTP threshold. Renegotiate drug pricing"
        elif not wtp_ok:
            rec = f"🟡 ICER ${icer:,.0f}/QALY — borderline. Consider patient subgroup enrichment"
        elif nda_prob > 0.70:
            rec = f"🟢 ICER ${icer:,.0f}/QALY — cost-effective. NDA probability {nda_prob:.0%}"
        else:
            rec = f"🟡 ICER ${icer:,.0f}/QALY — acceptable. Strengthen efficacy data (NDA: {nda_prob:.0%})"

        report = CEAReport(
            week=state.week,
            total_trial_cost=round(total_cost),
            cost_per_patient=round(total_cost / n_enrolled),
            drug_cost_per_week=self.DRUG_COST_PER_UNIT,
            incremental_cost=round(delta_cost),
            incremental_qaly=round(delta_qaly, 3),
            icer=round(icer),
            wtp_acceptable=wtp_ok,
            nda_approval_probability=nda_prob,
            cost_breakdown={
                "drug": round(drug_cost),
                "site": round(site_cost),
                "recruitment": round(recruitment_cost),
                "regulatory": regulatory_cost,
                "overhead": round(overhead),
            },
            recommendation=rec,
        )
        self.history.append({
            "week": weeks, "total_cost": round(total_cost),
            "icer": round(icer), "nda_prob": nda_prob,
        })
        return report
