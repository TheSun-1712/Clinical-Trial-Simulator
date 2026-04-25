from __future__ import annotations

import uuid

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


from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Clinical Trial Simulator API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
env = TrialEnv(default_config())
sessions: dict[str, TrialEnv] = {}


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

    action = Action(type=request.action_type, magnitude=request.magnitude)
    result = sessions[request.session_id].step(action)
    return {
        "session_id": request.session_id,
        "observation": result.observation.__dict__,
        "state": result.state.__dict__,
        "terminated": result.terminated,
        "truncated": result.truncated,
        "info": result.info,
    }
