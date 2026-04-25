from __future__ import annotations

import random

from cts.environment.models import DiseaseType
from cts.patient.models import PatientProfile, PatientTrialState


def generate_synthetic_patients(count: int, seed: int = 17, disease: DiseaseType = DiseaseType.TYPE2_DIABETES) -> list[PatientTrialState]:
    rng = random.Random(seed)
    states: list[PatientTrialState] = []
    for idx in range(count):
        age = rng.randint(21, 80)
        sex = "female" if rng.random() < 0.5 else "male"
        profile = PatientProfile(
            patient_id=f"syn-{seed}-{idx}",
            age=age,
            sex=sex,
            disease=disease,
            disease_stage=rng.choice(["mild", "moderate", "severe"]),
            comorbidities=[c for c in ["hypertension", "ckd", "obesity"] if rng.random() < 0.25],
            baseline_labs={"alt": rng.uniform(10.0, 45.0), "ast": rng.uniform(10.0, 45.0)},
            vitals={"sbp": rng.uniform(95.0, 160.0), "dbp": rng.uniform(60.0, 100.0), "hr": rng.uniform(55.0, 105.0)},
            concomitant_medications=[m for m in ["metformin", "ace_inhibitor", "statin"] if rng.random() < 0.3],
            biomarkers={"marker_a": rng.uniform(0.0, 1.0), "marker_b": rng.uniform(0.0, 1.0)},
            genotype={"cyp2d6": rng.choice(["normal", "poor", "rapid"]), "brca1": "negative"},
            inclusion_exclusion_flags={"eligible": True, "requires_manual_review": False},
        )
        states.append(PatientTrialState(
            profile=profile,
            assigned_arm=rng.choice(["control", "active_a", "active_b"]),
            lab_history=[profile.baseline_labs],
            vitals_history=[profile.vitals]
        ))
    return states

