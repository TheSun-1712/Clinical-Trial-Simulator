from __future__ import annotations

import uuid

from fastapi import FastAPI
from pydantic import BaseModel

from cts.config import default_config
from cts.environment.models import Action, ActionType
from cts.environment.trial_env import TrialEnv


class StepRequest(BaseModel):
    action_type: ActionType
    magnitude: float = 0.0


class OpenEnvResetRequest(BaseModel):
    seed: int = 7


class OpenEnvStepRequest(BaseModel):
    session_id: str
    action_type: ActionType
    magnitude: float = 0.0


app = FastAPI(title="Clinical Trial Simulator API")
env = TrialEnv(default_config())
sessions: dict[str, TrialEnv] = {}


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
