"""
Statistical power analysis with O'Brien-Fleming alpha spending
and futility stopping rules for adaptive clinical trials.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Optional

from scipy import stats


@dataclass
class InterimAnalysis:
    interim_number: int       # k = 1, 2, … K
    total_interims: int       # K
    n_treatment: int
    n_control: int
    mean_treatment: float
    mean_control: float
    std_pooled: float
    alpha_total: float = 0.05

    # --- O'Brien-Fleming boundary ---
    def alpha_spent(self) -> float:
        """Cumulative alpha spent at interim k using O'Brien-Fleming spending function."""
        info_fraction = self.interim_number / self.total_interims
        z_alpha_half = stats.norm.ppf(1 - self.alpha_total / 2)
        boundary = z_alpha_half / math.sqrt(info_fraction)
        spent = 2 * (1 - stats.norm.cdf(boundary))
        return round(spent, 6)

    def obf_z_boundary(self) -> float:
        """Z-score boundary for this interim (O'Brien-Fleming)."""
        info_fraction = max(1e-6, self.interim_number / self.total_interims)
        z_alpha_half = stats.norm.ppf(1 - self.alpha_total / 2)
        return z_alpha_half / math.sqrt(info_fraction)

    def test_statistic(self) -> float:
        """Two-sample z-statistic for primary endpoint."""
        n1, n2 = max(1, self.n_treatment), max(1, self.n_control)
        se = self.std_pooled * math.sqrt(1 / n1 + 1 / n2)
        if se == 0:
            return 0.0
        return (self.mean_treatment - self.mean_control) / se

    def p_value(self) -> float:
        z = self.test_statistic()
        return float(2 * (1 - stats.norm.cdf(abs(z))))

    def effect_size(self) -> float:
        """Cohen's d."""
        if self.std_pooled == 0:
            return 0.0
        return (self.mean_treatment - self.mean_control) / self.std_pooled

    def confidence_interval(self, alpha: float = 0.05) -> tuple[float, float]:
        """95% CI for treatment effect."""
        n1, n2 = max(1, self.n_treatment), max(1, self.n_control)
        se = self.std_pooled * math.sqrt(1 / n1 + 1 / n2)
        z = stats.norm.ppf(1 - alpha / 2)
        diff = self.mean_treatment - self.mean_control
        return (diff - z * se, diff + z * se)

    def stop_for_efficacy(self) -> bool:
        return abs(self.test_statistic()) >= self.obf_z_boundary()

    def conditional_power(self, assumed_effect: Optional[float] = None) -> float:
        """
        Conditional power under the null (pessimistic) — if < 20%, recommend stopping for futility.
        """
        n1, n2 = max(1, self.n_treatment), max(1, self.n_control)
        se = self.std_pooled * math.sqrt(1 / n1 + 1 / n2)
        z_obs = self.test_statistic()
        info_fraction = self.interim_number / self.total_interims
        remaining = 1 - info_fraction
        if remaining <= 0 or se == 0:
            return float(abs(z_obs) >= stats.norm.ppf(0.975))
        delta = assumed_effect or (self.mean_treatment - self.mean_control)
        z_final = z_obs * math.sqrt(info_fraction) + delta * math.sqrt(remaining) / se
        return float(stats.norm.cdf(z_final - stats.norm.ppf(0.975)) + stats.norm.cdf(-z_final - stats.norm.ppf(0.975)))

    def stop_for_futility(self, cp_threshold: float = 0.20) -> bool:
        return self.conditional_power() < cp_threshold

    def full_report(self) -> dict:
        z = self.test_statistic()
        ci = self.confidence_interval()
        return {
            "interim": self.interim_number,
            "total_interims": self.total_interims,
            "n_treatment": self.n_treatment,
            "n_control": self.n_control,
            "z_statistic": round(z, 4),
            "z_boundary_obf": round(self.obf_z_boundary(), 4),
            "p_value": round(self.p_value(), 5),
            "effect_size_cohens_d": round(self.effect_size(), 4),
            "ci_95_lower": round(ci[0], 4),
            "ci_95_upper": round(ci[1], 4),
            "alpha_spent": self.alpha_spent(),
            "conditional_power": round(self.conditional_power(), 4),
            "stop_for_efficacy": self.stop_for_efficacy(),
            "stop_for_futility": self.stop_for_futility(),
        }


def required_sample_size(effect_size: float, alpha: float = 0.05, power: float = 0.80) -> int:
    """Classic two-sample t-test sample size per arm."""
    z_alpha = stats.norm.ppf(1 - alpha / 2)
    z_beta = stats.norm.ppf(power)
    if effect_size == 0:
        return 9999
    n = ((z_alpha + z_beta) / effect_size) ** 2
    return int(math.ceil(n))
