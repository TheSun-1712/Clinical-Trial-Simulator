from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, List, Optional

from cts.config import TrialConfig
from cts.environment.models import Action, ActionType, ManagerGoal, TrialState
from cts.policy import ACTION_LIBRARY, LinearPolicy, feature_vector


@dataclass
class HierarchicalPolicy:
    """
    Two-tier policy architecture.
    Manager sets high-level goals every 4 weeks.
    Worker executes weekly actions conditioned on the goal.
    """
    manager: LinearPolicy
    worker: Dict[ManagerGoal, LinearPolicy]

    def select_action(
        self, 
        state: TrialState, 
        config: TrialConfig, 
        rng: random.Random,
        current_goal: Optional[ManagerGoal] = None,
        stochastic: bool = True,
        history_buffer: Optional[Any] = None,
        tcn_encoder: Optional[Any] = None,
    ) -> Action:
        """Worker selects an action based on the current Manager goal.
        If current_goal is not provided, the manager selects it automatically.
        If history_buffer and tcn_encoder are provided, uses TCN embedding.
        """
        if current_goal is None:
            current_goal = self.select_goal(state, config, rng=rng, stochastic=stochastic, history_buffer=history_buffer, tcn_encoder=tcn_encoder)
        policy = self.worker.get(current_goal)
        if not policy:
            # Fallback to a default policy if goal not found
            policy = list(self.worker.values())[0]
            
        features = feature_vector(state, config)
        if history_buffer and tcn_encoder:
            try:
                history_buffer.add(features)
                tensor = history_buffer.get_padded_tensor()
                out = tcn_encoder(tensor)
                features = out.tolist()[0]
            except Exception:
                pass # Fallback to base features

        index = policy.select_index(features, rng, stochastic=stochastic)
        template = ACTION_LIBRARY[index]
        return Action(type=template.action_type, magnitude=template.magnitude)

    def select_goal(
        self, 
        state: TrialState, 
        config: TrialConfig, 
        rng: random.Random, 
        stochastic: bool = True,
        history_buffer: Optional[Any] = None,
        tcn_encoder: Optional[Any] = None,
    ) -> ManagerGoal:
        """Manager selects a new goal."""
        features = feature_vector(state, config)
        if history_buffer and tcn_encoder:
            try:
                tensor = history_buffer.get_padded_tensor()
                out = tcn_encoder(tensor)
                features = out.tolist()[0]
            except Exception:
                pass

        # Assuming manager output space maps to ManagerGoal enum indices
        probs = self.manager.probabilities(features)
        
        if not stochastic:
            idx = max(range(len(probs)), key=lambda i: probs[i])
        else:
            threshold = rng.random()
            cumulative = 0.0
            idx = len(probs) - 1
            for i, p in enumerate(probs):
                cumulative += p
                if cumulative >= threshold:
                    idx = i
                    break
        
        return list(ManagerGoal)[idx % len(ManagerGoal)]


def init_hierarchical_policy() -> HierarchicalPolicy:
    """Initializes a zero-weighted hierarchical policy."""
    n_features = 14
    manager = LinearPolicy(weights=[[0.0 for _ in range(n_features)] for _ in ManagerGoal])
    
    workers = {}
    for goal in ManagerGoal:
        workers[goal] = LinearPolicy(weights=[[0.0 for _ in range(n_features)] for _ in ACTION_LIBRARY])
        
    return HierarchicalPolicy(manager=manager, worker=workers)
