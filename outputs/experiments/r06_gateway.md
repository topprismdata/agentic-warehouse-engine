# R06 — Execution Gateway stub (Todo #12): the §15.4 boundary

**Date**: 2026-08-16T09:52:19.642082+00:00 | seed = 42 | dry-run only (no WMS, no writes)

## What the gateway enforces (check chain, fail-fast)

| # | Check | Spec anchor | Reason code |
|---|-------|-------------|-------------|
| 1 | plan is solver-verified | §14.2 | SOLVER_STATUS_NOT_FEASIBLE |
| 2 | constraint_version fresh | §15.4 | CONSTRAINT_VERSION_MISMATCH |
| 3 | location capacity (whole plan) | §10.4 | CAPACITY_VIOLATION |
| 4 | risk routing: low→auto, medium→approve, high→sim+human, safety→blocked | §15.2 | RISK_HIGH_REQUIRES_SIM_AND_APPROVAL / SAFETY_CRITICAL_BLOCKED_FOR_LLM |
| 5 | MOVE payback: saving > move_cost | §3.3 | NEGATIVE_PAYBACK |

## Test matrix results

| Test | Verdict | accepted/rejected | rejection codes |
|------|---------|-------------------|-----------------|
| T1 good plan ≤5 acts → auto | PASS | 5 / 0 | — |
| T2 verifier_status=timeout | PASS | 0 / 1 | {'SOLVER_STATUS_NOT_FEASIBLE': 1} |
| T3 stale constraint_version | PASS | 0 / 1 | {'CONSTRAINT_VERSION_MISMATCH': 1} |
| T4 capacity violation | PASS | 0 / 1 | {'CAPACITY_VIOLATION': 1} |
| T5 safety_critical plan | PASS | 0 / 1 | {'SAFETY_CRITICAL_BLOCKED_FOR_LLM': 1} |
| T6 MOVE saving<cost | PASS | 0 / 3 | {'NEGATIVE_PAYBACK': 3} |
| T7 >5 actions => HIGH risk | PASS | 120 / 0 | — |
| T8 plan MEDIUM → approve | PASS | 5 / 0 | — |

All 8 verdicts correct: **PASS**

## Audit trail sample (§15.4 mandated provenance per task)

```json
{'task_id': 'T-DP-SMALL-GOOD-0000', 'decision_id': 'DP-SMALL-GOOD', 'model_version': 'B4_CPSAT@v0.3', 'constraint_version': 'v0.1.0', 'expected_value': 0.0, 'approved_by': None}
```

## Honest scope notes
- **dry_run only**: no WMS adapter, no task dispatch, no DB writes. The stub's job
  is the CONTRACT + rejection codes + audit row — execution plumbing is v0.4.
- expected_saving for initial ASSIGN is 0.0 by convention (value flows via L0/L1
  NormalizedCost, not per-action); per-action saving estimation belongs to the
  Learned Cost Model (spec §13.3), wired in v0.3+.
- The good B4 plan (120 ASSIGN actions) is deliberately routed HIGH risk by the
  >5-actions rule (spec §15.2 "large-scale re-slot needs approval") — correct
  behavior, not a bug: nothing here auto-executes at scale.
- validate_pipeline (non-vacuous, 120 assignments + 1 plan): hard-fails = **0**
