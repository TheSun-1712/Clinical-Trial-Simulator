"""Two-compartment pharmacokinetic model with patient-level variability."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List


@dataclass
class PKParameters:
    """Population PK parameters — can be individualised via covariates."""
    # Volumes (L)
    vc: float = 35.0    # Central compartment volume
    vp: float = 60.0    # Peripheral compartment volume
    # Rate constants (1/week)
    ka: float = 14.0    # Absorption rate (oral) — ~1/day converted to /week
    k10: float = 2.8    # Elimination from central (CL/Vc)
    k12: float = 1.4    # Distribution: central → peripheral
    k21: float = 0.7    # Distribution: peripheral → central
    # Bioavailability
    f: float = 0.85
    # Derived
    @property
    def cl(self) -> float:
        return self.k10 * self.vc
    @property
    def t_half(self) -> float:
        # Approximate terminal half-life
        return math.log(2) / self.k10


def cyp_multiplier(genotype: str) -> float:
    """CYP2D6/3A4 polymorphism effect on clearance."""
    return {"poor": 0.4, "intermediate": 0.7, "normal": 1.0, "ultra_rapid": 1.8}.get(genotype, 1.0)


@dataclass
class TwoCompartmentPK:
    """
    Numerical solver for 2-compartment PK using weekly Euler steps.
    State: (C1, C2) = central & peripheral concentrations (mg/L).
    """
    params: PKParameters = field(default_factory=PKParameters)
    c1: float = 0.0   # Central compartment concentration
    c2: float = 0.0   # Peripheral compartment concentration
    auc: float = 0.0  # Cumulative AUC (mg·week/L)
    cmax: float = 0.0
    cmin: float = float("inf")
    week: int = 0

    def dose(self, dose_mg: float, cyp_genotype: str = "normal") -> None:
        """Apply an oral dose (bolus into central after first-pass absorption)."""
        mult = cyp_multiplier(cyp_genotype)
        # Reduced clearance → higher AUC; implemented as F adjustment
        absorbed = dose_mg * self.params.f / (self.params.vc * mult)
        self.c1 += absorbed

    def step(self, dt: float = 1.0) -> dict:
        """Advance one time step (default 1 week). Returns PK summary."""
        p = self.params
        # Euler integration of 2-compartment ODEs
        dC1 = -(p.k10 + p.k12) * self.c1 + p.k21 * self.c2 * (p.vp / p.vc)
        dC2 = p.k12 * self.c1 * (p.vc / p.vp) - p.k21 * self.c2
        self.c1 = max(0.0, self.c1 + dC1 * dt)
        self.c2 = max(0.0, self.c2 + dC2 * dt)
        self.auc += self.c1 * dt
        self.cmax = max(self.cmax, self.c1)
        if self.c1 > 0:
            self.cmin = min(self.cmin, self.c1)
        self.week += 1
        return self.summary()

    def summary(self) -> dict:
        return {
            "c_central": round(self.c1, 4),
            "c_peripheral": round(self.c2, 4),
            "auc": round(self.auc, 3),
            "cmax": round(self.cmax, 4),
            "cmin": round(self.cmin, 4) if self.cmin < float("inf") else 0.0,
            "t_half_weeks": round(self.params.t_half, 2),
            "week": self.week,
        }

    def therapeutic_range(self, mec: float = 0.15, mtc: float = 0.80) -> str:
        """Classify current concentration vs MEC and MTC."""
        if self.c1 < mec:
            return "sub_therapeutic"
        if self.c1 > mtc:
            return "toxic"
        return "therapeutic"
