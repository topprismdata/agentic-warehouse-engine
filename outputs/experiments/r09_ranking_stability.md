# R09 — Expert Ranking Stability: the Go/No-Go experiment (spec update §10, Step 4)

**Date**: 2026-08-16T10:30:07.423455+00:00 | states = 7 regimes × 2 seeds = 14 | world = 40 SKU / 20 loc / 8 d

## Cost matrix — mean NormalizedCost vs E1 (L0 route, FUTURE window, honest split)

| Regime | E1_StaticABC | E2_COI | E3_Affinity | E4_ForecastABC | E5_Robust | E6_FcAff | E7_RollingLite | winner |
|--------|------|------|------|------|------|------|------|--------|
| R1_stable | 1.000 | 1.255 | 1.144 | 0.982 | 0.982 | 1.103 | 1.000 | E4_ForecastABC |
| R2_promotion | 1.000 | 1.145 | 1.068 | 0.887 | 0.887 | 0.926 | 0.985 | E4_ForecastABC |
| R3_velocity_reversal | 1.000 | 1.006 | 0.939 | 0.968 | 0.968 | 1.035 | 1.000 | E3_Affinity |
| R4_affinity_shift | 1.000 | 1.278 | 1.163 | 1.007 | 1.007 | 1.211 | 1.000 | E4_ForecastABC |
| R5_forecast_error | 1.000 | 1.255 | 1.144 | 1.025 | 0.989 | 1.171 | 1.000 | E1_StaticABC |
| R6_move_cost | 1.000 | 1.607 | 1.405 | 1.073 | 1.073 | 1.487 | 1.000 | E1_StaticABC |
| R7_capacity | 1.000 | 1.270 | 1.219 | 1.013 | 1.013 | 1.119 | 1.000 | E1_StaticABC |

## Winner switching
- distinct winners across 14 states: **4** (E4_ForecastABC×6, E1_StaticABC×6, E3_Affinity×1, E5_Robust×1)
- dominance of best single expert: **E4_ForecastABC 6/14 = 43%**
- regime → modal winner: {'R1_stable': 'E4_ForecastABC', 'R2_promotion': 'E4_ForecastABC', 'R3_velocity_reversal': 'E3_Affinity', 'R4_affinity_shift': 'E4_ForecastABC', 'R5_forecast_error': 'E1_StaticABC', 'R6_move_cost': 'E1_StaticABC', 'R7_capacity': 'E1_StaticABC'}
- predicted pattern matches (§9 table): **2**/6

## Verdict
**GO** — expert ranking switches with warehouse state in interpretable patterns; instance-wise selection (and the Selector research program) is justified.

## Caveats (honest scope)
- Synthetic platform (Zipf + basket structure + controlled regimes); WEPA/SLAPStack
  replication is the next step if GO (spec update §1: WEPA is the phase-1 priority).
- Cost = L0 route + L1 flow only; λ_r/λ_m/λ_c components enter with the full
  replenishment/relocation model (E7 full rolling, Step 10).
- E7 is the single-window reduction (move-penalized re-slot), declared in module
  docstring; multi-period rolling may change R6's shape but not the Go/No-Go logic.
- R5 noise hits E4/E5/E6's forecast INPUT only (the stream itself is R1-stable),
  per spec §9 definition of forecast uncertainty.

