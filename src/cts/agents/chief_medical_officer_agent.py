"""Chief Medical Officer — aggregates all specialized agents into CRO briefing."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Any

from cts.agents.dsmb_agent import DSMBAgent
from cts.agents.biostatistician_agent import BiostatisticianAgent
from cts.agents.pharmacokineticist_agent import PharmacokineticistAgent
from cts.agents.patient_advocate_agent import PatientAdvocateAgent
from cts.agents.regulatory_affairs_agent import RegulatoryAffairsAgent
from cts.agents.pharmacoeconomics_agent import PharmacoeconomicsAgent


@dataclass
class CMOBriefing:
    week: int
    overall_status: str       # on_track | at_risk | critical | stopped
    urgency_level: int        # 0=low, 1=medium, 2=high, 3=critical
    headline: str
    agent_signals: dict
    top_priority_action: str
    full_briefing: str


class ChiefMedicalOfficerAgent:
    """
    Aggregates outputs from all specialized agents and produces a prioritised
    weekly CRO briefing with a recommended top-priority action.
    """
    def __init__(self):
        self.dsmb = DSMBAgent()
        self.biostat = BiostatisticianAgent()
        self.pk_agent = PharmacokineticistAgent()
        self.advocate = PatientAdvocateAgent()
        self.regulatory = RegulatoryAffairsAgent()
        self.economics = PharmacoeconomicsAgent()
        self.briefings: List[dict] = []

    def run(self, state) -> CMOBriefing:
        # Run all agents
        dsmb_dec = self.dsmb.review(state)
        stat_report = self.biostat.analyze(state)
        pk_rec = self.pk_agent.analyze(state)
        ret_plan = self.advocate.analyze(state)
        reg_status = self.regulatory.analyze(state)
        cea = self.economics.analyze(state)

        signals = {
            "DSMB": {
                "status": dsmb_dec.decision if dsmb_dec else "pending_review",
                "p_value": dsmb_dec.p_value if dsmb_dec else None,
                "conditional_power": dsmb_dec.conditional_power if dsmb_dec else None,
                "next_review": 8 - (state.week % 8),
            },
            "Biostatistician": {
                "power": stat_report.power,
                "p_value": stat_report.p_value,
                "effect_size": stat_report.effect_size,
                "recommendation": stat_report.recommendation,
            },
            "Pharmacokineticist": {
                "dose_recommendation": pk_rec.recommended_dose,
                "n_sub_therapeutic": pk_rec.n_sub_therapeutic,
                "n_toxic": pk_rec.n_toxic,
                "reasoning": pk_rec.reasoning,
            },
            "PatientAdvocate": {
                "high_risk_count": ret_plan.high_risk_count,
                "mean_dropout_risk": ret_plan.mean_dropout_risk,
                "adherence_rate": ret_plan.adherence_rate,
                "interventions": ret_plan.recommended_interventions,
            },
            "RegulatoryAffairs": {
                "next_milestone": reg_status.next_milestone,
                "pending_saes": reg_status.pending_saes,
                "overdue_saes": reg_status.overdue_saes,
                "recommendation": reg_status.recommendation,
                "milestones": reg_status.milestones,
            },
            "PharmacoEconomics": {
                "icer": cea.icer,
                "wtp_acceptable": cea.wtp_acceptable,
                "nda_probability": cea.nda_approval_probability,
                "total_cost": cea.total_trial_cost,
                "recommendation": cea.recommendation,
            },
        }

        # Determine overall status
        urgency = 0
        reasons = []

        if dsmb_dec and dsmb_dec.decision in ("stop_safety", "stop_efficacy", "stop_futility"):
            urgency = 3
            reasons.append(f"DSMB: {dsmb_dec.decision.upper()}")
        if reg_status.overdue_saes > 0:
            urgency = max(urgency, 2)
            reasons.append(f"{reg_status.overdue_saes} overdue SAE(s)")
        if pk_rec.n_toxic > 3:
            urgency = max(urgency, 2)
            reasons.append(f"{pk_rec.n_toxic} patients in toxic range")
        if stat_report.power < 0.50:
            urgency = max(urgency, 1)
            reasons.append(f"Statistical power {stat_report.power:.0%}")
        if ret_plan.mean_dropout_risk > 0.30:
            urgency = max(urgency, 1)
            reasons.append(f"High dropout risk {ret_plan.mean_dropout_risk:.0%}")

        status_map = {0: "on_track", 1: "at_risk", 2: "critical", 3: "stopped"}
        overall_status = status_map[urgency]

        # Top priority
        if urgency == 3:
            top_action = f"STOP TRIAL — {reasons[0]}"
        elif reg_status.overdue_saes > 0:
            top_action = "File overdue SAE report immediately"
        elif pk_rec.recommended_dose != pk_rec.current_dose:
            top_action = f"Adjust dose: {pk_rec.current_dose:.2f} → {pk_rec.recommended_dose:.2f} ({pk_rec.reasoning})"
        elif ret_plan.high_risk_count > 2:
            top_action = f"Deploy retention plan for {ret_plan.high_risk_count} at-risk patients"
        else:
            top_action = stat_report.recommendation

        headline = reasons[0] if reasons else f"Week {state.week}: Trial {overall_status.replace('_',' ').title()}"

        full_briefing = (
            f"=== CRO WEEKLY BRIEFING — Week {state.week} ===\n"
            f"Status: {overall_status.upper()} | Priority: {'🔴' if urgency==3 else '🟡' if urgency>0 else '🟢'}\n"
            f"Top Action: {top_action}\n\n"
            f"📊 Stats: p={stat_report.p_value:.4f}, power={stat_report.power:.0%}, d={stat_report.effect_size:.3f}\n"
            f"💊 PK: Dose={pk_rec.current_dose:.2f}, Tox-range={pk_rec.n_toxic}pts, Sub-thr={pk_rec.n_sub_therapeutic}pts\n"
            f"👥 Retention: {ret_plan.high_risk_count} high-risk, adherence={ret_plan.adherence_rate:.0%}\n"
            f"📋 Regulatory: {reg_status.recommendation}\n"
            f"💰 Economics: ICER=${cea.icer:,.0f}/QALY, NDA={cea.nda_approval_probability:.0%}\n"
        )

        briefing = CMOBriefing(
            week=state.week,
            overall_status=overall_status,
            urgency_level=urgency,
            headline=headline,
            agent_signals=signals,
            top_priority_action=top_action,
            full_briefing=full_briefing,
        )
        self.briefings.append({"week": state.week, "status": overall_status, "urgency": urgency})
        return briefing

    def latest_signals(self) -> dict:
        """Return latest agent outputs without running a new step."""
        return {
            "pk_history": self.pk_agent.pk_timeseries(20),
            "stat_history": self.biostat.latest_history(20),
            "dsmb_decisions": self.dsmb.all_decisions(),
            "briefing_history": self.briefings[-10:],
        }
