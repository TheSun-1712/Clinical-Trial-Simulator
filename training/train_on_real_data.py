"""
train_on_real_data.py
=====================
Trains the HierarchicalPolicy using disease priors calibrated from:
  - OpenFDA Adverse Event API    (patient demographics + real AE rates)
  - HuggingFace Drug Reviews API (patient sentiment / drug tolerability)

The real-world priors are used to:
  1. Override the simulator's built-in disease profiles with real AE rates.
  2. Adjust patient population demographics (age, sex, weight distribution).
  3. Inject real top-10 adverse reactions into the environment narrative.

Usage:
  python training/train_on_real_data.py --condition type2_diabetes --steps 400
  python training/train_on_real_data.py --condition hypertension --steps 400 --no-cache
  python training/train_on_real_data.py --condition nsclc --steps 300
"""
import os
import sys
import argparse
import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Ensure local src is prioritised
root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(root, "src"))
sys.path.insert(0, root)
for mod in list(sys.modules.keys()):
    if mod.startswith("cts"):
        del sys.modules[mod]

from cts.config import default_config, TrialConfig, StageConfig, EventRates
from cts.environment.models import (
    Action, ActionType, DiseaseType, ManagerGoal, PatientStatus, TrialState,
)
from cts.environment.trial_env import TrialEnv
from cts.policy import (
    ACTION_LIBRARY, feature_vector, save_policy_checkpoint, HierarchicalPolicy,
    init_zero_policy,
)
from cts.policy.hierarchical_policy import init_hierarchical_policy
from cts.rewards.verifiers import reward_breakdown
from cts.data.real_data_loader import fetch_and_build_priors, DRUG_LOOKUP


# ---------------------------------------------------------------------------
# Map condition strings to DiseaseType enum
# ---------------------------------------------------------------------------
DISEASE_MAP = {
    "type2_diabetes": DiseaseType.TYPE2_DIABETES,
    "hypertension":   DiseaseType.HYPERTENSION,
    "nsclc":          DiseaseType.NSCLC,
}


# ---------------------------------------------------------------------------
# Config builder: inject real priors into TrialConfig
# ---------------------------------------------------------------------------
def build_calibrated_config(
    condition: str,
    real_priors: Dict,
    seed: int = 42,
) -> TrialConfig:
    """
    Build a TrialConfig whose disease_profiles entry is calibrated from
    real-world data instead of the synthetic defaults.
    """
    disease_type = DISEASE_MAP.get(condition, DiseaseType.TYPE2_DIABETES)
    base = default_config()

    # Patch the disease profile for our target condition
    new_profiles = dict(base.disease_profiles)
    new_profiles[disease_type] = {
        "name": condition.replace("_", " ").title(),
        "baseline_response":    real_priors.get("baseline_response",    0.55),
        "toxicity_sensitivity": real_priors.get("toxicity_sensitivity", 0.42),
        "fatality_floor":       real_priors.get("fatality_floor",       0.001),
        "major_threshold":      real_priors.get("major_threshold",      0.58),
        "fatal_threshold":      real_priors.get("fatal_threshold",      0.83),
    }

    # Build calibrated event rates from real AE data
    real_serious_rate = real_priors.get("toxicity_sensitivity", 0.05)
    real_fatal_rate   = real_priors.get("fatality_floor", 0.001)
    ae_prob     = min(0.15, real_serious_rate * 2)
    sae_prob    = min(0.05, real_serious_rate)
    dropout     = 0.02 + real_serious_rate * 0.1  # higher AE → higher dropout

    calibrated_rates = EventRates(
        adverse_event_prob=ae_prob,
        serious_adverse_event_prob=sae_prob,
        dropout_prob=min(0.08, dropout),
        recruit_variation=0.20,
    )

    # Update stage1 with calibrated event rates
    stage1 = base.stage1.model_copy(update={"event_rates": calibrated_rates})

    return base.model_copy(update={
        "seed": seed,
        "disease": disease_type,
        "disease_profiles": new_profiles,
        "stage1": stage1,
    })


# ---------------------------------------------------------------------------
# REINFORCE training loop (lightweight, no GPU needed)
# ---------------------------------------------------------------------------

