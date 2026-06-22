"""
GATE-R: Routing Accuracy Measurement.

Measures what fraction of alerts route to the correct category through the
full pipeline: alert_type -> resolve_alert_category() -> category_index ->
correct centroid slice mu[c,:,:].

GATE-R is the gate that enables the composite accuracy claim:
  composite_accuracy = routing_accuracy x scoring_accuracy
  If routing is 100%, composite equals scoring accuracy.

Tests:
  test_gate_r_resolve_correctness       -- resolve_alert_category matches ground truth
  test_gate_r_map_coverage              -- all pool alert_types in ALERT_TYPE_CATEGORY_MAP
  test_gate_r_category_index_consistency-- category_index valid and round-trips via SOC_CATEGORIES
  test_gate_r_no_default_fallback       -- no alert routes via DEFAULT_CATEGORY fallback
  test_gate_r_all_categories_represented-- all 6 SOC categories have at least one alert
  test_gate_r_end_to_end_scoring_path   -- alert_type -> category -> index -> ProfileScorer.score()
"""

import pytest
import numpy as np

from app.data.alert_pool import get_alert_pool
from app.domains.soc.config import (
    ALERT_TYPE_CATEGORY_MAP,
    DEFAULT_CATEGORY,
    SOC_CATEGORIES,
    SOCDomainConfig,
    resolve_alert_category,
)


# ---------------------------------------------------------------------------
# Module-level pool (loaded once)
# ---------------------------------------------------------------------------

_POOL = get_alert_pool()


# ---------------------------------------------------------------------------
# Test 1 — resolve_alert_category matches pool ground truth for every alert
# ---------------------------------------------------------------------------

def test_gate_r_resolve_correctness():
    """
    For every alert in the pool, resolve_alert_category(alert_type) must
    return the same category stored in alert["category"] (the ground truth).

    This measures routing accuracy end-to-end.
    """
    mismatches = []

    for alert in _POOL:
        alert_type = alert.get("alert_type", "")
        ground_truth = alert.get("category", "")
        predicted = resolve_alert_category(alert_type)

        if predicted != ground_truth:
            mismatches.append(
                f"  alert_id={alert.get('alert_id') or alert.get('id')!r}  "
                f"alert_type={alert_type!r}  "
                f"predicted={predicted!r}  ground_truth={ground_truth!r}"
            )

    n_total   = len(_POOL)
    n_correct = n_total - len(mismatches)
    accuracy  = n_correct / n_total if n_total else 0.0

    # Print GATE-R summary regardless of pass/fail
    print()
    print("=== GATE-R RESULTS ===")
    print(f"Routing accuracy: {n_correct}/{n_total} = {accuracy:.1%}")
    if mismatches:
        print("MISMATCHES:")
        for m in mismatches:
            print(m)

    if accuracy == 1.0:
        print("GATE-R: PASS")
        print("Composite accuracy = routing(100%) x scoring(97.89%) = 97.89%")
        print("No routing degradation.")
    else:
        composite = accuracy * 0.9789
        print(f"GATE-R: CONDITIONAL PASS")
        print(f"Composite accuracy = routing({accuracy:.1%}) x scoring(97.89%) = {composite:.1%}")
        print(f"Routing errors degrade composite by {(1 - accuracy) * 100:.1f}pp")

    assert not mismatches, (
        f"Routing accuracy {accuracy:.1%}: {len(mismatches)} mismatch(es):\n"
        + "\n".join(mismatches)
    )


# ---------------------------------------------------------------------------
# Test 2 — all pool alert_types are in ALERT_TYPE_CATEGORY_MAP
# ---------------------------------------------------------------------------

def test_gate_r_map_coverage():
    """
    Every alert_type in the pool must have an explicit entry in
    ALERT_TYPE_CATEGORY_MAP. Unlisted types fall back to DEFAULT_CATEGORY
    and degrade routing accuracy silently.
    """
    uncovered = []

    for alert in _POOL:
        alert_type = alert.get("alert_type", "")
        if alert_type not in ALERT_TYPE_CATEGORY_MAP:
            uncovered.append(alert_type)

    unique_uncovered = sorted(set(uncovered))
    n_total   = len({a.get("alert_type") for a in _POOL})
    n_covered = n_total - len(unique_uncovered)

    print()
    print(f"Map coverage: {n_covered}/{n_total} unique alert_types covered")
    if unique_uncovered:
        print(f"Uncovered alert_types: {unique_uncovered}")

    assert not unique_uncovered, (
        f"alert_types in pool but NOT in ALERT_TYPE_CATEGORY_MAP: {unique_uncovered}"
    )


# ---------------------------------------------------------------------------
# Test 3 — category_index is valid and round-trips via SOC_CATEGORIES
# ---------------------------------------------------------------------------

