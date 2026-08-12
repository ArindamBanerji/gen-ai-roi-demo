"""
Bootstrap Decision node writer (CORR-3).

After bootstrap_calibration() calibrates ProfileScorer centroids, this module
writes representative Decision nodes to AGE so that GATE-R, similar-cases
retrieval, and IKS v2 can access bootstrap history.

Design:
  - Generates sum(decisions_per_category.values()) Decision nodes total,
    round-robining through actions within each category.
  - factor_vector = centroid + small noise (sigma=0.02, seed=42), clipped [0,1].
    Stored as a native Python list -> AGE native array (NOT json.dumps string).
  - source='bootstrap' distinguishes these from live triage decisions.
  - No [:DECIDED_ON] relationship (bootstrap uses synthetic, not real, alerts).
  - Idempotent: skipped when any bootstrap Decision nodes already exist in AGE.

This is migration/seed infrastructure, not a live decision path. The writer
accepts the shared AGE client resolved by ``GraphConfig.load("soc")`` and uses
its governed ``run_query`` interface; it does not construct a legacy AGE
client or bypass the shared AGE graph.

Reference: docs/soc_copilot_design_v1.md Sec.14 (CORR-3).
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List

from app.domains.soc.factor_vector import validated_factor_vector

import numpy as np

log = logging.getLogger(__name__)

_BOOTSTRAP_SIGMA = 0.02   # centroid noise: tight enough to stay near centroid
_BOOTSTRAP_SEED  = 42     # reproducible -- same seed as bootstrap_calibration


def _apply_weights(
    total: int,
    categories: List[str],
    weights: Dict[str, float],
) -> Dict[str, int]:
    """
    Redistribute *total* decisions across *categories* using fractional weights.

    rounds each weight x total to the nearest integer, then adjusts the largest
    category by +/-1 so the result sums exactly to *total*.

    Parameters
    ----------
    total      : target total decision count
    categories : ordered category list
    weights    : {category: fraction} -- must contain all categories; need not sum to 1.0
                 (re-normalised internally)

    Returns
    -------
    {category: count}
    """
    total_weight = sum(weights.get(c, 0.0) for c in categories) or 1.0
    result: Dict[str, int] = {}
    distributed = 0
    for cat in categories:
        w = weights.get(cat, 0.0) / total_weight
        n = round(total * w)
        result[cat] = n
        distributed += n

    # Absorb any ±1-2 rounding discrepancy in the largest-weight category
    diff = total - distributed
    if diff != 0:
        largest = max(categories, key=lambda c: weights.get(c, 0.0))
        result[largest] += diff

    return result


def build_bootstrap_decisions(
    scorer,                              # ProfileScorer with calibrated mu
    categories: List[str],
    decisions_per_category: Dict[str, int],
    seed: int = _BOOTSTRAP_SEED,
    weights: Dict[str, float] | None = None,    # optional: recompute distribution from weights
) -> List[Dict[str, Any]]:
    """
    Build Decision record dicts representing bootstrap calibration decisions.

    Returns a list of dicts ready for batch UNWIND insertion.  Each dict
    contains all scalar fields; factor_vector is a Python list (not a JSON
    string), which the AGE Python driver stores as a native array.

    Parameters
    ----------
    scorer                 : ProfileScorer with calibrated centroids (mu).
    categories             : Ordered category list (matches mu axis 0).
    decisions_per_category : {category: count} from BootstrapResult.
    seed                   : RNG seed for reproducible factor vectors.
    weights                : optional {category: fraction} -- when provided,
                             recomputes N_per_category using non-uniform weights
                             (BOOTSTRAP_CATEGORY_WEIGHTS) so the distribution
                             reflects realistic SOC alert frequency rather than
                             equal-per-category allocation.  The total number of
                             decisions is preserved.

    Returns
    -------
    List of dicts with keys:
      id, action, confidence, factor_vector, centroid_snapshot,
      category, source
    """
    # Phase 9: when weights provided, redistribute using non-uniform allocation
    if weights is not None:
        total = sum(decisions_per_category.values())
        decisions_per_category = _apply_weights(total, categories, weights)
        log.debug(
            "[BOOTSTRAP-GRAPH] Weighted distribution applied: %s",
            decisions_per_category,
        )

    rng      = np.random.default_rng(seed)
    actions  = scorer.actions
    n_actions = len(actions)
    records: List[Dict[str, Any]] = []

    for cat_idx, category in enumerate(categories):
        n = decisions_per_category.get(category, 0)
        for i in range(n):
            action_idx  = i % n_actions
            action_name = actions[action_idx]
            centroid    = scorer.centroids[cat_idx, action_idx]  # shape (n_factors,)

            # Add small noise so records aren't all identical centroids;
            # clip to [0.0, 1.0] — factor values are bounded probabilities.
            fv_arr = (
                centroid + rng.normal(0.0, _BOOTSTRAP_SIGMA, len(centroid))
            ).clip(0.0, 1.0)
            fv = fv_arr.tolist()  # native Python list -- NOT json.dumps()

            score_result = scorer.score(fv_arr, category_index=cat_idx)

            records.append({
                "id":               str(uuid.uuid4()),
                "action":           action_name,
                "confidence":       float(score_result.confidence),
                "factor_vector":    validated_factor_vector(fv),
                "centroid_snapshot": centroid.tolist(),  # native list for AGE
                "category":         category,
                "source":           "bootstrap",
                "domain":           "soc",
            })

    return records


async def write_bootstrap_decisions(
    age_client,
    scorer,
    categories: List[str],
    decisions_per_category: Dict[str, int],
) -> int:
    """
    Write bootstrap Decision nodes to the shared SOC AGE graph via UNWIND batch.

    ``age_client`` must be the shared AGE client created from
    ``GraphConfig.load("soc")``. This direct batch is the documented
    migration-equivalent governed path for synthetic bootstrap records; live
    decisions use the GraphStore governed writer.

    Idempotent: skipped if any Decision node with source='bootstrap' already
    exists, preventing duplicate writes on repeated cold-starts.

    Parameters
    ----------
    age_client             : GraphConfig-resolved shared AGE client.
    scorer                 : ProfileScorer with calibrated centroids.
    categories             : Ordered category list.
    decisions_per_category : {category: count} from BootstrapResult.

    Returns
    -------
    int  Number of Decision nodes written (0 if skipped).
    """
    # Idempotency guard: skip if bootstrap nodes already exist
    check = await age_client.run_query(
        "MATCH (d:Decision {source: 'bootstrap'}) "
        "WHERE d.domain = 'soc' RETURN count(d) AS cnt"
    )
    existing = check[0]["cnt"] if check else 0
    if existing > 0:
        log.info(
            "[BOOTSTRAP-GRAPH] Skipping -- %d bootstrap Decision nodes already exist",
            existing,
        )
        print(f"[BOOTSTRAP-GRAPH] Skipping -- {existing} bootstrap Decision nodes already exist")
        return 0

    records = build_bootstrap_decisions(scorer, categories, decisions_per_category)
    if not records:
        log.info("[BOOTSTRAP-GRAPH] No decisions to write (empty pool)")
        return 0

    # UNWIND batch: factor_vector passed as Python list → native AGE array.
    # No [:DECIDED_ON] relationship — bootstrap uses synthetic, not real, alerts.
    # ARCHITECTURAL NOTE: Bootstrap uses direct AGE client write
    # (not GraphStore) because it seeds initial data before the
    # scorer/store lifecycle begins. Domain='soc' stamped.
    # Governed by GraphConfig-resolved AGE client injection.
    await age_client.run_query(
        """
        UNWIND $decisions AS dec
        CREATE (d:Decision {
            id:               dec.id,
            action:           dec.action,
            confidence:       dec.confidence,
            factor_vector:    dec.factor_vector,
            centroid_snapshot: dec.centroid_snapshot,
            category:         dec.category,
            source:           dec.source,
             domain:           dec.domain,
            timestamp_epoch:  $timestamp_epoch,
            auto_approved:    false,
            shadow_mode:      false,
            outcome:          null
        })
        """,
        {"decisions": records, "timestamp_epoch": int(datetime.utcnow().timestamp() * 1000)},
    )

    n = len(records)
    log.info(
        "[BOOTSTRAP-GRAPH] Wrote %d bootstrap Decision nodes "
        "(%d categories, %d actions, factor_vector=native list)",
        n, len(categories), len(scorer.actions),
    )
    print(
        f"[BOOTSTRAP-GRAPH] Wrote {n} bootstrap Decision nodes "
        f"(source='bootstrap', factor_vector=native list)"
    )
    return n
