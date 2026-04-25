"""
Mixture-of-Experts (MoE) Worker Architecture
============================================

Upgrades the standard LinearPolicy worker to a PyTorch-based MoE model.
Conditions the action selection on both the trial state and the active drug class.
"""

from typing import List, Optional

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False
    class nn:
        Module = object
        
class MoEWorker(nn.Module):
    """
    Mixture-of-Experts policy for action selection.
    Uses a gating network to route inputs to specialized expert networks based
    on the current state and drug class embedding.
    """
    def __init__(self, input_dim: int = 11, num_experts: int = 3, action_dim: int = 10, drug_classes: int = 8):
        super().__init__()
        if not HAS_TORCH:
            raise ImportError("PyTorch required for MoEWorker.")
            
        self.num_experts = num_experts
        
        # Drug class embedding layer
        self.drug_embed = nn.Embedding(drug_classes, 8)
        
        # Total input to routing and experts: state features (11) + drug embedding (8) = 19
        total_in = input_dim + 8
        
        # Gating network
        self.gate = nn.Sequential(
            nn.Linear(total_in, 16),
            nn.ReLU(),
            nn.Linear(16, num_experts)
        )
        
        # Expert networks
        self.experts = nn.ModuleList([
            nn.Sequential(
                nn.Linear(total_in, 32),
                nn.ReLU(),
                nn.Linear(32, action_dim)
            ) for _ in range(num_experts)
        ])
        
    def forward(self, state_features: "torch.Tensor", drug_class_idx: "torch.Tensor") -> "torch.Tensor":
        """
        state_features: (batch, input_dim)
        drug_class_idx: (batch,) integer indices
        Returns: logits of shape (batch, action_dim)
        """
        # Get drug embedding
        d_emb = self.drug_embed(drug_class_idx)
        
        # Combine inputs
        x = torch.cat([state_features, d_emb], dim=1)
        
        # Gating probabilities
        gate_logits = self.gate(x)
        gate_probs = F.softmax(gate_logits, dim=-1)  # (batch, num_experts)
        
        # Expert predictions
        expert_outputs = [expert(x) for expert in self.experts]
        expert_outputs = torch.stack(expert_outputs, dim=1)  # (batch, num_experts, action_dim)
        
        # Weighted sum of experts
        out = torch.einsum('be,bea->ba', gate_probs, expert_outputs)
        
        # We also return gate_probs for dashboard visualization
        return out, gate_probs

    def select_index(self, features: List[float], rng: "random.Random", stochastic: bool = True) -> int:
        """Backward compatibility for HierarchicalPolicy action selection."""
        self.eval()
        with torch.no_grad():
            feat_t = torch.tensor([features], dtype=torch.float32)
            # Default drug class to 0 for simplicity if not provided
            d_idx = torch.tensor([0], dtype=torch.long)
            logits, _ = self(feat_t, d_idx)
            
            if stochastic:
                probs = F.softmax(logits, dim=-1)
                dist = torch.distributions.Categorical(probs)
                return dist.sample().item()
            else:
                return torch.argmax(logits, dim=-1).item()
                
    def get_log_prob(self, features: "torch.Tensor", action_index: int) -> "torch.Tensor":
        """Compute log prob for REINFORCE. features is expected to be a PyTorch tensor (1, feature_dim)."""
        d_idx = torch.tensor([0], dtype=torch.long)
        logits, _ = self(features, d_idx)
        probs = F.softmax(logits, dim=-1)
        dist = torch.distributions.Categorical(probs)
        action_t = torch.tensor([action_index])
        return dist.log_prob(action_t)
