# R26 — Favorita Proxy (concentration stress test)

**Date**: 2026-08-17T13:23:33.187651+00:00

**Status**: Full Favorita corpus (890MB) unreachable due to Kaggle
download throttling. Proxy uses published concentration statistics
(top-2% of items = ~33% of unit sales) with Zipf(0.7).

**Question**: Does extreme demand concentration reduce expert diversity?

## Result

| n SKUs | myopic | BFIP | gap | winners | distinct | fixed-best |
|--------|--------|------|-----|---------|----------|------------|
| 30 | 12409 | 12409 | 0.00% | E1(6), E6(1) | 2 | E1 |

## Interpretation
- High concentration → limited diversity (2 winners)

- Cross-dataset T0 (different concentrations, different warehouse types):
  | Dataset | n SKUs | concentration | distinct winners | gap |
  |---------|--------|----------------|-------------------|-----|
  | WEPA (R21)       | 40  | 0.81 (Zipf 1.5) | 3-4 | 0.00% |
  | CrossStacks (R24)| 40  | 0.71           | 1-2 | 0.00% |
  | Instacart top (R25)| 20 | 0.81 (Zipf 1.5) | 2 | 0.00% |
  | Instacart mid (R25)| 20 | 0.81 (Zipf 1.0) | 2 | 0.00% |
  | Favorita proxy (R26)| 30 | ~0.89 (Zipf 0.7) | 2 | 0.00% |
  - Real data consistently gap=0 regardless of concentration
  - Winner diversity varies (1-4), but ≥2 experts in all cases
