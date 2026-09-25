# SOC Conservation Population Gap

## Conservation query requirements

`LearningHealthMonitor` obtains SOC conservation population statistics from
verified `Decision` nodes. The query requires all of the following:

- SOC domain scoping;
- `verified_at_epoch IS NOT NULL`;
- a non-null `status` or `outcome`;
- a canonical SOC category in the configured category set.

The query then counts verified decisions, correct outcomes, overrides, and
categories with data. Those values drive the coverage-derived alpha, verified
accuracy `q`, and conservation signal.

## SDK outcome-writer behavior

The SDK outcome writer persists the outcome and related decision metadata, but
the current shared writer does not populate `verified_at_epoch` as part of its
canonical outcome contract. SOC's route-level outcome path supplies
`verified_at_epoch` when it writes directly, while SDK-originated outcome
writes can omit it.

## Gap

The general verified-count population and the conservation population are not
necessarily the same set. A decision can be counted by a general verified
metric yet be excluded from conservation because `verified_at_epoch` is
missing, its status/outcome field is absent, or its category is not canonical.
This can make conservation coverage appear lower than the broader verified
count and can leave alpha unavailable or conservative.

## Recommended fix path

Align the shared SDK outcome writer with the conservation contract:

1. Populate `verified_at_epoch` on every accepted verified outcome.
2. Preserve the canonical category and outcome/status fields in the same
   write transaction.
3. Add an SDK-level migration/backfill policy for historical verified
   decisions where provenance is sufficient; otherwise leave them explicitly
   unqualified.
4. Add cross-repository contract tests comparing the general verified count
   with the conservation query population.

This Stage SOC-GATE-FIX documents the discrepancy only. The SDK writer is out
of scope and remains unchanged.
