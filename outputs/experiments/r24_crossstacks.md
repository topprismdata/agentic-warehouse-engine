# R24 — CrossStacks Validation (WEPA-Natural replicate)

**Date**: 2026-08-17T10:01:09.734287+00:00 | SKUs = 40 | orders = 40 | periods = 5

## Result
- myopic total: **1616**
- BFIP total: **1616**
- **gap = 0.00%**
- winners by period: ['E1', 'E1', 'E1', 'E6']
- fixed-best: E1_StaticABC (1617)

## Comparison with WEPA-Natural (R21)
| Dataset | gap | Myopic=BFIP? | Winner diversity |
|---------|-----|---------------|------------------|
| WEPA    | 0.00% | yes | 3-4 distinct |
| CrossStacks | **0.00%** | yes | 2 distinct |

## Interpretation
Both independent warehouses show gap=0 — the deployment-boundary finding (paper §11) is not WEPA-specific. Trap requires non-stationary regime changes beyond normal warehouse operations.
