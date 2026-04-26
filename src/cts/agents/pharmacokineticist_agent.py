"""Pharmacokineticist agent — population PK analysis and dose optimisation."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

from cts.pk import TwoCompartmentPK, cyp_multiplier


@dataclass
class DoseRecommendation:
    week: int
    current_dose: float
    recommended_dose: float
    reasoning: str
    pk_summary: dict
    n_sub_therapeutic: int
    n_therapeutic: int
    n_toxic: int


class PharmacokineticistAgent:
    """
    Uses population PK simulation to identify patients outside therapeutic window
    and recommend dose adjustments.
    MEC (minimum effective concentration) = 0.15 mg/L
    MTC (maximum tolerated concentration) = 0.80 mg/L
    """
    MEC = 0.15   # sub-therapeutic below this
    MTC = 0.80   # toxic above this

    def __init__(self):
        self._pk_model = TwoCompartmentPK()
        self.history: List[dict] = []

    def analyze(self, state) -> DoseRecommendation:
        # Simulate PK at current dose
        sim = TwoCompartmentPK()
        sim.dose(state.dose_level * 100, cyp_genotype="normal")  # dose in mg
        for _ in range(4):   # steady-state approximation over 4 weeks
            sim.dose(state.dose_level * 100, "normal")
            sim.step()
        pk = sim.summary()

        # Classify patients by CYP genotype if available
        patients = getattr(state, "patient_states", [])
        n_sub = n_thr = n_tox = 0
        for p in patients:
            geno = p.profile.genotype.get("cyp2d6", "normal") if hasattr(p, "profile") else "normal"
            mult = cyp_multiplier(geno)
            c_individual = state.drug_concentration * mult
            if c_individual < self.MEC:
                n_sub += 1
            elif c_individual > self.MTC:
                n_tox += 1
            else:
                n_thr += 1

        # Dose recommendation
        c = state.drug_concentration
        rec_dose = state.dose_level
        if c < self.MEC and state.dose_level < 1.5:
            rec_dose = min(1.5, state.dose_level * 1.15)
            reasoning = f"Plasma conc {c:.3f} < MEC {self.MEC} — increase dose +15%"
        elif c > self.MTC and state.dose_level > 0.5:
            rec_dose = max(0.5, state.dose_level * 0.85)
            reasoning = f"Plasma conc {c:.3f} > MTC {self.MTC} — reduce dose -15%"
        elif n_tox > (len(patients) * 0.15) and len(patients) > 0:
            rec_dose = max(0.5, state.dose_level * 0.90)
            reasoning = f"{n_tox} patients above MTC — reduce dose -10%"
        elif n_sub > (len(patients) * 0.30) and len(patients) > 0:
            rec_dose = min(1.5, state.dose_level * 1.10)
            reasoning = f"{n_sub} patients below MEC — increase dose +10%"
        else:
            reasoning = f"Concentration {c:.3f} within therapeutic window [{self.MEC}–{self.MTC}]"

        result = DoseRecommendation(
            week=state.week,
            current_dose=round(state.dose_level, 3),
            recommended_dose=round(rec_dose, 3),
            reasoning=reasoning,
            pk_summary={**pk, "drug_concentration": round(c, 4), "mec": self.MEC, "mtc": self.MTC},
            n_sub_therapeutic=n_sub,
            n_therapeutic=n_thr,
            n_toxic=n_tox,
        )
        self.history.append({
            "week": state.week,
            "c_central": pk["c_central"],
            "auc": pk["auc"],
            "dose": rec_dose,
            "n_sub": n_sub, "n_thr": n_thr, "n_tox": n_tox,
        })
        return result

    def pk_timeseries(self, n: int = 30) -> list:
        return self.history[-n:]
