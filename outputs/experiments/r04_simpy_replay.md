# R04 — SimPy L1 replay: distance → time metric (Todo #11)

**Date**: 2026-08-16T09:37:37.729894+00:00 | seed = 42 | pickers = 3
**Sim params**: speed 1.2 m/s, 20 s/stop, 2 s/unit, horizon 14 d (uncalibrated — see notes)

## Metric upgrade
L0 (distance) gated R02/R03. L1 adds finite pickers → queueing, travel time,
per-stop/per-unit pick time. Cost of interest: **makespan** (all orders done)
and utilization/wait (first congestion signal, spec §3.2 δ).

## Results

| Expert | L0 norm | L1 Σ flow (h) | **L1 norm** | makespan | utilization | wait |
|--------|---------|---------------|-------------|----------|-------------|------|
| B1_StaticABC | 1.0000 | 10.50 | 1.0000 | 321.02h | 1.1% | 0.00h |
| B2_COI | 1.1347 | 11.09 | 1.0554 | 321.02h | 1.2% | 0.00h |
| B3_Affinity | 0.4527 | 7.34 | 0.6987 | 321.00h | 0.8% | 0.00h |
| B4_CPSAT(l=0) | 0.6654 | 8.92 | 0.8489 | 321.01h | 0.9% | 0.00h |
| B0 Random (5 seeds) | — | — | 1.3212 | 321.04h (mean) | — | — |

## Gates
- all orders completed within horizon: **PASS**
- B0 always worst under L1 (flow time): **PASS**
- L0→L1 ranking: **PRESERVED** — see finding below
- validate_pipeline hard-fails: **0**

## Notes & honest caveats
- **Metric choice finding (2nd)**: even Σ completion is release-dominated
  (14-day spread ≈ 32.6k h vs hours of exec work). L1 cost = Σ per-order FLOW
  time (wait + travel + pick) — completion minus release. Two candidate metrics
  died before this one (makespan: insensitive; Σ completion: release-dominated);
  both failures were caught by the gates, which is the system working as designed.
- **Uncalibrated**: pick parameters (speed / s-per-stop / s-per-unit) are defaults,
  not fitted to a real warehouse. Until Task #12-style execution data exists, L1
  results are RELATIVE comparisons between experts under identical assumptions —
  exactly what the ranking-preservation gate tests. Absolute hours are not claims.
- Congestion (δ) is measurable but dormant: utilization ≈ 0.6% ≪ saturation, so
  queueing wait ≈ 0 for every expert. Congestion only becomes discriminating at
  higher load or fewer pickers (v0.3 stress test, spec §16.4 Labor Shock).
- Next (v0.3): wave/priority dispatch, replenishment events, per-picker speed
  distributions; calibration against SLAPStack/WEPA task durations (Todo #6).
