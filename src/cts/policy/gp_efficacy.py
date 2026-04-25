"""
Gaussian Process Efficacy Surface
=================================

Models the clinical efficacy of a drug dose as a smooth surface with uncertainty.
Uses HuggingFace patient reviews (star ratings) to calibrate a GP kernel,
providing the simulator with a realistic efficacy curve instead of a flat scalar.
"""

from typing import List, Tuple, Optional

try:
    import torch
    # For a lightweight GP without heavy dependencies like GPyTorch,
    # we implement a simple exact GP inference using PyTorch primitives.
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

class GPEfficacySurface:
    """
    1D Gaussian Process regression for Efficacy = f(Dose).
    Uses a Matérn 5/2 kernel which is standard for modelling physical/clinical processes.
    """
    def __init__(self, lengthscale: float = 1.0, variance: float = 1.0, noise: float = 0.1):
        if not HAS_TORCH:
            raise ImportError("PyTorch required for GPEfficacySurface.")
            
        self.lengthscale = lengthscale
        self.variance = variance
        self.noise = noise
        
        # Training data
        self.X_train: Optional["torch.Tensor"] = None
        self.y_train: Optional["torch.Tensor"] = None
        
        # Precomputed components
        self.L: Optional["torch.Tensor"] = None
        self.alpha: Optional["torch.Tensor"] = None
        
    def _matern52_kernel(self, x1: "torch.Tensor", x2: "torch.Tensor") -> "torch.Tensor":
        """
        Matérn 5/2 kernel function.
        """
        # Distance matrix
        dist = torch.cdist(x1, x2, p=2)
        scaled_dist = 2.2360679775 * dist / self.lengthscale  # sqrt(5) ≈ 2.236
        
        # Kernel computation
        k = self.variance * (1.0 + scaled_dist + (scaled_dist**2) / 3.0) * torch.exp(-scaled_dist)
        return k
        
    def fit(self, X: List[float], y: List[float]) -> None:
        """
        Fit the GP to observed dose-response data.
        X: List of doses (e.g. 0.0 to 1.0)
        y: List of observed efficacies (e.g. from HF star ratings normalized to 0-1)
        """
        if not HAS_TORCH or not X:
            return
            
        self.X_train = torch.tensor(X, dtype=torch.float32).view(-1, 1)
        self.y_train = torch.tensor(y, dtype=torch.float32).view(-1, 1)
        
        # Compute K(X, X)
        K = self._matern52_kernel(self.X_train, self.X_train)
        
        # Add noise variance to diagonal
        K += self.noise * torch.eye(K.size(0))
        
        # Cholesky decomposition for numerical stability
        try:
            self.L = torch.linalg.cholesky(K)
            # Compute alpha = K^-1 y
            # L * L^T * alpha = y  =>  L * z = y, L^T * alpha = z
            z = torch.linalg.solve_triangular(self.L, self.y_train, upper=False)
            self.alpha = torch.linalg.solve_triangular(self.L.T, z, upper=True)
        except RuntimeError:
            # Fallback if matrix is singular
            self.L = None
            self.alpha = None
            
    def predict(self, X_test: List[float]) -> Tuple[List[float], List[float]]:
        """
        Predict mean and standard deviation of efficacy for given doses.
        """
        if not HAS_TORCH or self.X_train is None or self.alpha is None:
            # Fallback if not fitted
            return [0.5 for _ in X_test], [0.1 for _ in X_test]
            
        x_t = torch.tensor(X_test, dtype=torch.float32).view(-1, 1)
        
        # K(X_test, X_train)
        K_star = self._matern52_kernel(x_t, self.X_train)
        
        # Mean = K_star * alpha
        mean = torch.matmul(K_star, self.alpha).squeeze(-1)
        
        # Variance = K(X_test, X_test) - K_star * K^-1 * K_star^T
        K_star_star = self._matern52_kernel(x_t, x_t)
        v = torch.linalg.solve_triangular(self.L, K_star.T, upper=False)
        variance = K_star_star - torch.matmul(v.T, v)
        std_dev = torch.sqrt(torch.diag(variance).clamp(min=1e-6))
        
        return mean.tolist(), std_dev.tolist()
