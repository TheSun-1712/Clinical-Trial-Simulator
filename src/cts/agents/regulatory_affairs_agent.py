"""Regulatory Affairs Agent — milestone tracking, SAE reporting, FDA interactions."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict


@dataclass
class SAEReport:
    report_id: str
    patient_id: str
    ae_term: str
    grade: int
    week_occurred: int
    causality: str          # related | possibly_related | unrelated
    reporting_deadline: int  # 7 or 15 day window mapped to weeks
    filed: bool = False


@dataclass
class RegulatoryStatus:
    week: int
    milestones: Dict[str, bool]
    pending_saes: int
    overdue_saes: int
    amendment_count: int
    fda_sentiment: float
    fda_flag: str
    next_milestone: str
    recommendation: str
    sae_log: List[dict]


class RegulatoryAffairsAgent:
    """
    Tracks IND → Phase I → EOP2 → Phase III → NDA milestones.
    Manages 7-day (fatal/life-threatening) and 15-day SAE reporting windows.
    """
    MILESTONE_WEEKS = {
        "ind_filed": 0,
        "phase1_start": 4,
        "phase1_complete": 26,
        "eop2_meeting": 34,
        "phase3_start": 40,
        "phase3_complete": 92,
        "nda_filed": 100,
    }

    def __init__(self):
        self.sae_reports: List[SAEReport] = []
        self._report_counter = 0
        self.amendments: List[dict] = []
        self.history: List[dict] = []

    def analyze(self, state) -> RegulatoryStatus:
        # Auto-update milestones based on week
        milestones = getattr(state, "milestones", {})
        for ms, target_week in self.MILESTONE_WEEKS.items():
            if state.week >= target_week and not milestones.get(ms, False):
                milestones[ms] = True
        # Phase I complete depends on cohort
        if state.enrolled >= state.cohort_target and not milestones.get("phase1_complete"):
            milestones["phase1_complete"] = True

        # Log new SAEs from this week's AE events
        self._log_saes(state)

        # Check overdue reports (>2 weeks for fatal, >3 weeks for serious)
        pending = [r for r in self.sae_reports if not r.filed]
        overdue = [r for r in pending if state.week - r.week_occurred > r.reporting_deadline]

        # Auto-file if overdue
        for r in overdue:
            r.filed = True

        # Next milestone
        next_ms = next(
            (k for k, v in sorted(self.MILESTONE_WEEKS.items(), key=lambda x: x[1]) if not milestones.get(k)),
            "nda_approved"
        )
        weeks_to_next = max(0, self.MILESTONE_WEEKS.get(next_ms, 999) - state.week)

        # Recommendation
        if len(overdue) > 0:
            rec = f"🚨 {len(overdue)} overdue SAE report(s) — file immediately"
        elif state.fda_flag == "hold":
            rec = "⚠️ FDA clinical hold — file response within 30 days"
        elif state.fda_flag == "warning":
            rec = "📋 FDA warning — prepare protocol amendment and safety update"
        elif weeks_to_next <= 4:
            rec = f"📌 {next_ms.replace('_',' ').title()} due in {weeks_to_next}w — prepare submission"
        else:
            rec = f"✅ Regulatory compliant — next: {next_ms.replace('_',' ').title()} in {weeks_to_next}w"

        status = RegulatoryStatus(
            week=state.week,
            milestones=dict(milestones),
            pending_saes=len(pending),
            overdue_saes=len(overdue),
            amendment_count=len(self.amendments),
            fda_sentiment=state.fda_sentiment,
            fda_flag=state.fda_flag,
            next_milestone=next_ms,
            recommendation=rec,
            sae_log=[
                {"report_id": r.report_id, "term": r.ae_term, "grade": r.grade,
                 "week": r.week_occurred, "causality": r.causality, "filed": r.filed}
                for r in self.sae_reports[-15:]
            ],
        )
        self.history.append({"week": state.week, "pending": len(pending), "milestones_done": sum(milestones.values())})
        return status

    def _log_saes(self, state) -> None:
        """Extract SAEs from patient adverse events."""
        for p in getattr(state, "patient_states", []):
            for ae in getattr(p, "adverse_events", []):
                if ae.get("is_serious") and ae.get("week", -1) == state.week:
                    self._report_counter += 1
                    grade = ae.get("grade", 3)
                    causality = "possibly_related" if grade >= 3 else "unrelated"
                    deadline = 1 if grade >= 4 else 2  # in weeks (7-day / 15-day)
                    pid = getattr(p, "profile", None)
                    self.sae_reports.append(SAEReport(
                        report_id=f"SAE-{self._report_counter:04d}",
                        patient_id=pid.patient_id if pid else "UNKNOWN",
                        ae_term=ae.get("term", "Unknown"),
                        grade=grade,
                        week_occurred=state.week,
                        causality=causality,
                        reporting_deadline=deadline,
                    ))

    def log_amendment(self, reason: str, week: int) -> None:
        self.amendments.append({"week": week, "reason": reason, "version": len(self.amendments) + 1})
