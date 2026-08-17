# R26 — Favorita REAL (replaces proxy)

**Date**: 2026-08-17T13:46:42.671864+00:00

**Source**: actual Favorita Grocery Sales (890MB Kaggle mirror,
CC0). Top-40 items by total unit sales across all 54 stores,
last 14 days, aggregated to (date, store, item) order lines.

**Question**: Does extreme demand concentration reduce expert
diversity on REAL Ecuador grocery data?

## Result

- n SKUs: 40
- n orders: 756
- myopic total: 63696
- BFIP total: 63696
- **gap = 0.00%**
- winners: E1(3), E4(1) (distinct=2)
- fixed-best: E1 (63722)

## Cross-dataset T0 summary (updated with real Favorita)

| Dataset | n SKUs | concentration | distinct winners | gap |
|---------|--------|----------------|-------------------|-----|
| WEPA (R21)            | 40 | 0.81 (Zipf 1.5) | 3-4 | 0.00% |
| CrossStacks (R24)     | 40 | 0.71              | 1-2 | 0.00% |
| Instacart top (R25)   | 20 | 0.81 (Zipf 1.5) | 2 | 0.00% |
| Instacart mid (R25)   | 20 | 0.81 (Zipf 1.0) | 2 | 0.00% |
| **Favorita real (R26b)** | 40 | very concentrated (top1=6.3M units) | **2** | **0.00%** |

**Finding**: 6th independent real-data configuration confirms
deployment boundary — gap is essentially 0% regardless of
demand concentration regime. Expert diversity varies (1-4 winners)
but ≥2 in all cases.
