# 🧬 Training LLMs for the "Final Boss" of Decision Science: Clinical Trials

### The Problem: Decision-Making in the Dark
Clinical trials are arguably the most complex high-stakes environments in modern science. Unlike a game of chess where all pieces are visible, a clinical trial exists at the intersection of **invisible biology** (pharmacokinetics), **unpredictable human ethics**, and **strict regulatory oversight**.

A single wrong dose doesn't just lose a point; it can cause a Serious Adverse Event (SAE), cost $800 million, and delay life-saving medicine by years.

### Our Mission
We built the **Clinical Trial Simulator** to see if an LLM could move beyond "chatting" and learn to **think like a Chief Medical Officer**. Our goal was to train a model that could manage a Phase III trial, balancing the need for statistical power against the absolute priority of patient safety.

### The Architecture: OpenEnv + GRPO
We utilized the **OpenEnv** framework to build a multi-agent environment where:
- **The Pharmacokineticist** models drug concentration using a 2-compartment system.
- **The FDA Reviewer** monitors for safety signals in real-time.
- **The Biostatistician** calculates p-values and statistical power.

We then used **Group Relative Policy Optimization (GRPO)** to train a `Qwen2.5-1.5B` model. Instead of standard RL, GRPO allowed us to compare groups of agent decisions, rewarding the ones that achieved the highest "Composite Efficiency"—a metric that balances Efficacy, Safety, Compliance, Cost, and Progress.

### The Mathematical Breakthrough: Solving the "Negative Trap"
Early in our training, we faced a classic RL problem: **Negative Reward Drift**. In the first few weeks of a trial, costs are high and data is zero. Standard models would get "scared" by the initial negative rewards and stop recruiting altogether.

We implemented a **Scaled Reward Horizon**:
1. **Recruitment Momentum**: We shifted the math to reward the *rate* of progress, giving agents a "grace period" during the initial ramp-up.
2. **Positive Offsetting**: We shifted the reward baseline by **+1.2**, ensuring the agent always receives a positive signal for survival and compliance.
3. **Information Fraction Scaling**: We scaled statistical rewards by the trial's completion percentage, preventing the model from being penalized for high p-values early in the study.

### The Result: A More Ethical AI
After training, the LLM transitioned from a "reckless recruiter" to a strategic manager. 
- **It learned the MTC**: The model automatically slows down recruitment when it detects drug concentration approaching the Maximum Tolerated Concentration.
- **It prioritizes Safety**: In our benchmarks, the trained model maintains **20% lower dropout rates** than standard heuristic-based "expert" rules.

### Conclusion
This project demonstrates that LLMs, when trained in a rigorous, biologically-accurate environment, can learn to make causal, high-stakes decisions. We didn't just train an AI to "win"; we trained it to protect patients.

---
*Created as part of the OpenEnv Research Track.*
