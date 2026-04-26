"""Biostatistician agent — live statistical analysis of trial endpoints."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

from cts.statistics.power_analysis import InterimAnalysis, required_sample_size


@dataclass
class StatisticalReport:
    week: int
    power: float
    p_value: float
    effect_size: float
    ci_lower: float
    ci_upper: float
    alpha_spent: float
    required_n_per_arm: int
    current_n_treatment: int
    current_n_control: int
    recommendation: str
    subgroup_analysis: dict


class BiostatisticianAgent:
    """
    Runs per-step statistical analysis including:
    - Primary endpoint t-test
    - Power calculation
    - Subgroup forest plot data (age, sex, CYP genotype)
    - Multiple comparison correction
    """

    def __init__(self, n_interims: int = 3):
        self.n_interims = n_interims
        self._interim_count = 0
        self.history: List[dict] = []

    def analyze(self, state) -> StatisticalReport:
        self._interim_count = min(self.n_interims, 1 + state.week // 8)

        n_trt = max(2, state.active)
        n_ctrl = max(2, state.control_arm_size)

        mean_trt = float(state.biomarker_improvement)
        mean_ctrl = float(getattr(state, "control_efficacy", 0.25))
        std_pooled = 0.25

        analysis = InterimAnalysis(
            interim_number=self._interim_count,
            total_interims=self.n_interims,
            n_treatment=n_trt, n_control=n_ctrl,
            mean_treatment=mean_trt, mean_control=mean_ctrl,
            std_pooled=std_pooled,
        )
        report = analysis.full_report()

        # Dynamic power based on current N
        import math
        from scipy import stats
        z_alpha = stats.norm.ppf(0.975)
        se = std_pooled * math.sqrt(1 / n_trt + 1 / n_ctrl)
        ncp = (mean_trt - mean_ctrl) / se if se > 0 else 0
        power = float(1 - stats.norm.cdf(z_alpha - ncp) + stats.norm.cdf(-z_alpha - ncp))
        power = max(0.0, min(1.0, power))

        req_n = required_sample_size(
            effect_size=abs(mean_trt - mean_ctrl) / std_pooled if std_pooled > 0 else 0.5
        )

        # Subgroup analysis (simulated — uses state patient_states if available)
        subgroups = self._subgroup_analysis(state)

        if report["stop_for_efficacy"]:
            rec = "✅ Cross efficacy boundary — recommend stopping for success"
        elif report["stop_for_futility"]:
            rec = "⚠️ Low conditional power — consider stopping for futility"
        elif power < 0.60:
            rec = f"📊 Power {power:.1%} — enrich sample size (need {req_n}/arm)"
        elif report["p_value"] < 0.05:
            rec = f"📈 p={report['p_value']:.4f} — significant trend emerging"
        else:
            rec = f"🔬 p={report['p_value']:.4f} — continue per protocol"

        result = StatisticalReport(
            week=state.week,
            power=round(power, 4),
            p_value=report["p_value"],
            effect_size=report["effect_size_cohens_d"],
            ci_lower=report["ci_95_lower"],
            ci_upper=report["ci_95_upper"],
            alpha_spent=report["alpha_spent"],
            required_n_per_arm=req_n,
            current_n_treatment=n_trt,
            current_n_control=n_ctrl,
            recommendation=rec,
            subgroup_analysis=subgroups,
        )
        self.history.append({
            "week": state.week, "power": power,
            "p_value": report["p_value"], "effect_size": report["effect_size_cohens_d"],
        })
        return result

    def _subgroup_analysis(self, state) -> dict:
        """Generate subgroup effect estimates from patient_states."""
        patients = getattr(state, "patient_states", [])
        if not patients:
            return {}

        def mean_efficacy(plist):
            vals = [p.efficacy_response for p in plist if hasattr(p, "efficacy_response")]
            return round(sum(vals) / len(vals), 4) if vals else 0.0

        over_65 = [p for p in patients if hasattr(p, "profile") and p.profile.age >= 65]
        under_65 = [p for p in patients if hasattr(p, "profile") and p.profile.age < 65]
        male = [p for p in patients if hasattr(p, "profile") and p.profile.sex == "Male"]
        female = [p for p in patients if hasattr(p, "profile") and p.profile.sex == "Female"]
        poor_cyp = [p for p in patients if hasattr(p, "profile") and p.profile.genotype.get("cyp2d6") == "poor"]
        normal_cyp = [p for p in patients if hasattr(p, "profile") and p.profile.genotype.get("cyp2d6") == "normal"]

        return {
            "age_over65": {"n": len(over_65), "mean_efficacy": mean_efficacy(over_65)},
            "age_under65": {"n": len(under_65), "mean_efficacy": mean_efficacy(under_65)},
            "male": {"n": len(male), "mean_efficacy": mean_efficacy(male)},
            "female": {"n": len(female), "mean_efficacy": mean_efficacy(female)},
            "cyp_poor": {"n": len(poor_cyp), "mean_efficacy": mean_efficacy(poor_cyp)},
            "cyp_normal": {"n": len(normal_cyp), "mean_efficacy": mean_efficacy(normal_cyp)},
        }

    def latest_history(self, n: int = 20) -> list:
        return self.history[-n:]
