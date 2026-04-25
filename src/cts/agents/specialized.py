from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from cts.knowledge import EvidenceStore
from cts.patient.models import CohortState


@dataclass
class AgentOutput:
    agent: str
    recommendation: str
    confidence: float
    details: dict[str, Any]


class PatientSafetyAgent:
    def analyze(self, cohort: CohortState) -> AgentOutput:
        severe_events = []
        for p in cohort.patient_states:
            for ae in p.adverse_events:
                if int(ae.get("grade", 1)) >= 3:
                    severe_events.append({"patient_id": p.profile.patient_id, "ae": ae})
        
        confidence = 0.85
        if len(severe_events) > len(cohort.patient_states) * 0.1:
            rec = "immediate_hold_and_safety_review"
        elif severe_events:
            rec = "dose_reduction_recommended"
        else:
            rec = "continue_enrollment"
        
        return AgentOutput("PatientSafetyAgent", rec, confidence, {"severe_event_count": len(severe_events), "events": severe_events})


class EfficacyAgent:
    def analyze(self, cohort: CohortState) -> AgentOutput:
        active_patients = [p for p in cohort.patient_states if p.assigned_arm != "control"]
        if not active_patients:
            return AgentOutput("EfficacyAgent", "awaiting_data", 0.5, {})
            
        mean_response = sum(p.efficacy_response for p in active_patients) / len(active_patients)
        
        if mean_response > 0.6:
            rec = "strong_signal_maintain_or_accelerate"
        elif mean_response > 0.3:
            rec = "moderate_signal_consider_optimization"
        else:
            rec = "weak_signal_investigate_subgroups"
            
        return AgentOutput("EfficacyAgent", rec, 0.75, {"mean_active_response": mean_response})


class TrialOpsAgent:
    def analyze(self, cohort: CohortState) -> AgentOutput:
        if not cohort.patient_states:
            return AgentOutput("TrialOpsAgent", "no_patients", 0.5, {})
            
        mean_dropout = sum(p.dropout_risk for p in cohort.patient_states) / len(cohort.patient_states)
        adherence_issues = [p.profile.patient_id for p in cohort.patient_states if p.adherence < 0.8]
        
        if mean_dropout > 0.25 or adherence_issues:
            rec = "implement_retention_strategies"
        else:
            rec = "operations_stable"
            
        return AgentOutput("TrialOpsAgent", rec, 0.8, {"mean_dropout": mean_dropout, "low_adherence_count": len(adherence_issues)})


class RegulatoryAgent:
    def analyze(self, cohort: CohortState) -> AgentOutput:
        deviations = sum(len(p.protocol_deviations) for p in cohort.patient_states)
        serious_aes = sum(1 for p in cohort.patient_states for ae in p.adverse_events if ae.get("is_serious"))
        
        if serious_aes > 0 or deviations > 5:
            rec = "file_expedited_safety_report"
        else:
            rec = "compliant"
            
        return AgentOutput("RegulatoryAgent", rec, 0.9, {"deviations": deviations, "serious_aes": serious_aes})


class LiteratureEvidenceAgent:
    def __init__(self, store: EvidenceStore) -> None:
        self.store = store

    def analyze(self, disease: str, intervention: str) -> AgentOutput:
        records = self.store.retrieve(disease=disease, intervention=intervention)
        summary = f"Found {len(records)} relevant evidence records."
        return AgentOutput("LiteratureEvidenceAgent", "grounding_context", 0.7, {
            "evidence_count": len(records),
            "evidence_ids": [r.evidence_id for r in records],
            "top_summary": summary
        })


class DrugCompositionAgent:
    def propose(self, current: dict[str, float], cohort: CohortState, evidence: list[dict]) -> AgentOutput:
        # Simple heuristic: if efficacy is low, increase 'a' (efficacy component), if safety issues, decrease 'c' (toxic component)
        active_response = sum(p.efficacy_response for p in cohort.patient_states if p.assigned_arm != "control") / max(1, len(cohort.patient_states))
        safety_issues = sum(1 for p in cohort.patient_states for ae in p.adverse_events if int(ae.get("grade", 1)) >= 3)
        
        updated = dict(current)
        if active_response < 0.4:
            updated["a"] = updated.get("a", 0.0) + 0.05
        if safety_issues > 0:
            updated["c"] = max(0.0, updated.get("c", 0.0) - 0.05)
            
        total = sum(updated.values())
        if total > 0:
            updated = {k: v / total for k, v in updated.items()}
            
        return AgentOutput("DrugCompositionAgent", "optimize_composition", 0.7, {"proposed_composition": updated})


class HindsightReplayAgent:
    def analyze(self, episode_trace: dict[str, Any]) -> AgentOutput:
        # Analyze points of failure
        outcomes = episode_trace.get("final_outcomes", {})
        if outcomes.get("serious_adverse_event_rate", 0.0) > 0.15:
            rec = "safety_failure_detected_relabel_safer_actions"
        elif outcomes.get("efficacy_score", 0.0) < 0.4:
            rec = "efficacy_failure_detected_relabel_optimized_composition"
        else:
            rec = "successful_episode"
            
        return AgentOutput("HindsightReplayAgent", rec, 0.8, {"failure_modes": outcomes})


class ChiefTrialScientistAgent:
    def aggregate(self, outputs: list[AgentOutput]) -> dict[str, Any]:
        return {
            "research_only_notice": "Research simulation only. Not medical advice. No real PHI used.",
            "status": "active",
            "recommendations": {o.agent: o.recommendation for o in outputs},
            "detailed_signals": {o.agent: o.details for o in outputs},
            "overall_confidence": sum(o.confidence for o in outputs) / len(outputs) if outputs else 0.0
        }

