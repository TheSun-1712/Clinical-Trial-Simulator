from __future__ import annotations

import random

import pandas as pd
import plotly.express as px
import streamlit as st

from cts.config import default_config
from cts.environment.models import Action, ActionType
from cts.environment.trial_env import TrialEnv
from cts.policy import checkpoint_exists, load_policy_checkpoint
from cts.rewards.verifiers import reward_breakdown
from eval.baselines import heuristic_policy_action, random_policy_action
from eval.run_benchmark import run_benchmark


st.set_page_config(page_title="Clinical Trial Simulator", layout="wide")
st.title("Clinical Trial Simulator")

seed = st.sidebar.number_input("Seed", min_value=0, value=7, step=1)
policy_mode = st.sidebar.selectbox("Interactive policy", ["manual", "random", "heuristic", "trained"])
trained_checkpoint = st.sidebar.text_input("Trained checkpoint", value="artifacts/policy/latest.json")

interactive_tab, benchmark_tab = st.tabs(["Interactive", "Benchmark"])

with interactive_tab:
    st.subheader("Manual Episode Stepper")
    env = TrialEnv(default_config())
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
            action = Action(type=ActionType.RECRUIT if step < 3 else ActionType.NOOP, magnitude=2.0)
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
                "action": action.type.value,
                "components": rb["components"],
                "total": rb["total"],
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
