# R07 — real Instacart baskets (Todo #5, Track B): honest re-ranking

**Date**: 2026-08-16T10:00:13.619392+00:00 | seed = 42 | users train/eval = 2100/900 | top SKUs = 120 | rack = 60 locs cap 2

## Real basket structure vs synthetic assumption
- observed same-aisle pair share: **0.2302** (synthetic world assumed 0.70)
- affinity pairs (CoPick>0): 6782 | lift>1: 4008
- USER-LEVEL split: slot on train users, evaluate on held-out users — no identity leakage (adapter has the reasoning)

## Results (held-out users only; B1 anchor = 1.0)

| Expert | L0 norm | L1 norm | capacity violations |
|--------|---------|---------|---------------------|
| B1_StaticABC | 1.0000 | 1.0000 | 0 |
| B2_COI | 1.0588 | 1.1818 | 0 |
| B3_Affinity | 0.9803 | 0.9251 | 0 |
| B4_CPSAT(l=0) | 0.9115 | 0.7736 | 0 |
| B0 Random (5 seeds) | 1.1886 | 1.5951 | 0 |

## Gates
- zero capacity violations: **PASS**
- B0 worst (both metrics, all seeds): **PASS**
- validate_pipeline clean (480 assignments, 4 plans): **PASS**
- L0/L1 ranking: **CONSISTENT**

## R05 (synthetic 0.7) vs R07 (real) comparison
| Expert | R05 L0 | R07 L0 |
|--------|--------|--------|
| B3 Affinity | 0.8442 | 0.9803 |
| B4 CP-SAT | 0.8089 | 0.9115 |

## Honest notes
- Geometry is still synthetic (Track B definition): real DC layout remains Todo #6.
- **B2 COI's volumes are synthetic uniform draws** (Instacart ships no cube/weight) —
  COI's real-data loss (1.0588/1.1818 vs synthetic 0.9707) is partly this artifact;
  do not cite B2 as a real-data result until real cube data arrives.
- quantity=1 per line (Instacart carries no counts); L1 is therefore stop-dominated
  (avg 3.25 lines/order), which is also why B4's L1 edge (0.7736) exceeds its L0
  edge (0.9115): frequency-weighted distance assignment saves travel per stop,
  and stops are what dominate flow time here.
- The interesting number is the concentration gap: real co-occurrence is 0.23 vs
  the synthetic 0.70 — the affinity edge (B3) collapses to ~2% and the synthetic
  B2 advantage flips sign. **Synthetic parameters systematically distort expert
  rankings; every synthetic conclusion needs a real-data counterpart run.**
