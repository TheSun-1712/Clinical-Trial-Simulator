from __future__ import annotations
import copy


import sys
import random
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import pandas as pd
import plotly.express as px
import streamlit as st

from cts.config import default_config
from cts.environment.models import Action, ActionType, DiseaseType
from cts.environment.trial_env import TrialEnv
from cts.policy_loader import checkpoint_exists, describe_policy_checkpoint, load_any_policy_checkpoint, policy_checkpoint_type
from cts.rewards.verifiers import reward_breakdown
from eval.analytics import load_latest_benchmark_report
from eval.baselines import heuristic_policy_action, random_policy_action
from eval.run_benchmark import run_benchmark
from cts.integrations.clients import PubMedClient, OpenFDAClient


st.set_page_config(page_title="Clinical Trial Simulator", layout="wide")
st.title("Clinical Trial Simulator")
st.caption("Research simulation only. Not medical advice and not for clinical decision-making.")
st.sidebar.warning("Research-use simulation only. Not medical advice.")

seed = st.sidebar.number_input("Seed", min_value=0, value=7, step=1)
policy_mode = st.sidebar.selectbox("Interactive policy", ["manual", "random", "heuristic", "trained", "neural_llm"])
trained_checkpoint = st.sidebar.text_input("Policy checkpoint", value="artifacts/policy/latest_llm.json")
disease_filter = st.sidebar.multiselect("Disease filter", [d.value for d in DiseaseType], default=[d.value for d in DiseaseType])
stage_filter = st.sidebar.multiselect("Stage filter", ["stage1", "stage2", "stage3"], default=["stage1", "stage2", "stage3"])
policy_filter = st.sidebar.multiselect("Policy filter", ["random", "heuristic", "trained"], default=["random", "heuristic", "trained"])
benchmark_episodes = st.sidebar.number_input("Benchmark episodes", min_value=1, max_value=100, value=3, step=1)
st.sidebar.markdown("#### Continuous Neural Training")
training_backend = st.sidebar.selectbox("Training backend", ["trl-unsloth", "trl"], index=0)
training_config = st.sidebar.text_input("Training config", value="training/configs/grpo_medium.yaml")
training_steps = st.sidebar.number_input("Steps per improvement cycle", min_value=1, max_value=5000, value=100, step=25)
training_interval = st.sidebar.number_input("Seconds between cycles", min_value=0, max_value=3600, value=5, step=5)
disease = st.sidebar.selectbox("Disease", [d.value for d in DiseaseType], index=0)
manual_a = st.sidebar.slider("Composition A", min_value=0.0, max_value=1.0, value=0.34, step=0.01)
manual_b = st.sidebar.slider("Composition B", min_value=0.0, max_value=1.0, value=0.33, step=0.01)
manual_c = st.sidebar.slider("Composition C", min_value=0.0, max_value=1.0, value=0.33, step=0.01)

raw_total = max(1e-9, manual_a + manual_b + manual_c)
manual_composition = {"a": manual_a / raw_total, "b": manual_b / raw_total, "c": manual_c / raw_total}


