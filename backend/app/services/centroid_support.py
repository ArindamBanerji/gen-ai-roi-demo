"""
app/services/centroid_support.py -- Block 3.6 Centroid Support Monitoring.

Flags when a centroid has moved outside its data support region --
i.e., the system is making decisions on factor combinations it has
never observed.  Makes the conservation law story concrete in Tab 2.

Design: warn-only, never blocks decisions.
"""

import numpy as np


def compute_centroid_support(
    mu: np.ndarray,
    mu_zero: np.ndarray,
    sigma_per_factor: list,
    threshold_sigma: float = 2.0,
) -> dict:
    """
    Check whether live centroids have moved outside their data support region.

    A centroid is "outside support" when its distance from mu_zero exceeds
    threshold_sigma x sigma_per_factor for any factor dimension.

    Parameters
    ----------
    mu               : np.ndarray, shape [C, A, D] -- live centroid tensor
    mu_zero          : np.ndarray, shape [C, A, D] -- bootstrap baseline
    sigma_per_factor : list[float], len D -- per-factor sigma values
    threshold_sigma  : float (default 2.0) -- number of sigmas for boundary

    Returns
    -------
    dict mapping (c_idx, a_idx) -> {
        "n_factors_outside"    : int,
        "factors_outside"      : list[int],
        "max_deviation_sigma"  : float,
        "support_status"       : "ok" | "warning",
    }
    """
    C, A, D = mu.shape
    sigma_arr = np.array(sigma_per_factor, dtype=np.float64)
    thresholds = threshold_sigma * sigma_arr  # shape [D]
    result: dict = {}

    for c in range(C):
        for a in range(A):
            deviation = np.abs(mu[c, a, :] - mu_zero[c, a, :])
            outside = deviation > thresholds
            n_outside = int(np.sum(outside))
            result[(c, a)] = {
                "n_factors_outside":   n_outside,
                "factors_outside":     [int(i) for i, o in enumerate(outside) if o],
                "max_deviation_sigma": float(
                    np.max(deviation / (thresholds + 1e-9))
                ),
                "support_status": "warning" if n_outside >= 2 else "ok",
            }

    return result
