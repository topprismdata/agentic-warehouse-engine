# R28b — M5 with ALL 10 stores (robustness check)

**Date**: 2026-08-17T16:02:30.136765+00:00

**Question**: Was R28's distinct=1 a consequence of (a) the
5-year steady-state nature of M5 hierarchical demand, or (b) the
thin signal from a single store (78 lines/30d)?

**Method**: Use ALL 10 stores (CA/TX/WI) over last 30 days, top-40
items by total volume.

## Result

- n SKUs: 40 (top by total volume)
- n orders: 480 (~80 per period)
- n lines: 688 (~114 per period)
- myopic total: 1451
- BFIP total: 1451
- **gap = 0.00%**
- winners: E1(6) (distinct=1)
- fixed-best: E1 (1451)

## Interpretation
- Still distinct=1 even with denser data: confirms M5's
  5-year steady-state produces single-winner outcomes.

## Cross-dataset T0 (9 real-data sources now)

| Source | n SKUs | data type | distinct winners | gap |
|--------|--------|-----------|-------------------|-----|
| WEPA (R21) | 40 | single warehouse, 3mo | 3-4 | 0.00% |
| CrossStacks (R24) | 40 | cross-dock, single batch | 1-2 | 0.00% |
| Instacart top (R25) | 20 | retail top 10% | 2 | 0.00% |
| Instacart mid (R25) | 20 | retail mid 10% | 2 | 0.00% |
| Favorita real (R26b) | 40 | 14d, 54 stores | 2 | 0.00% |
| M5 single store (R28) | 40 | 5-yr hierarchical | 1 | 0.00% |
| M5 all stores (R28b) | 40 | 5-yr hierarchical (dense) | **1** | **0.00%** |
| SLAPRP (R29) | 40 | basket structure | 3 | 0.00% |
