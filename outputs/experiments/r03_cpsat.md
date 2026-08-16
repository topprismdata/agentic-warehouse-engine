# R03 — B4 CP-SAT joint travel+affinity (Todo #10)

**Date**: 2026-08-16T09:31:59.723180+00:00 | seed = 42 | time_budget = 10.0s
**World**: same as R02 (concentration=0.7), metric = L0 route cost.

## Reference (deterministic)
- B1 Static ABC: 1132.3 → norm 1.0000
- B3 Affinity (greedy): 860.4 → norm 0.7599

## B4 CP-SAT λ sweep
| λ | route cost | NormalizedCost | status | gap | wall time |
|---|-----------|----------------|--------|-----|-----------|
| 0.0 | 690.6 | 0.6099 | OPT | 0.000 | 0.02s |
| 0.5 | 787.9 | 0.6959 | FEAS | 0.126 | 10.00s |
| 1.0 | 835.5 | 0.7379 | FEAS | 0.201 | 10.01s |
| 2.0 | 915.1 | 0.8082 | FEAS | 0.371 | 10.01s |
| 5.0 | 870.1 | 0.7684 | FEAS | 0.594 | 10.01s |

## Best
- **λ* = 0.0, norm = 0.6099** (vs B3 0.7599)

## Gates
- sanity λ=0 ≤ B1 (B4 is optimal assignment, B1 is greedy under same capacity): **PASS** (norm=0.6099023907592243)
- B4 ≤ B3 (solver ≥ greedy clustering): **PASS**
- best solve solver-verified (OPTIMAL or gap ≤ 5%): **PASS**
- solver verification (App C.2 status on every solve): **PASS** (non-feasible aborts run)
- validate_pipeline hard-fails: **0**

## Notes
- Linearization: affinity term uses rank-distance |pos_i − pos_j| scaled to meters
  (spec §12.4 two-stage collapsed; full location-pair quadratic is a v0.3 upgrade).
- **Finding (negative result worth keeping):** under the L0 route metric — which
  counts DISTINCT stops per order — the capacity-constrained optimal freq–dist
  assignment (λ=0) already captures most co-stop benefit implicitly; the explicit
  affinity term pushes on rank-distance, which is MISALIGNED with the route metric
  and makes solutions worse as λ grows. An affinity term only pays off when the
  cost metric cannot see shared stops (per-line cost) or when capacity is tight
  enough that clustering decisions must trade off against frequency.
