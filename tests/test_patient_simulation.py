import pytest
from cts.patient.generator import generate_synthetic_patients
from cts.environment.event_engine import EventEngine
from cts.config import EventRates

def test_patient_generation():
    patients = generate_synthetic_patients(5, seed=42)
    assert len(patients) == 5
    assert patients[0].profile.age > 0
    assert patients[0].status == "active"

def test_patient_transition():
    rates = EventRates(
        minor_reaction_base=0.1,
        major_reaction_base=0.01,
        fatal_reaction_base=0.0,
        efficacy_base=0.5,
        recruitment_base=2.0,
        dropout_base=0.05
    )
    engine = EventEngine(rates)
    patients = generate_synthetic_patients(1, seed=42)
    p = patients[0]
    
    # Mock composition
    composition = {"a": 0.5, "b": 0.5, "c": 0.0}
    
    updated = engine.transition_patient(p, composition)
    assert updated.efficacy_response >= 0.0
    assert updated.efficacy_response <= 1.0
    assert len(updated.lab_history) >= 1
