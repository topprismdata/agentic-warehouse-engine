# R02 — Affinity (Todo #7) + B3 under L0 route cost

**Date**: 2026-08-16T09:26:19.975771+00:00
**Seed**: 42 | concentration = 0.7 | alpha = 1.0 | top_k = 5

## Metric change vs R01
Cost upgraded per-line Euclidean → **per-order greedy route** (spec §14.3 L0).
R01 numbers are legacy per-line; not comparable. B1 remains the anchor (norm = 1.0).

## Affinity graph
- pairs with CoPick > 0: **239**
- pairs with lift > 1 (better-than-chance co-occurrence): **176**
- top pair: {'sku_i': 'S00015', 'sku_j': 'S00039', 'copick': 4, 'support_i': 7, 'support_j': 4, 'confidence_ij': 0.5714285714285714, 'confidence_ji': 1.0, 'lift': 28.7143, 'affinity': 46.2139}

## Results (L0 route cost)

| Expert | Total route cost | NormalizedCost vs B1 |
|--------|-----------------|---------------------|
| **B1 Static ABC** | **1132.3** | **1.0000** |
| B2 COI | 1281.0 | 1.1313 |
| B3 Affinity | 861.8 | **0.7611** |
| B0 Random (5 seeds) | 1458.1 | 1.2878 |

- Per-seed B0: [1610.5, 1488.4, 1525.9, 1460.8, 1204.9]

## Gates
- B3 improves ≥ 5%: **PASS** (norm = 0.7611)
- B0 always worse than B1: **PASS**
- affinity graph non-degenerate: **PASS** (176 lift>1 pairs)
- validate_pipeline hard-fails: **0**

## Interpretation
- B3 exploits basket structure: co-picked SKUs share one location → fewer route stops.
- If B3 FAILs the 5% gate, sweep `--concentration` (basket strength) or `--alpha`
  before touching the algorithm — a degenerate world cannot reward affinity.
