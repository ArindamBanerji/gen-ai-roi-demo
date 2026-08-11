"""Strict SOC-facing wrappers around learning calibration helpers."""

from typing import cast

from gae.calibration import compute_theta_min as _gae_compute_theta_min


def compute_theta_min(alpha: float, V: float) -> float:
    """Compute the deployment threshold, rejecting invalid inputs."""
    if alpha <= 0:
        raise ValueError("alpha must be positive")
    if V <= 0:
        raise ValueError("V must be positive")
    return cast(float, _gae_compute_theta_min(alpha, V))
