"""
Toxicity Regression Head (Layer A)
==================================

A lightweight PyTorch module to predict the likelihood of a serious adverse event 
(SAE) based on patient demographics and drug composition.

This provides a "warm start" for the `OPTIMIZE_SAFETY` worker policy by learning
from real OpenFDA records before the REINFORCE loop begins.
"""

import os
from typing import List, Dict, Tuple, Any, Optional

# We'll import torch gracefully so the whole app doesn't crash if it's missing
try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import DataLoader, TensorDataset
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False
    class nn:
        Module = object

class ToxicityPredictor(nn.Module):
    """
    Predicts the probability of a Serious Adverse Event (SAE).
    Input features (6-dim):
      0: age_norm (age / 100)
      1: sex (1=F, 0=M)
      2: weight_norm (weight / 150)
      3: drug_comp_a (fraction)
      4: drug_comp_b (fraction)
      5: drug_comp_c (fraction)
    """
    def __init__(self, input_dim: int = 6, hidden_dim: int = 32):
        super().__init__()
        if not HAS_TORCH:
            raise ImportError("PyTorch is required to run the ToxicityPredictor.")
            
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, 1),
            nn.Sigmoid()
        )
        
    def forward(self, x: "torch.Tensor") -> "torch.Tensor":
        return self.net(x)

def _extract_features(record: Dict[str, Any]) -> Tuple[List[float], float]:
    """Extract 6-dim feature vector and label from a parsed FDA record."""
    age_norm = record.get("age", 60.0) / 100.0
    sex = 1.0 if record.get("sex") == "F" else 0.0
    weight_norm = record.get("weight", 80.0) / 150.0
    
    # Calculate drug composition fractions for this record
    comp_votes = {"a": 0, "b": 0, "c": 0}
    drugs = record.get("drugs", [])
    
    # Use a generic hash to map real drug names to a/b/c components
    for drug in drugs:
        name = drug.get("name", "").lower()
        if name:
            hash_val = sum(ord(c) for c in name) % 3
            comp_idx = ["a", "b", "c"][hash_val]
            comp_votes[comp_idx] += 1
            
    total_votes = sum(comp_votes.values()) or 1
    comp_a = comp_votes["a"] / total_votes
    comp_b = comp_votes["b"] / total_votes
    comp_c = comp_votes["c"] / total_votes
    
    features = [age_norm, sex, weight_norm, comp_a, comp_b, comp_c]
    label = 1.0 if record.get("is_serious", False) else 0.0
    
    return features, label

def pretrain_toxicity_head(fda_records: List[Dict[str, Any]], epochs: int = 20, batch_size: int = 32) -> Tuple[Optional["ToxicityPredictor"], List[float]]:
    """
    Trains the ToxicityPredictor on fetched OpenFDA records.
    Returns (trained_model, loss_history).
    """
    if not HAS_TORCH:
        print("[ToxicityHead] PyTorch not found. Skipping pre-training.")
        return None, []
        
    print(f"\n[ToxicityHead] Preparing {len(fda_records)} FDA records for pre-training...")
    X, y = [], []
    for rec in fda_records:
        feats, label = _extract_features(rec)
        X.append(feats)
        y.append([label])
        
    if not X:
        print("[ToxicityHead] No valid records for pre-training.")
        return None, []
        
    X_t = torch.tensor(X, dtype=torch.float32)
    y_t = torch.tensor(y, dtype=torch.float32)
    
    dataset = TensorDataset(X_t, y_t)
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
    
    model = ToxicityPredictor()
    criterion = nn.BCELoss()
    optimizer = optim.Adam(model.parameters(), lr=0.005)
    
    loss_history = []
    
    print("[ToxicityHead] Starting pre-training (Toxicity Regression Head)...")
    for ep in range(epochs):
        model.train()
        total_loss = 0.0
        for batch_X, batch_y in dataloader:
            optimizer.zero_grad()
            preds = model(batch_X)
            loss = criterion(preds, batch_y)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
            
        avg_loss = total_loss / len(dataloader)
        loss_history.append(avg_loss)
        if (ep + 1) % 5 == 0 or ep == 0:
            print(f"  Epoch {ep+1:02d}/{epochs} | Loss: {avg_loss:.4f}")
            
    print("[ToxicityHead] Pre-training complete.")
    return model, loss_history
