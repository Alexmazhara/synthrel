"""
Vectorized statistical distribution generators for relational data and time offsets.
"""
from typing import Optional
import numpy as np


class DistributionSampler:
    """Fast vectorized random sampling using NumPy."""

    def __init__(self, seed: Optional[int] = 42):
        self.rng = np.random.default_rng(seed)

    def sample_zipf(self, n_items: int, size: int, alpha: float = 1.5) -> np.ndarray:
        """
        Samples indices in range [0, n_items - 1] following a Zipf (power law) distribution.
        Simulates 80/20 Pareto principle: top few items get majority of occurrences.
        """
        # np.random.zipf produces values >= 1
        raw_zipf = self.rng.zipf(a=alpha, size=size)
        # Wrap/clamp into range [0, n_items - 1]
        indices = (raw_zipf - 1) % n_items
        return indices

    def sample_uniform_int(self, low: int, high: int, size: int) -> np.ndarray:
        """Samples uniform integers in range [low, high]."""
        return self.rng.integers(low, high + 1, size=size)

    def sample_choice(self, choices: list, size: int, weights: Optional[list] = None) -> np.ndarray:
        """Weighted or uniform categorical choice."""
        p = None
        if weights is not None:
            total = sum(weights)
            p = [w / total for w in weights]
        return self.rng.choice(choices, size=size, p=p)

    def sample_exponential_offset(
        self,
        size: int,
        scale_seconds: float,
        min_seconds: float = 0,
        max_seconds: float = 86400 * 365,
    ) -> np.ndarray:
        """
        Samples time offsets (in seconds) following an exponential distribution.
        Models natural user waiting times (most events happen quickly, long tail delays).
        """
        raw = self.rng.exponential(scale=scale_seconds, size=size) + min_seconds
        return np.clip(raw, min_seconds, max_seconds).astype(int)

    def sample_normal_offset(
        self,
        size: int,
        mean_seconds: float,
        std_seconds: float,
        min_seconds: float = 0,
        max_seconds: float = 86400 * 365,
    ) -> np.ndarray:
        """
        Samples time offsets (in seconds) following a Gaussian/normal distribution.
        Models delivery times or processing intervals.
        """
        raw = self.rng.normal(loc=mean_seconds, scale=std_seconds, size=size)
        return np.clip(raw, min_seconds, max_seconds).astype(int)