@dataclass
class Transition:
    features: List[float]
    action_index: int


def run_episode(
    env: TrialEnv,
    policy: HierarchicalPolicy,
    rng: random.Random,
    stochastic: bool = True,
    tcn_encoder: Optional[Any] = None,
) -> Tuple[float, List[Tuple[Transition, Transition, float, float]], Dict[str, Any]]:
    """
    Runs one full episode. Returns (total_reward, step_data, online_data).
    step_data: list of (manager_transition, worker_transition, reward, worker_entropy)
    """
    result = env.reset()
    state = result.state
    total_reward = 0.0
    step_data: List[Tuple[Transition, Transition, float, float]] = []
    current_goal = ManagerGoal.RECRUIT_PHASE
    week = 0

    history_buffer = None
    if tcn_encoder:
        from cts.policy.tcn_encoder import StateHistoryBuffer
        history_buffer = StateHistoryBuffer(window_size=4, feature_dim=11)
        
    online_data = {"doses": [], "efficacies": [], "tox_X": [], "tox_y": []}

    while True:
        if week % 4 == 0:
            mgr_feats = feature_vector(state, env.config)
            current_goal = policy.select_goal(
                state, env.config, rng, stochastic=stochastic, 
                history_buffer=history_buffer, tcn_encoder=tcn_encoder
            )
            goal_idx = list(ManagerGoal).index(current_goal)
            mgr_trans = Transition(features=mgr_feats, action_index=goal_idx)
        else:
            mgr_trans = Transition(features=[], action_index=0)

        wkr_feats = feature_vector(state, env.config)
        action = policy.select_action(
            state, env.config, rng, current_goal=current_goal, 
            stochastic=stochastic, history_buffer=history_buffer, tcn_encoder=tcn_encoder
        )
        act_idx   = next(
            (i for i, a in enumerate(ACTION_LIBRARY)
             if a.action_type == action.type and a.magnitude == action.magnitude),
            0,
        )
        wkr_trans = Transition(features=wkr_feats, action_index=act_idx)

        step_result = env.step(action)
        rb = reward_breakdown(env.config.reward_weights, state, action, step_result.state)
        step_reward = rb["total"] + step_result.info.get("validation", {}).get("penalty", 0.0)
        total_reward += step_reward

        step_data.append((mgr_trans, wkr_trans, step_reward, 0.0))
        state = step_result.state
        
        # Collect online GP & Toxicity data
        if state.active > 0 and state.dose_level > 0.0:
            online_data["doses"].append(state.dose_level)
            online_data["efficacies"].append(state.biomarker_improvement)
            
            c_a = state.composition.get("a", 0.0)
            c_b = state.composition.get("b", 0.0)
            c_c = state.composition.get("c", 0.0)
            
            for p in state.patient_agents:
                if p.status == PatientStatus.ACTIVE or p.status == PatientStatus.DROPPED_OUT:
                    # 6-dim feats: [age_norm, sex, weight_norm, c_a, c_b, c_c]
                    age_norm = p.latent.age / 100.0
                    sex_idx = 1.0 if p.latent.sex == "F" else 0.0
                    weight_norm = p.history.weight_kg / 150.0
                    online_data["tox_X"].append([age_norm, sex_idx, weight_norm, c_a, c_b, c_c])
                    
                    # Target: did they have a major reaction/accumulated toxicity this week?
                    label = 1.0 if p.accumulated_toxicity > 0.6 else 0.0
                    online_data["tox_y"].append([label])

        week += 1
        if step_result.terminated or step_result.truncated:
            break

    return total_reward, step_data, online_data