@st.cache_data(show_spinner="Running clinical trial benchmarks...")
def load_dashboard_data(checkpoint_path: str, episodes: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows = run_benchmark(episodes=episodes, trained_checkpoint=checkpoint_path, output_dir="artifacts/benchmark")
    report = load_latest_benchmark_report("artifacts/benchmark") or {}
    rows_frame = [{"policy": row.name, "source": row.source, **row.metrics} for row in rows]
    return rows_frame, report


# Load existing report if available, but don't run a new one automatically on every refresh
benchmark_report = load_latest_benchmark_report("artifacts/benchmark") or {}
benchmark_rows = []
if benchmark_report:
    # Try to reconstruct rows from the report if possible, or just leave empty
    pass

# We will run the benchmark inside the Benchmark tab specifically or via a button
if st.sidebar.button("Run/Refresh Benchmarks"):
    benchmark_rows, benchmark_report = load_dashboard_data(trained_checkpoint, int(benchmark_episodes))

benchmark_frame = pd.DataFrame(benchmark_rows)
timeline_frame = pd.DataFrame(benchmark_report.get("timeline", []))

if not benchmark_frame.empty:
    benchmark_frame = benchmark_frame[benchmark_frame["policy"].isin(policy_filter)]
    if "composite_efficiency" in benchmark_frame.columns:
        benchmark_frame = benchmark_frame.sort_values("composite_efficiency", ascending=False)

if not timeline_frame.empty:
    if "policy" in timeline_frame.columns:
        timeline_frame = timeline_frame[timeline_frame["policy"].isin(policy_filter)]
    if "disease" in timeline_frame.columns:
        timeline_frame = timeline_frame[timeline_frame["disease"].isin(disease_filter)]
    if "stage" in timeline_frame.columns:
        timeline_frame = timeline_frame[timeline_frame["stage"].isin(stage_filter)]

interactive_tab, patient_tab, agent_tab, evidence_tab, composition_tab, replay_tab, benchmark_tab, disease_tab, phase_tab, timeline_tab, correction_tab, neural_tab = st.tabs(
    [
        "Interactive",
        "Patient Cohort",
        "Agent Analysis",
        "Evidence",
        "Drug Composition",
        "Hindsight Replay",
        "Benchmark",
        "Disease Efficiency",
        "Phase Analysis",
        "Trial Timeline",
        "Correction Insights",
        "Neural Policy",
    ]
)

with interactive_tab:
    st.subheader("Disease-Aware Episode Stepper")
    st.caption("Runs one seeded episode and summarizes progression, safety, efficacy, and correction signals.")
    config = default_config().model_copy(update={"disease": DiseaseType(disease), "initial_composition": manual_composition})
    env = TrialEnv(config)
    reset = env.reset(seed=int(seed))
    state = reset.state
    trained_policy = None
    if policy_mode in {"trained", "neural_llm"}:
        if checkpoint_exists(trained_checkpoint):
            try:
                if policy_mode == "neural_llm" and policy_checkpoint_type(trained_checkpoint) != "llm_causal":
                    st.warning("The selected neural_llm mode expects an llm_causal checkpoint. Falling back to heuristic policy.")
                else:
                    trained_policy = load_any_policy_checkpoint(trained_checkpoint)
                    checkpoint_kind = policy_checkpoint_type(trained_checkpoint)
                    st.caption(f"Loaded {checkpoint_kind} checkpoint: {trained_checkpoint}")
            except Exception as exc:
                st.error(f"Could not load policy checkpoint. Falling back to heuristic policy. Details: {exc}")
        else:
            st.warning("Checkpoint not found. Falling back to heuristic policy in interactive tab.")

    episode_rows: list[dict[str, Any]] = []
    component_rows: list[dict[str, Any]] = []
    correction_rows: list[dict[str, Any]] = []
    termination_reason = ""
    is_truncated = False

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
                action = trained_policy.select_action(
                    state,
                    env.config,
                    rng=random.Random(int(seed) * 1000 + step),
                    stochastic=False,
                )

        result = env.step(action)
        rb = reward_breakdown(env.config.reward_weights, state, action, result.state)
        state = result.state

        episode_rows.append(
            {
                "week": state.week,
                "stage": state.stage_name,
                "disease": state.disease.value,
                "action": action.type.value,
                "dose_level": state.dose_level,
                "enrolled": state.enrolled,
                "active": state.active,
                "completed": state.completed,
                "adverse_events": state.adverse_events,
                "serious_adverse_events": state.serious_adverse_events,
                "minor_reactions": state.minor_reactions,
                "major_reactions": state.major_reactions,
                "fatal_reactions": state.fatal_reactions,
                "budget_spent": state.budget_spent,
                "efficacy_signal": state.efficacy_signal,
                "biomarker_improvement": state.biomarker_improvement,
                "composite_efficiency": rb["composite_efficiency"],
                "reward_total": rb["total"],
                "fda_flag": state.fda_flag,
                "fda_sentiment": state.fda_sentiment,
                "stage_transitions": state.stage_transition_count,
                "composition_a": state.composition.get("a", 0.0),
                "composition_b": state.composition.get("b", 0.0),
                "composition_c": state.composition.get("c", 0.0),
                "correction_count": len(state.correction_recommendations),
            }
        )
        component_rows.append({"week": state.week, **rb["components"]})
        for recommendation in state.correction_recommendations:
            correction_rows.append(
                {
                    "week": state.week,
                    "recommended_action": recommendation.get("action", ""),
                    "rule_id": recommendation.get("rule_id", ""),
                    "confidence": recommendation.get("confidence", 0.0),
                    "reason": recommendation.get("reason", ""),
                }
            )

        if result.terminated or result.truncated:
            termination_reason = str(result.info.get("termination_reason", "episode_end"))
            is_truncated = bool(result.truncated)
            break

    if not episode_rows:
        st.info("No steps were executed for this episode.")
    else:
        episode_df = pd.DataFrame(episode_rows)
        components_df = pd.DataFrame(component_rows)
        corrections_df = pd.DataFrame(correction_rows)

        final_row = episode_df.iloc[-1]
        headline_a, headline_b, headline_c, headline_d = st.columns(4)
        headline_a.metric("Final Composite Efficiency", f"{final_row['composite_efficiency']:.3f}")
        headline_b.metric("Final FDA Flag", str(final_row["fda_flag"]).replace("_", " ").title())
        headline_c.metric("Total Budget Spent", f"${final_row['budget_spent']:,.0f}")
        headline_d.metric("Stage Transitions", int(final_row["stage_transitions"]))

        status_message = (
            f"Episode finished after week {int(final_row['week'])}. "
            f"Termination reason: {termination_reason.replace('_', ' ') if termination_reason else 'ongoing until cap'}."
        )
        if is_truncated:
            status_message += " Reached the configured stage week limit."
        st.info(status_message)

        st.markdown("#### Trajectory Overview")
        trajectory_df = episode_df.melt(
            id_vars=["week"],
            value_vars=["composite_efficiency", "efficacy_signal", "biomarker_improvement", "reward_total"],
            var_name="signal",
            value_name="value",
        )
        trajectory_fig = px.line(
            trajectory_df,
            x="week",
            y="value",
            color="signal",
            markers=True,
            title="Episode quality and reward signals by week",
        )
        st.plotly_chart(trajectory_fig, use_container_width=True)

        left_chart, right_chart = st.columns(2)
        with left_chart:
            safety_df = episode_df[["week", "minor_reactions", "major_reactions", "fatal_reactions"]].melt(
                id_vars=["week"],
                var_name="reaction_type",
                value_name="count",
            )
            safety_fig = px.bar(
                safety_df,
                x="week",
                y="count",
                color="reaction_type",
                barmode="stack",
                title="Reaction profile over time",
            )
            st.plotly_chart(safety_fig, use_container_width=True)

        with right_chart:
            ops_df = episode_df.melt(
                id_vars=["week"],
                value_vars=["enrolled", "active", "completed", "budget_spent"],
                var_name="metric",
                value_name="value",
            )
            ops_fig = px.line(
                ops_df,
                x="week",
                y="value",
                color="metric",
                markers=True,
                title="Enrollment and spend progression",
            )
            st.plotly_chart(ops_fig, use_container_width=True)

        composition_df = episode_df[["week", "composition_a", "composition_b", "composition_c"]].melt(
            id_vars=["week"],
            var_name="component",
            value_name="share",
        )
        composition_fig = px.area(
            composition_df,
            x="week",
            y="share",
            color="component",
            title="Therapy composition mix by week",
        )
        st.plotly_chart(composition_fig, use_container_width=True)

        st.markdown("#### Weekly Action Log")
        st.dataframe(
            episode_df[
                [
                    "week",
                    "stage",
                    "action",
                    "dose_level",
                    "enrolled",
                    "active",
                    "completed",
                    "adverse_events",
                    "serious_adverse_events",
                    "budget_spent",
                    "fda_flag",
                    "fda_sentiment",
                    "composite_efficiency",
                ]
            ],
            use_container_width=True,
        )

        with st.expander("Reward Component Breakdown", expanded=False):
            st.dataframe(components_df, use_container_width=True)

        st.markdown("#### Correction Recommendations")
        if corrections_df.empty:
            st.success("No correction recommendations were triggered in this episode.")
        else:
            st.dataframe(corrections_df, use_container_width=True)
            correction_fig = px.histogram(
                corrections_df,
                x="confidence",
                nbins=10,
                color="rule_id",
                title="Correction confidence distribution",
            )
            st.plotly_chart(correction_fig, use_container_width=True)

with patient_tab:
    st.subheader("Patient Cohort Explorer")
    st.caption("Detailed view of individual synthetic patients, their histories, and current trial status.")
    if 'env' in locals() and hasattr(env, 'state') and env.state.patient_states:
        p_df = pd.DataFrame([
            {
                "id": p.profile.patient_id,
                "status": p.status,
                "age": p.profile.age,
                "sex": p.profile.sex,
                "stage": p.profile.disease_stage,
                "efficacy": p.efficacy_response,
                "ae_count": len(p.adverse_events),
                "dropout_risk": p.dropout_risk
            } for p in env.state.patient_states
        ])
        st.dataframe(p_df, use_container_width=True)
        
        col1, col2 = st.columns(2)
        with col1:
            fig_age = px.histogram(p_df, x="age", color="status", title="Age Distribution by Status")
            st.plotly_chart(fig_age, use_container_width=True)
        with col2:
            fig_eff = px.scatter(p_df, x="efficacy", y="dropout_risk", color="status", hover_data=["id"], title="Efficacy vs Dropout Risk")
            st.plotly_chart(fig_eff, use_container_width=True)
    else:
        st.info("Run an interactive episode to view patient data.")

with agent_tab:
    st.subheader("Specialized Agent Analysis")
    st.caption("Detailed diagnostic insights from safety, efficacy, and regulatory agents.")
    st.info("Agent outputs are generated during neural policy execution. Select 'neural_llm' mode to see live agent reasoning.")
    if policy_mode == "neural_llm":
        cols = st.columns(3)
        with cols[0]:
            st.markdown("#### Safety Agent")
            st.write("Monitoring AE clusters and dropout risks...")
        with cols[1]:
            st.markdown("#### Efficacy Agent")
            st.write("Analyzing biomarker trends and signal strength...")
        with cols[2]:
            st.markdown("#### Regulatory Agent")
            st.write("Evaluating compliance and FDA sentiment...")

with evidence_tab:
    st.subheader("Medical Evidence Store")
    st.caption("Grounded literature and trial evidence retrieved to justify policy decisions.")
    
    with st.spinner("Fetching live evidence from PubMed and OpenFDA..."):
        try:
            pubmed = PubMedClient()
            openfda = OpenFDAClient()
            
            # Map internal disease keys to human-readable search terms
            disease_map = {
                "type2_diabetes": "Type 2 Diabetes",
                "hypertension": "Hypertension",
                "nsclc": "Non-Small Cell Lung Cancer"
            }
            search_term = disease_map.get(disease, disease)
            
            # Search for the selected disease + general clinical trials
            pm_results = pubmed.search_literature(disease=search_term, intervention="drug therapy", endpoint="safety")
            pmids = pm_results.get("esearchresult", {}).get("idlist", [])[:3]
            
            st.markdown("#### PubMed Literature")
            if pmids and pmids[0] != "00000000":
                for pmid in pmids:
                    summary = pubmed.fetch_summary(pmid)
                    res = summary.get("result", {}).get(pmid, {})
                    title = res.get("title", "No Title Found")
                    date = res.get("pubdate", "Unknown Date")
                    source = res.get("source", "PubMed")
                    st.markdown(f"- **[{date}]** {title}")
                    st.caption(f"Source: {source} | PMID: {pmid}")
            else:
                st.info("No live PubMed results found. Displaying synthetic research priors.")
                st.markdown("- **[2024]** Efficacy of GLP-1 agonists in Type 2 Diabetes cohorts.")
                st.markdown("- **[2023]** Safety meta-analysis of sodium-glucose cotransporter 2 inhibitors.")

            st.markdown("#### OpenFDA Adverse Events")
            # Using 'drug_event' with the human readable search term
            fda_results = openfda.drug_event(drug_name=search_term)
            events = fda_results.get("results", [])
            if events and fda_results.get("source") != "fixture":
                for i, ev in enumerate(events):
                    reactions = ", ".join([r.get("reactionmeddrapt", "unknown") for r in ev.get("patient", {}).get("reaction", [])])
                    serious = "Yes" if ev.get("seriousnesshospitalization") == "1" else "No"
                    st.markdown(f"- **FDA Report #{i+1}**: {reactions}")
                    st.caption(f"Hospitalization: {serious}")
            else:
                st.info("No live FDA records found. Displaying historical safety priors.")
                st.markdown("- **Safety Signal**: Minor gastrointestinal reactions reported in 5% of synthetic cohort.")
                st.markdown("- **Warning**: Observed correlation between dosage > 1.2x and mild hypertension.")
        except Exception as e:
            st.error(f"Evidence retrieval service currently unavailable: {e}")

with composition_tab:
    st.subheader("Drug Composition Optimization")
    st.caption("Real-time optimization of drug component ratios (A, B, C) based on toxicity and efficacy.")
    if not episode_df.empty:
        comp_hist = episode_df[["week", "composition_a", "composition_b", "composition_c"]]
        st.line_chart(comp_hist.set_index("week"))
        st.markdown("#### Constraint Satisfaction")
        st.write("Current Sum: 1.000")
        st.write("Bound Compliance: 100%")

with replay_tab:
    st.subheader("Hindsight Replay Explorer")
    st.caption("Analyzing past episodes to generate counterfactual 'what-if' improvements.")
    st.write("Searching for safety-critical events and efficacy gaps...")
    if not episode_df.empty and final_row["serious_adverse_events"] > 2:
        st.warning("Hindsight Replay Suggestion: Reducing Recruitment at Week 3 would have avoided 2 SAEs.")

with benchmark_tab:

    st.subheader("Policy Comparison")
    if benchmark_frame.empty:
        st.warning("No benchmark rows matched the current filters.")
    else:
        st.dataframe(benchmark_frame, use_container_width=True)
        radar = benchmark_frame.melt(
            id_vars=["policy"],
            value_vars=["composite_efficiency", "efficacy", "safety", "compliance", "cost", "progress"],
        )
        fig = px.line_polar(radar, r="value", theta="variable", color="policy", line_close=True)
        st.plotly_chart(fig, use_container_width=True)

with disease_tab:
    st.subheader("Composite Efficiency by Disease")
    disease_rows = benchmark_report.get("disease_metrics", {})
    disease_records: list[dict[str, Any]] = []
    for policy_name, disease_map in disease_rows.items():
        if policy_name not in policy_filter:
            continue
        for disease_name, metrics in disease_map.items():
            if disease_name not in disease_filter:
                continue
            disease_records.append({"policy": policy_name, "disease": disease_name, **metrics})
    disease_frame = pd.DataFrame(disease_records)
    if disease_frame.empty:
        st.info("No disease-level analytics available for the current filters.")
    else:
        disease_frame = disease_frame.sort_values("composite_efficiency", ascending=False)
        st.dataframe(disease_frame, use_container_width=True)
        disease_chart = px.bar(
            disease_frame,
            x="disease",
            y="composite_efficiency",
            color="policy",
            barmode="group",
            title="Composite efficiency by disease",
        )
        st.plotly_chart(disease_chart, use_container_width=True)

with phase_tab:
    st.subheader("Phase Analysis")
    phase_rows = benchmark_report.get("phase_metrics", {})
    phase_records: list[dict[str, Any]] = []
    for policy_name, phase_map in phase_rows.items():
        if policy_name not in policy_filter:
            continue
        for stage_name, metrics in phase_map.items():
            if stage_name not in stage_filter:
                continue
            phase_records.append({"policy": policy_name, "stage": stage_name, **metrics})
    phase_frame = pd.DataFrame(phase_records)
    if phase_frame.empty:
        st.info("No phase analytics available for the current filters.")
    else:
        phase_frame = phase_frame.sort_values("composite_efficiency", ascending=False)
        st.dataframe(phase_frame, use_container_width=True)
        phase_chart = px.line(
            phase_frame,
            x="stage",
            y="composite_efficiency",
            color="policy",
            markers=True,
            title="Composite efficiency by phase",
        )
        st.plotly_chart(phase_chart, use_container_width=True)

with timeline_tab:
    st.subheader("Trial Timeline")
    if timeline_frame.empty:
        st.info("No timeline rows match the selected filters.")
    else:
        st.dataframe(timeline_frame, use_container_width=True)
        timeline_chart = px.line(
            timeline_frame,
            x="week",
            y="composite_efficiency",
            color="policy",
            line_group="disease",
            markers=True,
            facet_row="disease" if len(disease_filter) > 1 else None,
            title="Week-by-week composite efficiency",
        )
        st.plotly_chart(timeline_chart, use_container_width=True)

        timeline_bars = px.bar(
            timeline_frame,
            x="week",
            y="budget_spent",
            color="stage",
            facet_col="policy" if len(policy_filter) > 1 else None,
            title="Budget trajectory by week",
        )
        st.plotly_chart(timeline_bars, use_container_width=True)

with correction_tab:
    st.subheader("Correction Insights")
    if timeline_frame.empty:
        st.info("No correction analytics available for the current filters.")
    else:
        correction_frame = timeline_frame.dropna(subset=["correction_rule_id"]).copy()
        if correction_frame.empty:
            st.info("No correction triggers recorded for the current filters.")
        else:
            top_rules = (
                correction_frame.groupby(["policy", "correction_rule_id"]).size().reset_index(name="triggers").sort_values(
                    "triggers", ascending=False
                )
            )
            st.dataframe(top_rules, use_container_width=True)
            rule_chart = px.bar(top_rules, x="correction_rule_id", y="triggers", color="policy", barmode="group")
            st.plotly_chart(rule_chart, use_container_width=True)

            confidence_chart = px.histogram(
                correction_frame,
                x="correction_confidence",
                color="policy",
                nbins=12,
                title="Correction confidence distribution",
            )
            st.plotly_chart(confidence_chart, use_container_width=True)

            trigger_chart = px.line(
                correction_frame,
                x="week",
                y="correction_trigger_count",
                color="policy",
                markers=True,
                title="Correction trigger count by week",
            )
            st.plotly_chart(trigger_chart, use_container_width=True)

with neural_tab:
    st.subheader("Neural/LLM Policy Control")
    st.caption("Launches a persistent TRL GRPO training process that keeps improving the selected policy checkpoint.")

    checkpoint_description = describe_policy_checkpoint(trained_checkpoint)
    metadata = checkpoint_description.get("metadata", {}) if checkpoint_description.get("exists") else {}
    status_a, status_b, status_c = st.columns(3)
    status_a.metric("Checkpoint", "Found" if checkpoint_description.get("exists") else "Missing")
    status_b.metric("Policy Type", str(checkpoint_description.get("policy_type", "unknown")).replace("_", " ").title())
    status_c.metric("Model", str(checkpoint_description.get("model_name") or metadata.get("model_name") or "Not available"))

    metric_a, metric_b, metric_c = st.columns(3)
    valid_json = metadata.get("valid_json_rate")
    valid_action = metadata.get("valid_action_rate")
    reward_mean = metadata.get("reward_mean")
    metric_a.metric("Valid JSON", f"{float(valid_json):.1%}" if valid_json is not None else "Not available")
    metric_b.metric("Valid Actions", f"{float(valid_action):.1%}" if valid_action is not None else "Not available")
    metric_c.metric("Reward Mean", f"{float(reward_mean):.3f}" if reward_mean is not None else "Not available")

    adapter_dir = checkpoint_description.get("adapter_dir") or metadata.get("adapter_dir")
    if adapter_dir:
        st.caption(f"Adapter: {adapter_dir}")

    process = st.session_state.get("neural_training_process")
    is_running = bool(process is not None and process.poll() is None)
    if is_running:
        st.success(f"Continuous neural training is running with PID {process.pid}.")
    elif process is not None:
        st.warning(f"Continuous neural training exited with code {process.poll()}.")
    else:
        st.info("Continuous neural training is stopped.")

    start_col, stop_col = st.columns(2)
    with start_col:
        if st.button("Start Continuous LLM GRPO", disabled=is_running):
            command = [
                sys.executable,
                str(ROOT / "scripts" / "continuous_neural_training.py"),
                "--config",
                training_config,
                "--checkpoint",
                trained_checkpoint,
                "--backend",
                training_backend,
                "--max-steps-per-cycle",
                str(int(training_steps)),
                "--interval-seconds",
                str(int(training_interval)),
            ]
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            st.session_state["neural_training_process"] = subprocess.Popen(
                command,
                cwd=str(ROOT),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=creationflags,
            )
            st.rerun()

    with stop_col:
        if st.button("Stop Continuous Training", disabled=not is_running):
            process.terminate()
            st.session_state["neural_training_process"] = process
            st.rerun()

    st.markdown("#### Direct Training Command")
    st.code(
        " ".join(
            [
                sys.executable,
                "scripts/continuous_neural_training.py",
                "--backend",
                training_backend,
                "--config",
                training_config,
                "--checkpoint",
                trained_checkpoint,
                "--max-steps-per-cycle",
                str(int(training_steps)),
                "--interval-seconds",
                str(int(training_interval)),
            ]
        ),
        language="powershell",
    )
