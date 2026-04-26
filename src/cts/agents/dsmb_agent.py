"""Data Safety Monitoring Board (DSMB) — autonomous safety and efficacy monitoring."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from cts.statistics.power_analysis import InterimAnalysis


@dataclass
class DSMBDecision:
    week: int
    decision: str           # continue | modify_protocol | stop_safety | stop_efficacy | stop_futility
    reasoning: str
    z_stat: float
    z_boundary: float
    p_value: float
    conditional_power: float
    ae_rate_treatment: float
    ae_rate_control: float


class DSMBAgent:
    """
    Independent data monitoring board. Reviews at pre-specified intervals.
    Uses O'Brien-Fleming boundaries for stopping.
    """
    REVIEW_INTERVAL = 8   # every 8 weeks
    N_PLANNED_INTERIMS = 3

    def __init__(self):
        self.decisions: List[DSMBDecision] = []
        self._interim_count = 0

    def should_review(self, week: int) -> bool:
        return week > 0 and week % self.REVIEW_INTERVAL == 0

    def review(self, state) -> DSMBDecision | None:
        """Full DSMB review. Returns a DSMBDecision or None if not yet due."""
        if not self.should_review(state.week):
            return None

        self._interim_count += 1
        n_trt = max(1, state.active)
        n_ctrl = max(1, state.control_arm_size)

        # Primary endpoint difference (biomarker improvement vs control)
        mean_trt = state.biomarker_improvement
        mean_ctrl = getattr(state, "control_efficacy", 0.25)
        std_pooled = 0.25  # assumed pooled SD

        analysis = InterimAnalysis(
            interim_number=self._interim_count,
            total_interims=self.N_PLANNED_INTERIMS,
            n_treatment=n_trt, n_control=n_ctrl,
            mean_treatment=mean_trt, mean_control=mean_ctrl,
            std_pooled=std_pooled,
        )
        report = analysis.full_report()

        ae_rate_trt = state.serious_adverse_events / max(1, state.enrolled)
        ae_rate_ctrl = getattr(state, "control_ae_rate", 0.02)

        # Determine decision
        if ae_rate_trt > 0.20 or state.fatal_reactions > 0:
            decision = "stop_safety"
            reasoning = f"AE rate {ae_rate_trt:.1%} exceeds 20% threshold or fatal reaction detected"
        elif report["stop_for_efficacy"]:
            decision = "stop_efficacy"
            reasoning = f"|Z|={report['z_statistic']:.2f} crossed O'Brien-Fleming boundary {report['z_boundary_obf']:.2f}"
        elif report["stop_for_futility"]:
            decision = "stop_futility"
            reasoning = f"Conditional power {report['conditional_power']:.1%} < 20% futility threshold"
        else:
            decision = "continue"
            reasoning = (
                f"Interim {self._interim_count}/{self.N_PLANNED_INTERIMS}: "
                f"Z={report['z_statistic']:.2f} (boundary={report['z_boundary_obf']:.2f}), "
                f"p={report['p_value']:.4f}, CP={report['conditional_power']:.1%}"
            )

        d = DSMBDecision(
            week=state.week,
            decision=decision,
            reasoning=reasoning,
            z_stat=report["z_statistic"],
            z_boundary=report["z_boundary_obf"],
            p_value=report["p_value"],
            conditional_power=report["conditional_power"],
            ae_rate_treatment=ae_rate_trt,
            ae_rate_control=ae_rate_ctrl,
        )
        self.decisions.append(d)
        return d

    def latest(self) -> dict | None:
        if not self.decisions:
            return None
        d = self.decisions[-1]
        return {
            "week": d.week, "decision": d.decision, "reasoning": d.reasoning,
            "z_stat": d.z_stat, "z_boundary": d.z_boundary, "p_value": d.p_value,
            "conditional_power": d.conditional_power,
            "ae_rate_treatment": d.ae_rate_treatment, "ae_rate_control": d.ae_rate_control,
        }

    def all_decisions(self) -> list:
        return [
            {"week": d.week, "decision": d.decision, "reasoning": d.reasoning,
             "p_value": d.p_value, "conditional_power": d.conditional_power}
            for d in self.decisions
        ]