def test_gate_r_category_index_consistency():
    """
    For every pool alert, the category resolved from its alert_type must
    have a valid index (0 <= idx < len(SOC_CATEGORIES)) and
    SOC_CATEGORIES[idx] must equal the resolved category.
    """
    cfg      = SOCDomainConfig()
    n_cats   = len(SOC_CATEGORIES)
    failures = []

    for alert in _POOL:
        alert_type = alert.get("alert_type", "")
        category   = resolve_alert_category(alert_type)

        try:
            idx = cfg.get_category_index(category)
        except ValueError as exc:
            failures.append(f"  {alert_type!r} -> {category!r}: get_category_index raised {exc}")
            continue

        if not (0 <= idx < n_cats):
            failures.append(
                f"  {alert_type!r} -> {category!r}: index {idx} out of range [0, {n_cats})"
            )
        elif SOC_CATEGORIES[idx] != category:
            failures.append(
                f"  {alert_type!r} -> {category!r}: "
                f"SOC_CATEGORIES[{idx}]={SOC_CATEGORIES[idx]!r} != {category!r}"
            )

    assert not failures, (
        "Category index consistency failures:\n" + "\n".join(failures)
    )


# ---------------------------------------------------------------------------
# Test 4 — no alert routes via DEFAULT_CATEGORY fallback
# ---------------------------------------------------------------------------

def test_gate_r_no_default_fallback():
    """
    No alert in the pool should route via the DEFAULT_CATEGORY fallback.
    An alert uses the fallback when its alert_type is not in
    ALERT_TYPE_CATEGORY_MAP, meaning the routing is accidental (it happens
    to be correct only if ground_truth == DEFAULT_CATEGORY).
    """
    fallback_alerts = []

    for alert in _POOL:
        alert_type = alert.get("alert_type", "")
        if alert_type not in ALERT_TYPE_CATEGORY_MAP:
            predicted = resolve_alert_category(alert_type)  # will log ERROR + return DEFAULT
            fallback_alerts.append(
                f"  alert_type={alert_type!r}  fallback={predicted!r}  "
                f"ground_truth={alert.get('category')!r}"
            )

    n_fallback = len(fallback_alerts)
    print()
    print(f"Default fallback used: {n_fallback} times")
    if fallback_alerts:
        for f in fallback_alerts:
            print(f)

    assert not fallback_alerts, (
        f"{n_fallback} alert(s) route via DEFAULT_CATEGORY fallback "
        f"(add them to ALERT_TYPE_CATEGORY_MAP):\n" + "\n".join(fallback_alerts)
    )


# ---------------------------------------------------------------------------
# Test 5 — all 6 SOC categories are represented in the pool
# ---------------------------------------------------------------------------

def test_gate_r_all_categories_represented():
    """
    After routing, all 6 SOC categories must have at least one alert routing
    to them. A missing category would mean its centroid slice is never exercised.
    """
    categories_seen = set()

    for alert in _POOL:
        alert_type = alert.get("alert_type", "")
        categories_seen.add(resolve_alert_category(alert_type))

    missing = set(SOC_CATEGORIES) - categories_seen
    extra   = categories_seen - set(SOC_CATEGORIES)

    print()
    print(f"Categories covered: {len(categories_seen)}/6 -> {sorted(categories_seen)}")
    if missing:
        print(f"Missing categories: {sorted(missing)}")

    assert not missing, (
        f"Pool has no alerts routing to: {sorted(missing)}. "
        f"Add pool entries for these categories."
    )
    assert not extra, (
        f"Alerts route to unknown categories: {sorted(extra)}"
    )


# ---------------------------------------------------------------------------
# Test 6 — end-to-end scoring path: alert_type → category → index → score
# ---------------------------------------------------------------------------

def test_gate_r_end_to_end_scoring_path():
    """
    For one alert from each unique category, verify the full pipeline:
      alert_type -> resolve_alert_category() -> get_category_index()
                 -> ProfileScorer.score() returns a valid ScoringResult.

    Uses a dummy factor vector [0.5]*6; this tests routing plumbing, not scoring.
    """
    scorer = SOCDomainConfig().build_profile_scorer()
    cfg    = SOCDomainConfig()
    f_dummy = np.array([0.5] * 6, dtype=np.float64)

    # Pick one alert per unique (resolved) category
    seen_categories: set = set()
    sampled = []
    for alert in _POOL:
        cat = resolve_alert_category(alert.get("alert_type", ""))
        if cat not in seen_categories:
            seen_categories.add(cat)
            sampled.append(alert)

    assert len(sampled) >= 6, (
        f"Expected at least 6 sampled alerts (one per category), got {len(sampled)}"
    )

    failures = []
    for alert in sampled:
        alert_type = alert.get("alert_type", "")
        category   = resolve_alert_category(alert_type)
        try:
            cat_idx = cfg.get_category_index(category)
        except ValueError as exc:
            failures.append(f"  {alert_type!r}: get_category_index raised {exc}")
            continue

        result = scorer.score(f_dummy, category_index=cat_idx)

        if result is None:
            failures.append(f"  {alert_type!r}: scorer.score() returned None")
            continue
        if not (0 <= result.action_index < 5):
            failures.append(
                f"  {alert_type!r}: action_index={result.action_index} out of [0,5)"
            )
        if result.confidence <= 0:
            failures.append(
                f"  {alert_type!r}: confidence={result.confidence} must be > 0"
            )

    assert not failures, (
        "End-to-end scoring path failures:\n" + "\n".join(failures)
    )
