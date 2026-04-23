from __future__ import annotations

import random

import pandas as pd
import plotly.express as px
import streamlit as st

from cts.config import default_config
from cts.environment.models import Action, ActionType, DiseaseType
from cts.environment.trial_env import TrialEnv
from cts.policy import checkpoint_exists, load_policy_checkpoint
from cts.rewards.verifiers import reward_breakdown
from eval.baselines import heuristic_policy_action, random_policy_action
from eval.run_benchmark import run_benchmark


st.set_page_config(page_title="Clinical Trial Simulator", layout="wide")
st.title("Clinical Trial Simulator")
st.caption("Research simulation only. Not medical advice and not for clinical decision-making.")

seed = st.sidebar.number_input("Seed", min_value=0, value=7, step=1)
policy_mode = st.sidebar.selectbox("Interactive policy", ["manual", "random", "heuristic", "trained"])
trained_checkpoint = st.sidebar.text_input("Trained checkpoint", value="artifacts/policy/latest.json")
disease = st.sidebar.selectbox("Disease", [d.value for d in DiseaseType], index=0)
manual_a = st.sidebar.slider("Composition A", min_value=0.0, max_value=1.0, value=0.34, step=0.01)
manual_b = st.sidebar.slider("Composition B", min_value=0.0, max_value=1.0, value=0.33, step=0.01)
manual_c = st.sidebar.slider("Composition C", min_value=0.0, max_value=1.0, value=0.33, step=0.01)

raw_total = max(1e-9, manual_a + manual_b + manual_c)
manual_composition = {"a": manual_a / raw_total, "b": manual_b / raw_total, "c": manual_c / raw_total}

interactive_tab, benchmark_tab = st.tabs(["Interactive", "Benchmark"])

with interactive_tab:
    st.subheader("Disease-Aware Episode Stepper")
    config = default_config().model_copy(update={"disease": DiseaseType(disease), "initial_composition": manual_composition})
    env = TrialEnv(config)
    reset = env.reset(seed=int(seed))
    state = reset.state
    trained_policy = None
    if policy_mode == "trained":
        if checkpoint_exists(trained_checkpoint):
            trained_policy = load_policy_checkpoint(trained_checkpoint)
            st.caption(f"Loaded checkpoint: {trained_checkpoint}")
        else:
            st.warning("Checkpoint not found. Falling back to heuristic policy in interactive tab.")

    for step in range(8):
        if policy_mode == "manual":
            if step == 0:
                action = Action(type=ActionType.UPDATE_COMPOSITION, composition=manual_composition)
            elif step < 4:
                action = Action(type=ActionType.RECRUIT, magnitude=2.0)
            else:
                action = Action(type=ActionType.ADJUST_DOSE, magnitude=0.1)
        elif policy_mode == "random":
            action = random_policy_action(int(seed) + step)
        elif policy_mode == "heuristic":
            action = heuristic_policy_action(state)
        else:
            if trained_policy is None:
                action = heuristic_policy_action(state)
            else:
                action = trained_policy.select_action(state, env.config, rng=random.Random(int(seed) * 1000 + step), stochastic=False)

        result = env.step(action)
        rb = reward_breakdown(env.config.reward_weights, state, action, result.state)
        state = result.state

        st.write(
            {
                "week": state.week,
                "disease": state.disease.value,
                "action": action.type.value,
                "composition": state.composition,
                "components": rb["components"],
                "total": rb["total"],
                "reactions": {
                    "minor": state.minor_reactions,
                    "major": state.major_reactions,
                    "fatal": state.fatal_reactions,
                },
                "biomarker_improvement": state.biomarker_improvement,
                "fda": {"sentiment": state.fda_sentiment, "flag": state.fda_flag},
            }
        )
        if result.terminated or result.truncated:
            break

with benchmark_tab:
    st.subheader("Policy Comparison")
    rows = run_benchmark(episodes=10, trained_checkpoint=trained_checkpoint)
    frame = pd.DataFrame([
        {"policy": row.name, "source": row.source, **row.metrics} for row in rows
    ])
    st.dataframe(frame, use_container_width=True)

    radar = frame.melt(id_vars=["policy"], value_vars=["efficacy", "safety", "compliance", "cost", "progress"])
    fig = px.line_polar(radar, r="value", theta="variable", color="policy", line_close=True)
    st.plotly_chart(fig, use_container_width=True)
