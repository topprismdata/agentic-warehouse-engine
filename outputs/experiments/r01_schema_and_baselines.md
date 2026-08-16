# R01 — schema + baselines (B0 Random, B1 Static ABC, B2 COI)

**Date**: 2026-08-16T09:46:11.868452+00:00
**Seed**: 42
**Spec**: FMCG_Agentic_Warehouse_Decision_Engine_v1.0.pdf

## Stage 0 — Configuration
- `main_config.yaml`: project `agentic-warehouse-engine` v0.1.0
- World State size: SKUs = 120, locations = 60, days = 14
- Cost weights: α=1.0, β..ζ=0.0 (v0.1 pick-only)

## Stage 1 — Data Loading (synthetic)
- 9 canonical tables present: ['constraints', 'decision_plan', 'forecast_daily', 'inventory_snapshot', 'locations', 'order_lines', 'orders', 'sku_master', 'slot_assignment']
- Records: {'sku_master': 120, 'orders': 191, 'order_lines': 678, 'forecast_daily': 1680, 'locations': 60, 'inventory_snapshot': 120, 'slot_assignment': 840, 'constraints': 41, 'decision_plan': 7}
- hard-fails = 0, soft warnings = 0

## Stage 2 — Feature Engineering
- Skipped. **Todo #7 (Affinity)** and **#8 (Travel-time Calibration)** live here in v0.2.

## Stage 3 — OR Experts (B0, B1, B2)

| Expert | Total cost (± std over 5 seeds) | NormalizedCost vs B1 |
|--------|---------------|-------------------|
| **B1 Static ABC** | **65845.630** | **1.0000** |
| B2 COI            | 79643.965 | 1.2096 |
| B0 Random         | 236973.047 ± 44710.035 | 3.5989 |

- Per-seed B0 costs: [221201.59, 253600.949, 299043.282, 248154.241, 162865.173]
- B1 is the deterministic anchor.
- B0 should be **worse** than B1; metric_gate asserts `|B0_norm - 1| > 0.05` and win_rate `>= 1.0`.
- win_rate(B0 worse than B1) = **1.00** across 5 seeds (per-seed comparison; std/mean is not used — see gate docstring).

### Reproducibility gate (B1 across 5 reruns)
- max relative deviation = **0.000000** (B1 is fully deterministic ⇒ expected ≈ 0)

## Stage 4 — Predict + Submit
- `validate_pipeline`: hard-fails = **0**
- metric_gate verdict: **PASS**
- `evaluation_gate()` would block on FAIL; v0.1 logs the verdict.

## Open TODOs (next milestones)
- Todo #5/#6 (real data)
- Todo #7 (Affinity Score)
- Todo #8 (Warehouse graph + travel-time calibration)
- Todo #10 (CP-SAT Dynamic Slotting)
- Todo #11 (SimPy L1 replay → enables `pick_distance_total` replacement)
- Todo #12 (Execution Gateway stub)

