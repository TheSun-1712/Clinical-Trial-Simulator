from __future__ import annotations

import uuid
import random

from fastapi import FastAPI, Query
from pydantic import BaseModel

from cts.config import default_config
from cts.environment.models import Action, ActionType
from cts.environment.trial_env import TrialEnv
from eval.analytics import load_latest_benchmark_report
from eval.run_benchmark import run_benchmark


class StepRequest(BaseModel):
    action_type: ActionType
    magnitude: float = 0.0


class OpenEnvResetRequest(BaseModel):
    seed: int = 7


class OpenEnvStepRequest(BaseModel):
    session_id: str
    action_type: ActionType
    magnitude: float = 0.0
    composition: dict = {}


from fastapi.middleware.cors import CORSMiddleware

from cts.data.db import init_db
init_db()

app = FastAPI(title="OpenEnv API - Clinical Trial Simulator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
from fastapi import HTTPException
from cts.data.realworld_apis import fetch_clinical_trials, fetch_adverse_events, fetch_recent_literature
from cts.data.serp_scanner import fetch_medical_news

# Global session store
sessions: dict[str, TrialEnv] = {}

# Helper to retrieve environment by session id
def _session_env(session_id: str):
    env = sessions.get(session_id)
    if not env:
        raise HTTPException(status_code=404, detail="Session not found")
    return env



def _benchmark_report() -> dict:
    report = load_latest_benchmark_report()
    if report is None:
        run_benchmark(episodes=10, trained_checkpoint="artifacts/policy/latest.json", output_dir="artifacts/benchmark")
        report = load_latest_benchmark_report() or {}
    return report


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/openenv/metadata")
def openenv_metadata() -> dict:
    config = default_config()
    return {
        "name": "clinical-trial-simulator",
        "version": "0.1.0",
        "observation_type": "aggregate_summary",
        "action_schema": [
            {"action_type": action.value, "magnitude": "float"} for action in ActionType
        ],
        "stage": config.stage,
    }


@app.get("/analytics/efficiency-by-disease")
def efficiency_by_disease(policy: str = Query(default="trained")) -> dict:
    report = _benchmark_report()
    policy_metrics = report.get("disease_metrics", {}).get(policy, {})
    return {"policy": policy, "disease_metrics": policy_metrics}


@app.get("/analytics/efficiency-by-phase")
def efficiency_by_phase(policy: str = Query(default="trained")) -> dict:
    report = _benchmark_report()
    policy_metrics = report.get("phase_metrics", {}).get(policy, {})
    return {"policy": policy, "phase_metrics": policy_metrics}


@app.get("/analytics/timeline-by-run")
def timeline_by_run(
    policy: str = Query(default="trained"),
    disease: str | None = Query(default=None),
    stage: str | None = Query(default=None),
) -> dict:
    report = _benchmark_report()
    timeline = report.get("timeline", [])
    filtered = [
        row
        for row in timeline
        if row.get("policy") == policy
        and (disease is None or row.get("disease") == disease)
        and (stage is None or row.get("stage") == stage)
    ]
    return {"policy": policy, "disease": disease, "stage": stage, "timeline": filtered}


@app.get("/analytics/stage-config")
def stage_config() -> dict:
    config = default_config()
    return {
        "stage": config.stage,
        "stage1": config.stage1.model_dump(),
        "stage2": config.stage2.model_dump(),
        "stage3": config.stage3.model_dump(),
    }


class SelectDiseaseRequest(BaseModel):
    session_id: str
    disease: DiseaseType


@app.get("/simulation/disease-profiles")
def get_disease_profiles() -> dict:
    config = default_config()
    return {"profiles": {k.value: v for k, v in config.disease_profiles.items()}}


@app.post("/simulation/select-disease")
def select_disease(request: SelectDiseaseRequest) -> dict:
    if request.session_id not in sessions:
        return {"error": "unknown_session"}
    
    env = sessions[request.session_id]
    env.config = env.config.model_copy(update={"disease": request.disease})
    result = env.reset()
    return {"session_id": request.session_id, "observation": result.observation.__dict__}


@app.get("/simulation/patients/{session_id}")
def get_patients(session_id: str) -> dict:
    if session_id not in sessions:
        return {"error": "unknown_session"}
    env = sessions[session_id]
    patients = []
    for p in env.state.patient_states:
        patients.append({
            "id": p.profile.patient_id,
            "status": p.status,
            "age": p.profile.age,
            "sex": p.profile.sex,
            "stage": p.profile.disease_stage,
            "efficacy": p.efficacy_response,
            "ae_count": len(p.adverse_events),
            "dropout_risk": p.dropout_risk
        })
    return {"patients": patients}


@app.get("/simulation/evidence/{disease}")
def get_evidence(disease: str) -> dict:
    """Fetch real-world clinical trial data, literature, and adverse events for a disease."""
    # Use the unified realworld API helpers
    trials = fetch_clinical_trials(disease)
    literature = fetch_recent_literature(disease)
    adverse = fetch_adverse_events(disease)
    return {"trials": trials, "literature": literature, "adverse_events": adverse}

# New endpoint: drug composition (dynamic, no manual edit)
@app.get("/simulation/drug_composition/{session_id}")
def get_drug_composition(session_id: str):
    env = _session_env(session_id)
    state = env.state
    comp = getattr(state, "composition", {"a": 0.33, "b": 0.33, "c": 0.33})
    dose = getattr(state, "dose_level", 1.0)
    return {"composition": comp, "dose_level": dose}

# New endpoint: policy benchmarks
@app.get("/simulation/benchmarks/{session_id}")
def get_benchmarks(session_id: str):
    try:
        report = load_latest_benchmark_report()
        if report is None:
            report = {}
    except Exception:
        report = {}
    heuristic = report.get("heuristic", {}).get("total_reward", 0.0)
    trained = report.get("trained", {}).get("total_reward", 0.0)
    random = report.get("random", {}).get("total_reward", 0.0)
    return {"heuristic_reward": heuristic, "trained_reward": trained, "random_reward": random}

# New endpoint: agent analysis data for graphs
@app.get("/simulation/agent_analysis/{session_id}")
def get_agent_analysis(session_id: str):
    env = _session_env(session_id)
    history = getattr(env, "history", [])
    recent_rewards = [step.get("reward", 0.0) for step in history[-20:]]
    breakdown = [step.get("info", {}).get("reward_breakdown", {}) for step in history[-20:]]
    return {"recent_rewards": recent_rewards, "reward_breakdown": breakdown}

# New endpoint: world map news (already added earlier, ensure import)
@app.get("/simulation/news")
def get_news(limit: int = 20):
    news_items = fetch_medical_news(num_results=limit)
    return {"news": news_items}



class PolicyActionRequest(BaseModel):
    session_id: str
    checkpoint_path: str = "artifacts/policy/latest.json"


@app.post("/policy/action")
def get_policy_action(request: PolicyActionRequest) -> dict:
    from cts.policy_loader import checkpoint_exists, load_any_policy_checkpoint
    if request.session_id not in sessions:
        return {"error": "unknown_session"}
    
    env = sessions[request.session_id]
    from eval.baselines import heuristic_policy_action
    action = heuristic_policy_action(env.state)
        
    return {"action_type": action.type.value, "magnitude": action.magnitude}


@app.post("/simulation/batch")
def run_batch_simulation(seed: int = 7) -> dict:
    results = {}
    for disease in DiseaseType:
        config = default_config().model_copy(update={"disease": disease})
        env = TrialEnv(config)
        reset = env.reset(seed=seed)
        trajectory = [reset.observation.__dict__]
        state = reset.state
        for _ in range(20): # Run 20 weeks
            # Use heuristic policy for batch baseline
            from eval.baselines import heuristic_policy_action
            action = heuristic_policy_action(state)
            step_res = env.step(action)
            trajectory.append(step_res.observation.__dict__)
            state = step_res.state
            if step_res.terminated or step_res.truncated:
                break
        results[disease.value] = trajectory
    return {"results": results}


@app.post("/reset")
def reset(seed: int = 7) -> dict:
    result = env.reset(seed=seed)
    return {"observation": result.observation.__dict__, "terminated": result.terminated, "truncated": result.truncated}


@app.post("/step")
def step(request: StepRequest) -> dict:
    action = Action(type=request.action_type, magnitude=request.magnitude)
    result = env.step(action)
    return {
        "observation": result.observation.__dict__,
        "state": result.state.__dict__,
        "terminated": result.terminated,
        "truncated": result.truncated,
        "info": result.info,
    }


@app.post("/openenv/reset")
def openenv_reset(request: OpenEnvResetRequest) -> dict:
    session_id = str(uuid.uuid4())
    session_env = TrialEnv(default_config())
    result = session_env.reset(seed=request.seed)
    sessions[session_id] = session_env
    return {
        "session_id": session_id,
        "observation": result.observation.__dict__,
        "terminated": result.terminated,
        "truncated": result.truncated,
    }


@app.post("/openenv/step")
def openenv_step(request: OpenEnvStepRequest) -> dict:
    if request.session_id not in sessions:
        return {"error": "unknown_session"}

    action = Action(type=request.action_type, magnitude=request.magnitude, composition=request.composition)
    action_dict = {"type": action.type.value, "magnitude": action.magnitude}
    
    env = sessions[request.session_id]
    prev_state = env.state
    result = env.step(action)
    reward = result.info.get("reward", {}).get("total", 0.0)
    
    # Log to SQLite experience replay (safe serialization)
    from cts.data.db import log_transition
    def _safe_dict(obj):
        if hasattr(obj, '__dict__'):
            return {k: v for k, v in obj.__dict__.items() if isinstance(v, (int, float, str, bool, type(None)))}
        if isinstance(obj, dict):
            return {k: v for k, v in obj.items() if isinstance(v, (int, float, str, bool, type(None)))}
        return {}
    log_transition(
        request.session_id, result.state.week,
        _safe_dict(prev_state), action_dict, reward, _safe_dict(result.state), True
    )

    return {
        "session_id": request.session_id,
        "observation": result.observation.__dict__,
        "state": result.state.__dict__,
        "terminated": result.terminated,
        "truncated": result.truncated,
        "info": result.info,
        "reward": reward,
    }


# ─────────────────────────────────────────────────────────────────────────────
# New Comprehensive Endpoints
# ─────────────────────────────────────────────────────────────────────────────

def _get_state(session_id: str):
    env = sessions.get(session_id)
    if not env:
        return None, {"error": "session_not_found"}
    try:
        return env, None
    except RuntimeError:
        return None, {"error": "session_not_started"}


@app.get("/simulation/pkpd/{session_id}")
def get_pkpd(session_id: str) -> dict:
    env, err = _get_state(session_id)
    if err:
        return err
    s = env.state
    return {
        "c_central": s.pk_central_concentration,
        "c_peripheral": s.pk_peripheral_concentration,
        "auc": s.pk_auc,
        "cmax": s.pk_cmax,
        "cmin": s.pk_cmin,
        "t_half_weeks": s.pk_half_life,
        "therapeutic_range": s.pk_therapeutic_range,
        "dose_level": s.dose_level,
        "dose_recommendation": s.pk_dose_recommendation,
        "timeseries": s.pk_timeseries[-40:],
        "mec": 0.15,
        "mtc": 0.80,
    }


@app.get("/simulation/sites/{session_id}")
def get_sites(session_id: str) -> dict:
    env, err = _get_state(session_id)
    if err:
        return err
    return {
        "sites": env.state.sites,
        "total_enrolled": env.state.enrolled,
        "week": env.state.week,
    }


@app.get("/simulation/statistics/{session_id}")
def get_statistics(session_id: str) -> dict:
    env, err = _get_state(session_id)
    if err:
        return err
    s = env.state
    stat = s.agent_signals.get("Biostatistician", {})
    return {
        "power": s.current_power,
        "p_value": s.current_pvalue,
        "effect_size": s.current_effect_size,
        "ci_lower": s.ci_lower,
        "ci_upper": s.ci_upper,
        "alpha_spent": s.alpha_spent,
        "recommendation": s.stat_recommendation,
        "stat_history": env._cmo.biostat.latest_history(40),
        "subgroup_analysis": stat.get("subgroup_analysis", {}),
        "n_treatment": s.active,
        "n_control": s.control_arm_size,
    }


@app.get("/simulation/dsmb/{session_id}")
def get_dsmb(session_id: str) -> dict:
    env, err = _get_state(session_id)
    if err:
        return err
    s = env.state
    return {
        "latest_decision": s.dsmb_latest,
        "all_decisions": s.dsmb_decisions,
        "next_review_week": 8 - (s.week % 8) if s.week % 8 != 0 else 8,
        "ae_rate_treatment": s.serious_adverse_events / max(1, s.enrolled),
        "ae_rate_control": s.control_ae_rate,
        "week": s.week,
    }


@app.get("/simulation/supply/{session_id}")
def get_supply(session_id: str) -> dict:
    env, err = _get_state(session_id)
    if err:
        return err
    s = env.state
    snap = env._supply.snapshot(s.week)
    return {
        **snap,
        "active_patients": s.active,
        "stockout": s.supply_stockout,
        "week": s.week,
    }


@app.get("/simulation/milestones/{session_id}")
def get_milestones(session_id: str) -> dict:
    env, err = _get_state(session_id)
    if err:
        return err
    s = env.state
    reg = s.agent_signals.get("RegulatoryAffairs", {})
    return {
        "milestones": s.milestones,
        "next_milestone": s.regulatory_next_milestone,
        "recommendation": s.regulatory_recommendation,
        "sae_log": s.sae_log[-20:],
        "amendment_count": s.amendment_count,
        "fda_flag": s.fda_flag,
        "fda_sentiment": s.fda_sentiment,
        "pending_saes": reg.get("pending_saes", 0),
        "overdue_saes": reg.get("overdue_saes", 0),
    }


@app.get("/simulation/agents/{session_id}")
def get_agents(session_id: str) -> dict:
    env, err = _get_state(session_id)
    if err:
        return err
    s = env.state
    return {
        "cmo_briefing": s.cmo_briefing,
        "cmo_status": s.cmo_status,
        "cmo_urgency": s.cmo_urgency,
        "agent_signals": s.agent_signals,
        "top_action": s.agent_signals.get("top_action", ""),
        "week": s.week,
    }


@app.get("/simulation/economics/{session_id}")
def get_economics(session_id: str) -> dict:
    env, err = _get_state(session_id)
    if err:
        return err
    s = env.state
    econ = s.agent_signals.get("PharmacoEconomics", {})
    return {
        "total_trial_cost": s.total_trial_cost,
        "cost_per_patient": s.cost_per_patient,
        "icer": s.icer,
        "nda_probability": s.nda_probability,
        "incremental_qaly": s.incremental_qaly,
        "wtp_acceptable": econ.get("wtp_acceptable", True),
        "recommendation": s.economics_recommendation,
        "cost_history": env._cmo.economics.history[-30:],
        "week": s.week,
    }


@app.get("/simulation/endpoints/{session_id}")
def get_endpoints(session_id: str) -> dict:
    env, err = _get_state(session_id)
    if err:
        return err
    s = env.state
    return {
        "primary_endpoint": {
            "name": "Biomarker Improvement",
            "treatment_value": round(s.biomarker_improvement, 4),
            "control_value": round(s.control_efficacy, 4),
            "difference": round(s.biomarker_improvement - s.control_efficacy, 4),
        },
        "secondary_endpoints": s.secondary_endpoint_values,
        "disease_progression": s.disease_progression,
        "efficacy_signal": s.efficacy_signal,
        "treatment_n": s.active,
        "control_n": s.control_arm_size,
        "week": s.week,
    }

