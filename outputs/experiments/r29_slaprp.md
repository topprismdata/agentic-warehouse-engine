# R29 — SLAPRP REAL (eighth real-data source)

**Date**: 2026-08-17T14:21:14.437353+00:00

**Source**: Prunet, Absi, Cattaruzza 2025 (Zenodo 7866860, EJOR).
**Unique property**: the FIRST source with **real multi-SKU
basket structure** (Guo 2021 instances: 1-8 items/order, mean ~6).
This is the natural domain of E3 (Affinity) and E6 (DDSR).

**Question**: Does the basket structure + published-optimal setting
change the deployment-boundary finding?

## Result

- n SKUs: 40
- n orders: 100
- n lines: 514 (basket structure: 1-8 items/order)
- n aisles × n bays: 4×5
- myopic total: 1050
- BFIP total: 1050
- **gap = 0.00%**
- winners: E1(1), E6(1), E7(3) (distinct=3)
- fixed-best: E7 (1058)

## Cross-dataset T0 (8 real-data sources)

| Source | n SKUs | data type | distinct winners | gap |
|--------|--------|-----------|-------------------|-----|
| WEPA (R21)            | 40 | single warehouse, 3mo | 3-4 | 0.00% |
| CrossStacks (R24)     | 40 | cross-dock, single batch | 1-2 | 0.00% |
| Instacart top (R25)   | 20 | retail top 10% | 2 | 0.00% |
| Instacart mid (R25)   | 20 | retail mid 10% | 2 | 0.00% |
| Favorita real (R26b)  | 40 | 14d, 54 stores | 2 | 0.00% |
| M5 (R28)              | 40 | 5-yr hierarchical | 1 (sparse) | 0.00% |
| **SLAPRP (R29)**     | 40 | **basket structure (1-8 items/order)** | **3** | **0.00%** |

**Key finding**: even with the strongest natural basket structure
of any real source, the deployment-boundary finding holds.
