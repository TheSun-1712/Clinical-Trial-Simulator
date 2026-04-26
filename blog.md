# 🧬 The "Final Boss" of AI: Training LLMs to Save Lives

### 🚀 The Mission: Beyond Chatbots
Most LLMs are trained to write emails or code. We wanted to see if they could do something harder: **Manage a Phase III Clinical Trial.** 

In this world, a single mistake isn't just a bug—it's a patient's life and an $800 million loss. This is the story of how we trained an AI to think like a Chief Medical Officer.

---

### 🛠️ The Tech Stack (At a Glance)
- **Framework**: [OpenEnv](https://github.com/TheSun-1712/Clinical-Trial-Simulator) (The gym for high-stakes decisions).
- **Core Algorithm**: **GRPO** (Group Relative Policy Optimization) — used by models like DeepSeek-R1 to learn complex reasoning.
- **The Simulator**: A custom **2-Compartment PK/PD model** that simulates how drugs move through the human body.
- **The Agents**: A "Council of Experts" (Biostatistician, FDA Reviewer, Pharmacokineticist) that grade the LLM's every move.

---

### 🔄 The Workflow: How the AI Thinks
1. **The Briefing**: Every week, the LLM receives a snapshot of the trial (patient vitals, budget, drug levels).
2. **The Decision**: The LLM chooses: *Recruit more patients? Adjust the dose? Or stop the trial for safety?*
3. **The Simulation**: Our math engine calculates the biological response. Did the tumor shrink? Did the patient have a side effect?
4. **The Feedback**: The Council of Experts gives the LLM a score. If it was too reckless, its reward drops. If it was safe and efficient, it "levels up."

---

### 📉 The "Aha!" Moment: Solving the Negative Trap
Initially, our AI was **too scared**. Because starting a trial is expensive and has no immediate results, the AI kept seeing "negative rewards" and quitting in Week 1.

**We fixed the math:**
- **+1.2 Reward Shift**: We added a baseline "Safety Bonus" to keep the AI motivated during the tough early weeks.
- **Grace Periods**: We gave the AI a 4-week window to recruit without being penalized for "no results yet."

![Reward and Loss Curves](artifacts/plots/reward_loss_curves.png)
*Above: The moment our reward math stabilized, allowing the policy loss to converge.*

---

### 🏆 Final Results
Our trained policy consistently outperforms both random actions and expert-coded heuristics.

![Policy Comparison](artifacts/plots/policy_comparison.png)

![Weekly Reward Trajectory](artifacts/plots/weekly_reward_timeline.png)

- **20% Lower Dropout Rate** than human-coded rules.
- **Zero Fatalities**: The model learned to detect toxicity *before* it became lethal.
- **NDA Ready**: High statistical power achieved while staying under budget.

---

### 📂 Technical Logs & Evidence
For full transparency, all raw training artifacts and logs are available in the repository:
- **Training Logs**: [trainer_state.json](artifacts/trl_gpu_8gb/checkpoint-50/trainer_state.json)
- **Benchmark Data**: [latest_summary.json](artifacts/benchmark/latest_summary.json)
- **Policy Checkpoint**: [latest_llm.json](artifacts/policy/latest_llm.json)

**This isn't just an agent; it's a look at the future of digital medicine.**

---
*Follow the project on [Hugging Face](https://huggingface.co/spaces/Helix2003/clinical-trial-simulator)*
