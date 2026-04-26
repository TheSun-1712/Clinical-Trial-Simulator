from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PLOTS_DIR = ROOT / "artifacts" / "plots"


def _load_json(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Missing artifact: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _build_reward_loss_curve() -> Path:
    trainer_state = _load_json(ROOT / "artifacts" / "trl_gpu_8gb" / "checkpoint-50" / "trainer_state.json")
    history = trainer_state.get("log_history", [])
    if not history:
        raise RuntimeError("No log_history found in trainer_state.json")

    df = pd.DataFrame(history)
    if "step" not in df:
        raise RuntimeError("trainer_state log_history does not contain step values")

    fig, ax1 = plt.subplots(figsize=(10, 5.5))
    ax1.plot(df["step"], df.get("reward", pd.Series([0] * len(df))), marker="o", linewidth=2.2, color="#0072B2", label="GRPO reward")
    ax1.set_xlabel("Training Step")
    ax1.set_ylabel("Reward (mean)", color="#0072B2")
    ax1.tick_params(axis="y", labelcolor="#0072B2")

    ax2 = ax1.twinx()
    ax2.plot(df["step"], df.get("loss", pd.Series([0] * len(df))), marker="s", linestyle="--", linewidth=1.8, color="#D55E00", label="Policy loss")
    ax2.set_ylabel("Loss", color="#D55E00")
    ax2.tick_params(axis="y", labelcolor="#D55E00")

    lines_1, labels_1 = ax1.get_legend_handles_labels()
    lines_2, labels_2 = ax2.get_legend_handles_labels()
    ax1.legend(lines_1 + lines_2, labels_1 + labels_2, loc="lower right")

    ax1.set_title("GRPO Training Dynamics (Resumed Run)")
    ax1.grid(alpha=0.25)
    fig.tight_layout()

    out_path = PLOTS_DIR / "reward_loss_curves.png"
    fig.savefig(out_path, dpi=160)
    plt.close(fig)
    return out_path


def _build_policy_comparison_plot() -> Path:
    summary = _load_json(ROOT / "artifacts" / "benchmark" / "latest_summary.json")
    rows = summary.get("policy_rows", [])
    if not rows:
        raise RuntimeError("No policy_rows in benchmark summary")

    df = pd.DataFrame(rows)
    df = df[["policy", "total_reward", "composite_efficiency", "compliance", "cost"]]

    fig, ax = plt.subplots(figsize=(9.5, 5.2))
    colors = ["#999999", "#E69F00", "#009E73"]
    ax.bar(df["policy"], df["total_reward"], color=colors[: len(df)], alpha=0.9)
    ax.axhline(0.0, color="#333333", linewidth=1)
    ax.set_title("Policy Comparison on Clinical Trial Simulator")
    ax.set_xlabel("Policy")
    ax.set_ylabel("Mean Episode Total Reward")
    for idx, value in enumerate(df["total_reward"]):
        ax.text(idx, value + (0.2 if value >= 0 else -0.35), f"{value:.2f}", ha="center", va="bottom" if value >= 0 else "top", fontsize=9)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()

    out_path = PLOTS_DIR / "policy_comparison.png"
    fig.savefig(out_path, dpi=160)
    plt.close(fig)
    return out_path


def _build_weekly_timeline_plot() -> Path:
    timeline = _load_json(ROOT / "artifacts" / "benchmark" / "latest_timeline.json")
    df = pd.DataFrame(timeline)
    if df.empty:
        raise RuntimeError("Empty timeline artifact")

    grouped = (
        df.groupby(["policy", "week"], as_index=False)["total_reward"]
        .mean()
        .sort_values(["policy", "week"])
    )

    fig, ax = plt.subplots(figsize=(10.5, 5.5))
    palette = {"random": "#888888", "heuristic": "#CC79A7", "trained": "#009E73"}
    for policy, policy_df in grouped.groupby("policy"):
        ax.plot(
            policy_df["week"],
            policy_df["total_reward"],
            label=policy,
            linewidth=2,
            color=palette.get(policy, None),
        )
    ax.set_title("Weekly Reward Trajectory by Policy")
    ax.set_xlabel("Week")
    ax.set_ylabel("Per-step Reward")
    ax.grid(alpha=0.25)
    ax.legend()
    fig.tight_layout()

    out_path = PLOTS_DIR / "weekly_reward_timeline.png"
    fig.savefig(out_path, dpi=160)
    plt.close(fig)
    return out_path


def main() -> None:
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    outputs = [
        _build_reward_loss_curve(),
        _build_policy_comparison_plot(),
        _build_weekly_timeline_plot(),
    ]
    for output in outputs:
        print(f"[saved] {output.relative_to(ROOT)}")


if __name__ == "__main__":
    main()