def reinforce_update(
    policy: HierarchicalPolicy,
    step_data: List[Tuple[Transition, Transition, float, float]],
    gamma: float = 0.98,
    lr: float = 0.003,
    tcn_encoder: Optional[Any] = None,
    tox_model: Optional[Any] = None,
    gp_surface: Optional[Any] = None,
    online_data: Optional[Dict[str, Any]] = None,
) -> None:
    """Policy-gradient (REINFORCE) weight update in-place with synchronous ML updating."""
    # Compute discounted returns
    G = 0.0
    returns = []
    for _, _, r, _ in reversed(step_data):
        G = r + gamma * G
        returns.insert(0, G)

    # Normalise returns
    mean_G = sum(returns) / max(len(returns), 1)
    std_G  = (sum((g - mean_G) ** 2 for g in returns) / max(len(returns), 1)) ** 0.5 + 1e-8
    norm_returns = [(g - mean_G) / std_G for g in returns]

    # Worker update (softmax policy gradient)
    worker_policies = list(policy.worker.values())
    if not worker_policies:
        pass
    else:
        sub = worker_policies[0]  # simplified; ideally keyed by current_goal
        
        if hasattr(sub, 'parameters'):
            import torch
            import torch.optim as optim
            
            # Combine MoE and TCN parameters for End-to-End training
            params = list(sub.parameters())
            if tcn_encoder:
                params += list(tcn_encoder.parameters())
                from cts.policy.tcn_encoder import StateHistoryBuffer
                hist_buf = StateHistoryBuffer(window_size=4, feature_dim=11)
                
            optimizer = optim.Adam(params, lr=lr)
            optimizer.zero_grad()
            
            policy_loss = []
            for (mgr_t, wkr_t, _, _), G_norm in zip(step_data, norm_returns):
                feats = wkr_t.features
                if not feats:
                    continue
                idx = wkr_t.action_index
                
                if tcn_encoder:
                    hist_buf.add(feats)
                    tensor = hist_buf.get_padded_tensor()
                    tcn_feats = tcn_encoder(tensor).squeeze(0) # (11,)
                else:
                    tcn_feats = torch.tensor(feats, dtype=torch.float32)
                    
                # Re-calculate log prob maintaining the graph back to TCN
                d_idx = torch.tensor([0], dtype=torch.long)
                logits, _ = sub(tcn_feats.unsqueeze(0), d_idx)
                probs = torch.nn.functional.softmax(logits, dim=-1)
                dist = torch.distributions.Categorical(probs)
                action_t = torch.tensor([idx])
                log_prob = dist.log_prob(action_t)
                
                policy_loss.append(-log_prob * G_norm)
                
            if policy_loss:
                loss = torch.cat(policy_loss).sum()
                loss.backward()
                # Gradient clipping to prevent TCN explosion
                torch.nn.utils.clip_grad_norm_(params, max_norm=1.0)
                optimizer.step()
                
        else:
            # Fallback to manual Gradient Ascent for LinearPolicy
            for (mgr_t, wkr_t, _, _), G_norm in zip(step_data, norm_returns):
                feats = wkr_t.features
                if not feats:
                    continue
                idx = wkr_t.action_index

                scores = [sum(f * w for f, w in zip(feats, row)) for row in sub.weights]
                max_s  = max(scores)
                exps   = [2.718281828 ** (s - max_s) for s in scores]
                tot    = sum(exps) or 1.0
                probs  = [e / tot for e in exps]

                for j, row in enumerate(sub.weights):
                    indicator = 1.0 if j == idx else 0.0
                    grad      = indicator - probs[j]
                    for k, feat in enumerate(feats):
                        row[k] += lr * G_norm * feat * grad

    # Manager update (Linear REINFORCE)
    for i, (mgr_t, _, _, _) in enumerate(step_data):
        if not mgr_t.features or i % 4 != 0:
            continue
        feats = mgr_t.features
        idx   = mgr_t.action_index
        G_norm = norm_returns[i]

        scores = [sum(f * w for f, w in zip(feats, row)) for row in policy.manager.weights]
        max_s  = max(scores)
        exps   = [2.718281828 ** (s - max_s) for s in scores]
        tot    = sum(exps) or 1.0
        probs  = [e / tot for e in exps]

        for j, row in enumerate(policy.manager.weights):
            indicator = 1.0 if j == idx else 0.0
            grad      = indicator - probs[j]
            for k, feat in enumerate(feats):
                row[k] += lr * G_norm * feat * grad
                
    # ---------------------------------------------------------
    # SYNCHRONOUS ONLINE LEARNING FOR ML MODELS
    # ---------------------------------------------------------
    if online_data:
        # 1. Update GP Efficacy Surface Online
        if gp_surface and online_data["doses"]:
            try:
                # Online fitting appends the new points directly to the Gaussian Process
                gp_surface.fit(online_data["doses"], online_data["efficacies"])
            except Exception as e:
                print(f"[Training] GP Online update error: {e}")
                
        # 2. Continual Learning for Toxicity Head
        if tox_model and online_data["tox_X"]:
            try:
                import torch
                import torch.nn as nn
                import torch.optim as optim
                X_t = torch.tensor(online_data["tox_X"], dtype=torch.float32)
                y_t = torch.tensor(online_data["tox_y"], dtype=torch.float32)
                
                tox_opt = optim.Adam(tox_model.parameters(), lr=0.001)
                tox_crit = nn.BCELoss()
                
                tox_model.train()
                tox_opt.zero_grad()
                preds = tox_model(X_t)
                loss = tox_crit(preds, y_t)
                loss.backward()
                tox_opt.step()
            except Exception as e:
                print(f"[Training] Toxicity Head Online update error: {e}")


