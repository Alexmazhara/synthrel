"""
Temporal dependency resolver and validator.
Ensures causality: parent_event_time <= child_event_time.
"""
from datetime import datetime
from typing import Optional, Tuple
import numpy as np

from synthrel.core.models import TemporalDependencyConfig
from synthrel.generators.distributions import DistributionSampler


class TemporalEngine:
    """
    Computes dependent timestamps ensuring chronological validity.
    """

    def __init__(self, sampler: DistributionSampler):
        self.sampler = sampler

    def generate_timeline(
        self,
        start_time_iso: str,
        end_time_iso: str,
        size: int,
    ) -> np.ndarray:
        """
        Generates base timestamps sorted chronologically or uniform across time window.
        """
        start = np.datetime64(start_time_iso, "s").astype("int64")
        end = np.datetime64(end_time_iso, "s").astype("int64")
        
        # Uniform timestamps across window
        random_seconds = self.sampler.rng.integers(start, end, size=size)
        random_seconds.sort()
        return random_seconds.astype("datetime64[s]")

    def apply_temporal_offset(
        self,
        parent_timestamps: np.ndarray,
        dep_config: TemporalDependencyConfig,
    ) -> np.ndarray:
        """
        Generates child timestamps strictly respecting parent_timestamps and offset rules.
        """
        size = len(parent_timestamps)
        offset_cfg = dep_config.offset

        if not offset_cfg:
            offsets = np.zeros(size, dtype=int)
        elif offset_cfg.distribution == "exponential":
            scale = offset_cfg.scale_seconds or 3600
            offsets = self.sampler.sample_exponential_offset(
                size=size,
                scale_seconds=scale,
                min_seconds=offset_cfg.min_seconds,
                max_seconds=offset_cfg.max_seconds,
            )
        elif offset_cfg.distribution == "normal":
            mean = offset_cfg.mean_seconds or 86400
            std = offset_cfg.std_seconds or (mean / 3.0)
            offsets = self.sampler.sample_normal_offset(
                size=size,
                mean_seconds=mean,
                std_seconds=std,
                min_seconds=offset_cfg.min_seconds,
                max_seconds=offset_cfg.max_seconds,
            )
        else:
            offsets = self.sampler.sample_uniform_int(
                low=offset_cfg.min_seconds,
                high=offset_cfg.max_seconds,
                size=size,
            )

        # Convert parent timestamps to seconds if necessary
        parent_secs = parent_timestamps.astype("datetime64[s]").astype("int64")
        child_secs = parent_secs + offsets
        return child_secs.astype("datetime64[s]")

    @staticmethod
    def validate_temporal_integrity(
        parent_timestamps: np.ndarray,
        child_timestamps: np.ndarray,
    ) -> Tuple[bool, int]:
        """
        Verifies that parent_time <= child_time holds for 100% of rows.
        Returns: (is_valid, violation_count)
        """
        violations = np.sum(child_timestamps < parent_timestamps)
        return bool(violations == 0), int(violations)
