"""
Temporal Convolutional Network (TCN) Encoder
============================================

This module provides a PyTorch-based TCN to encode a history of trial states
into a single summary vector. It captures the temporal dynamics of the trial
(e.g., delayed adverse events, patient recruitment momentum).
"""

from typing import List

try:
    import torch
    import torch.nn as nn
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False
    class nn:
        Module = object

class TCNHistoryEncoder(nn.Module):
    """
    1D Convolutional network over a sequence of state feature vectors.
    """
    def __init__(self, input_features: int = 11, out_features: int = 11):
        super().__init__()
        if not HAS_TORCH:
            raise ImportError("PyTorch is required for TCNHistoryEncoder.")
            
        # 1D Conv expects input shape: (batch_size, channels, sequence_length)
        # We treat input_features as channels.
        self.conv_layers = nn.Sequential(
            nn.Conv1d(in_channels=input_features, out_channels=32, kernel_size=3, padding=1, dilation=1),
            nn.ReLU(),
            nn.Conv1d(in_channels=32, out_channels=32, kernel_size=3, padding=2, dilation=2),
            nn.ReLU(),
            nn.Conv1d(in_channels=32, out_channels=32, kernel_size=3, padding=4, dilation=4),
            nn.ReLU()
        )
        
        self.pool = nn.AdaptiveMaxPool1d(1)
        self.fc = nn.Linear(32, out_features)
        
    def forward(self, x: "torch.Tensor") -> "torch.Tensor":
        """
        x shape: (batch_size, sequence_length, input_features)
        Returns: (batch_size, out_features)
        """
        # Conv1d expects (batch_size, in_channels, sequence_length)
        x = x.transpose(1, 2)
        
        # Pass through TCN
        x = self.conv_layers(x)
        
        # Global max pooling over time
        x = self.pool(x).squeeze(-1)
        
        # Final projection
        return self.fc(x)

class StateHistoryBuffer:
    """
    Maintains a rolling window of state feature vectors.
    """
    def __init__(self, window_size: int = 4, feature_dim: int = 11):
        self.window_size = window_size
        self.feature_dim = feature_dim
        self.buffer: List[List[float]] = []
        
    def add(self, feature_vector: List[float]):
        self.buffer.append(feature_vector)
        if len(self.buffer) > self.window_size:
            self.buffer.pop(0)
            
    def get_padded_tensor(self) -> "torch.Tensor":
        """
        Returns a tensor of shape (1, window_size, feature_dim).
        Zero-pads the beginning if the buffer is not full.
        """
        if not HAS_TORCH:
            raise ImportError("PyTorch is required.")
            
        padded = []
        pad_len = self.window_size - len(self.buffer)
        
        for _ in range(pad_len):
            padded.append([0.0] * self.feature_dim)
            
        padded.extend(self.buffer)
        return torch.tensor([padded], dtype=torch.float32)
