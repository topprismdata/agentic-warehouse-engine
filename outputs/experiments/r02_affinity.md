# R02 — Affinity (Todo #7) + B3 under L0 route cost

**Date**: 2026-08-16T09:36:14.710969+00:00
**Seed**: 42 | concentration = 0.7 | alpha = 1.0 | top_k = 5

## Metric change vs R01
Cost upgraded per-line Euclidean → **per-order greedy route** (spec §14.3 L0).
R01 numbers are legacy per-line; not comparable. B1 remains the anchor (norm = 1.0).

## Affinity graph
- pairs with CoPick > 0: **380**
- pairs with lift > 1 (better-than-chance co-occurrence): **322**
- top pair: {'sku_i': 'S00071', 'sku_j': 'S00106', 'copick': 1, 'support_i': 1, 'support_j': 1, 'confidence_ij': 1.0, 'confidence_ji': 1.0, 'lift': 205.0, 'affinity': 142.0952}

## Results (L0 route cost)

| Expert | Total route cost | NormalizedCost vs B1 |
|--------|-----------------|---------------------|
| **B1 Static ABC** | **18842.5** | **1.0000** |
| B2 COI | 21380.8 | 1.1347 |
| B3 Affinity | 8530.2 | **0.4527** |
| B0 Random (5 seeds) | 33705.9 | 1.7888 |

- Per-seed B0: [34991.2, 32503.2, 38184.3, 32107.1, 30743.9]

## Gates
- B3 improves ≥ 5%: **PASS** (norm = 0.4527)
- B0 always worse than B1: **PASS**
- affinity graph non-degenerate: **PASS** (322 lift>1 pairs)
- validate_pipeline hard-fails: **0**

## Interpretation
- B3 exploits basket structure: co-picked SKUs share one location → fewer route stops.
- If B3 FAILs the 5% gate, sweep `--concentration` (basket strength) or `--alpha`
  before touching the algorithm — a degenerate world cannot reward affinity.
