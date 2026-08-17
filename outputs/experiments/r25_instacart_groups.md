# R25 — Instacart Multi-Group T0 Validation

**Date**: 2026-08-17T13:22:16.719388+00:00

**Question**: Does T0 diversity hold across demand-concentration
regimes? Instacart: top-10% SKUs = 81.4%, mid-10% = 9.5% of order lines.
Proxied by Zipf(1.5) concentrated vs Zipf(1.0) flatter.

## Results

| Group | n SKUs | myopic | BFIP | gap | winners | distinct | fixed-best |
|-------|--------|--------|------|-----|---------|----------|------------|
| top10pct_concentrated | 20 | 681 | 681 | 0.00% | E1(1), E6(6) | 2 | E1 |
| mid10pct_flatter | 20 | 1004 | 1004 | 0.00% | E1(1), E6(6) | 2 | E1 |

## Interpretation
- Concentrated (top-10%): 2 distinct winners
- Flatter (mid-10%): 2 distinct winners
- Mixed: top=2 vs mid=2 winners — concentration may matter
