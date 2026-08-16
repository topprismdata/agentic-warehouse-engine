# R03 — B4 CP-SAT joint travel+affinity (Todo #10)

**Date**: 2026-08-16T09:46:11.354167+00:00 | seed = 42 | time_budget = 10.0s
**World**: same as R02 (concentration=0.7), metric = L0 route cost.

## Reference (deterministic)
- B1 Static ABC: 18842.5 → norm 1.0000
- B3 Affinity (greedy): 14683.2 → norm 0.7793

## B4 CP-SAT λ sweep
| λ | route cost | NormalizedCost | status | gap | wall time |
|---|-----------|----------------|--------|-----|-----------|
| 0.0 | 12512.5 | 0.6641 | OPT | 0.000 | 0.46s |
| 0.5 | 17134.9 | 0.9094 | FEAS | 0.187 | 10.03s |
| 1.0 | 19344.8 | 1.0267 | FEAS | 0.305 | 10.03s |
| 2.0 | 19355.9 | 1.0272 | FEAS | 0.511 | 10.03s |
| 5.0 | 19694.9 | 1.0452 | FEAS | 0.710 | 10.03s |

## Best
- **λ* = 0.0, norm = 0.6641** (vs B3 0.7793)

## Gates
- sanity λ=0 ≤ B1 (B4 is optimal assignment, B1 is greedy under same capacity): **PASS** (norm=0.6640584345538074)
- B4 ≤ B3 (solver ≥ greedy clustering): **PASS**
- best solve solver-verified (OPTIMAL or gap ≤ 5%): **PASS**
- solver verification (App C.2 status on every solve): **PASS** (non-feasible aborts run)
- validate_pipeline hard-fails: **0**

## Notes
- Linearization: affinity term uses rank-distance |pos_i − pos_j| scaled to meters
  (spec §12.4 two-stage collapsed; full location-pair quadratic is a v0.3 upgrade).
- **Finding REVISED (v0.2 review F4 — the original 'worsens monotonically in λ'
  claim was FALSE):** λ>0 solves hit the 10 s budget, so their route costs are
  incumbents, not proofs. In the 120-SKU world the λ-curve is non-monotone
  (λ=1.0 incumbent 0.7401 < λ=0.5 0.9369). The only conclusive point is λ=0
  (OPTIMAL): no λ>0 incumbent beat it under L0 in this run. NOTE: this run's
  B3 comparison predates the capacity fix (review F2) — see R05 for the fair,
  leakage-free ranking, where B4(λ=0) beats B3.