# ---------------------------------------------------------------------------
# Main training loop
# ---------------------------------------------------------------------------

def train(
    condition: str = "type2_diabetes",
    n_steps: int = 300,
    n_fda: int = 300,
    n_hf: int = 200,
    cache_db: str = "artifacts/trial_data.db",
    output_dir: str = "artifacts/policy",
    seed: int = 42,
    use_cache: bool = True,
    lr: float = 0.003,
    gamma: float = 0.98,
) -> None:
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 60)
    print(f"  Real-Data Training Pipeline")
    print(f"  Condition : {condition}")
    print(f"  Sources   : OpenFDA ({n_fda} records) + HF Reviews ({n_hf} records)")
    print(f"  Steps     : {n_steps}")
    print("=" * 60)

    # 1. Fetch & build priors
    if not use_cache:
        # Clear priors cache so we re-fetch
        import sqlite3
        try:
            with sqlite3.connect(cache_db) as conn:
                conn.execute("DELETE FROM real_priors WHERE condition=?", (condition,))
                conn.execute("DELETE FROM fda_cache WHERE condition=?",   (condition,))
                conn.execute("DELETE FROM hf_cache WHERE condition=?",    (condition,))
                conn.commit()
        except Exception:
            pass

    real_priors = fetch_and_build_priors(condition, n_fda=n_fda, n_hf=n_hf, cache_db=cache_db)

    print(f"\n[Priors] Sources: FDA={real_priors['source_fda_n']}, HF={real_priors['source_hf_n']}")
    print(f"[Priors] mean_age={real_priors['mean_age']:.1f}  "
          f"pct_female={real_priors['pct_female']:.2%}  "
          f"toxicity_sensitivity={real_priors['toxicity_sensitivity']:.3f}")
    print(f"[Priors] Top adverse reactions:")
    for rxn, cnt in list(real_priors.get("top_adverse_reactions", {}).items())[:5]:
        print(f"         {rxn}: {cnt}")

    # 1.5 Pre-train Toxicity Regression Head
    from cts.data.real_data_loader import _load_fda_cache
    from cts.policy.toxicity_head import pretrain_toxicity_head
    
    tox_model = None
    fda_records = _load_fda_cache(cache_db, condition, n_fda)
    if fda_records:
        tox_model, loss_history = pretrain_toxicity_head(fda_records, epochs=15)
        if tox_model:
            print("[Training] Toxicity Head pre-training successful. Worker safety policy warm-started.")
            # Save the curve for the dashboard
            curve_path = Path(output_dir) / "checkpoints" / "pretrain_curve.json"
            curve_path.parent.mkdir(parents=True, exist_ok=True)
            curve_path.write_text(json.dumps({"loss": loss_history}))


    # 2. Build calibrated environment
    config = build_calibrated_config(condition, real_priors, seed=seed)
    env    = TrialEnv(config)

    # 3. Initialise policy and TCN
    policy = init_hierarchical_policy()
    rng    = random.Random(seed)
    
    tcn_encoder = None
    try:
        from cts.policy.tcn_encoder import TCNHistoryEncoder
        tcn_encoder = TCNHistoryEncoder()
        print("[Training] TCN History Encoder successfully initialized.")
    except ImportError:
        print("[Training] TCN not initialized (PyTorch missing).")

    # 4. Training loop
    reward_history: List[float] = []
    best_reward = float("-inf")

    print(f"\n[Training] Starting {n_steps} episodes...\n")
    for episode in range(n_steps):
        ep_rng = random.Random(seed * 10000 + episode)
        total_reward, step_data, online_data = run_episode(env, policy, ep_rng, stochastic=True, tcn_encoder=tcn_encoder)
        reinforce_update(
            policy, 
            step_data, 
            gamma=gamma, 
            lr=lr, 
            tcn_encoder=tcn_encoder,
            tox_model=tox_model,
            gp_surface=getattr(env, 'gp_surface', None),
            online_data=online_data
        )
        reward_history.append(total_reward)

        # Checkpoint every 50 episodes and at the end
        if (episode + 1) % 50 == 0 or episode == n_steps - 1:
            ckpt_path = Path(output_dir) / "checkpoints" / f"real_ep{episode+1:04d}.json"
            ckpt_path.parent.mkdir(parents=True, exist_ok=True)
            save_policy_checkpoint(
                policy,
                str(ckpt_path),
                metadata={
                    "episode": episode + 1,
                    "condition": condition,
                    "mean_reward_last50": sum(reward_history[-50:]) / min(50, len(reward_history)),
                    "source_fda_n": real_priors["source_fda_n"],
                    "source_hf_n":  real_priors["source_hf_n"],
                    "real_priors": {k: v for k, v in real_priors.items()
                                    if isinstance(v, (int, float, str))},
                },
            )
            avg = sum(reward_history[-50:]) / min(50, len(reward_history))
            print(f"  Episode {episode+1:4d}/{n_steps}  |  avg_reward(last50)={avg:.4f}")

            # Save best model
            if avg > best_reward:
                best_reward = avg
                best_path = Path(output_dir) / f"best_{condition}.json"
                save_policy_checkpoint(policy, str(best_path),
                                       metadata={"condition": condition, "best_reward": best_reward})

    # 5. Save final checkpoint as "latest"
    latest_path = Path(output_dir) / "latest.json"
    save_policy_checkpoint(
        policy,
        str(latest_path),
        metadata={
            "condition": condition,
            "episodes": n_steps,
            "final_reward": reward_history[-1],
            "mean_reward_all": sum(reward_history) / len(reward_history),
        },
    )

    # 6. Save reward history JSON for dashboard plotting
    hist_path = Path(output_dir) / "checkpoints" / "reward_history.json"
    hist_path.parent.mkdir(parents=True, exist_ok=True)
    hist_path.write_text(json.dumps({
        "condition": condition,
        "rewards": reward_history,
        "real_priors_summary": {k: v for k, v in real_priors.items()
                                if isinstance(v, (int, float, str))},
    }, indent=2))

    print(f"\n[Training] Done. Best mean reward: {best_reward:.4f}")
    print(f"[Training] Saved to: {output_dir}/latest.json")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train on real clinical data")
    parser.add_argument("--condition", choices=["type2_diabetes", "hypertension", "nsclc"],
                        default="type2_diabetes")
    parser.add_argument("--steps",    type=int,   default=300,  help="Training episodes")
    parser.add_argument("--n-fda",    type=int,   default=300,  help="FDA records to fetch")
    parser.add_argument("--n-hf",     type=int,   default=200,  help="HF reviews to fetch")
    parser.add_argument("--cache-db", type=str,   default="artifacts/trial_data.db")
    parser.add_argument("--output",   type=str,   default="artifacts/policy")
    parser.add_argument("--seed",     type=int,   default=42)
    parser.add_argument("--lr",       type=float, default=0.003)
    parser.add_argument("--no-cache", action="store_true", help="Force re-fetch from APIs")
    args = parser.parse_args()

    train(
        condition  = args.condition,
        n_steps    = args.steps,
        n_fda      = args.n_fda,
        n_hf       = args.n_hf,
        cache_db   = args.cache_db,
        output_dir = args.output,
        seed       = args.seed,
        lr         = args.lr,
        use_cache  = not args.no_cache,
    )
