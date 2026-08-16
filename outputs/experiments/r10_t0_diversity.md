# R10 — T0 Expert Diversity(v1.2 序列协议,28 天 / 8 相位,warm-up 除外 7 期)

**Date**: 2026-08-16T10:50:07.534785+00:00 | seeds = [7, 17, 27] | world = 120 SKU / 60 loc
**Cost**: per-period pick(L0 route)+ λm·moves(λs=0,SPEC §9 声明)| myopic path 评估

## Per-period detail(cost 相对当期最差 expert 归一)

| seed | t | phase | myopic winner | #moves | costs by expert |
|------|---|-------|---------------|--------|-----------------|
| 7 | 1 | promo_ramp | E1_StaticABC | 0 | {'E1': 0.569, 'E2': 1.0, 'E3': 0.607, 'E4': 0.591, 'E5': 0.591, 'E6': 0.59, 'E7': 0.586} |
| 7 | 2 | promo_peak | E3_Affinity | 61 | {'E1': 0.809, 'E2': 1.0, 'E3': 0.799, 'E4': 0.81, 'E5': 0.81, 'E6': 0.809, 'E7': 0.804} |
| 7 | 3 | promo_decay | E7_Joint | 76 | {'E1': 0.604, 'E2': 1.0, 'E3': 0.662, 'E4': 0.506, 'E5': 0.506, 'E6': 0.491, 'E7': 0.49} |
| 7 | 4 | stable2 | E1_StaticABC | 106 | {'E1': 0.695, 'E2': 1.0, 'E3': 0.872, 'E4': 0.774, 'E5': 0.774, 'E6': 0.761, 'E7': 0.753} |
| 7 | 5 | reversal | E7_Joint | 64 | {'E1': 0.865, 'E2': 1.0, 'E3': 0.912, 'E4': 0.86, 'E5': 0.86, 'E6': 0.846, 'E7': 0.843} |
| 7 | 6 | affinity_shift | E7_Joint | 93 | {'E1': 0.8, 'E2': 1.0, 'E3': 0.839, 'E4': 0.794, 'E5': 0.794, 'E6': 0.791, 'E7': 0.79} |
| 7 | 7 | move_cost_shock | E7_Joint | 16 | {'E1': 0.771, 'E2': 1.0, 'E3': 0.909, 'E4': 0.771, 'E5': 0.771, 'E6': 0.674, 'E7': 0.479} |
| 17 | 1 | promo_ramp | E1_StaticABC | 0 | {'E1': 0.781, 'E2': 1.0, 'E3': 0.845, 'E4': 0.793, 'E5': 0.793, 'E6': 0.8, 'E7': 0.797} |
| 17 | 2 | promo_peak | E5_Robust | 113 | {'E1': 0.822, 'E2': 1.0, 'E3': 0.857, 'E4': 0.782, 'E5': 0.781, 'E6': 0.803, 'E7': 0.795} |
| 17 | 3 | promo_decay | E4_Forecast | 96 | {'E1': 0.718, 'E2': 1.0, 'E3': 0.795, 'E4': 0.673, 'E5': 0.673, 'E6': 0.678, 'E7': 0.676} |
| 17 | 4 | stable2 | E6_DDSR | 70 | {'E1': 0.746, 'E2': 1.0, 'E3': 0.818, 'E4': 0.745, 'E5': 0.745, 'E6': 0.735, 'E7': 0.74} |
| 17 | 5 | reversal | E7_Joint | 64 | {'E1': 0.897, 'E2': 1.0, 'E3': 0.924, 'E4': 0.893, 'E5': 0.893, 'E6': 0.883, 'E7': 0.874} |
| 17 | 6 | affinity_shift | E3_Affinity | 117 | {'E1': 0.743, 'E2': 1.0, 'E3': 0.731, 'E4': 0.76, 'E5': 0.76, 'E6': 0.758, 'E7': 0.756} |
| 17 | 7 | move_cost_shock | E7_Joint | 55 | {'E1': 0.834, 'E2': 1.0, 'E3': 0.792, 'E4': 0.841, 'E5': 0.841, 'E6': 0.751, 'E7': 0.608} |
| 27 | 1 | promo_ramp | E7_Joint | 16 | {'E1': 0.751, 'E2': 1.0, 'E3': 0.805, 'E4': 0.755, 'E5': 0.753, 'E6': 0.757, 'E7': 0.744} |
| 27 | 2 | promo_peak | E7_Joint | 65 | {'E1': 0.743, 'E2': 1.0, 'E3': 0.775, 'E4': 0.648, 'E5': 0.648, 'E6': 0.633, 'E7': 0.628} |
| 27 | 3 | promo_decay | E7_Joint | 79 | {'E1': 0.742, 'E2': 1.0, 'E3': 0.729, 'E4': 0.694, 'E5': 0.694, 'E6': 0.689, 'E7': 0.688} |
| 27 | 4 | stable2 | E6_DDSR | 76 | {'E1': 0.828, 'E2': 1.0, 'E3': 0.806, 'E4': 0.805, 'E5': 0.805, 'E6': 0.8, 'E7': 0.802} |
| 27 | 5 | reversal | E7_Joint | 63 | {'E1': 0.939, 'E2': 0.933, 'E3': 1.0, 'E4': 0.951, 'E5': 0.951, 'E6': 0.936, 'E7': 0.926} |
| 27 | 6 | affinity_shift | E1_StaticABC | 110 | {'E1': 0.8, 'E2': 1.0, 'E3': 0.832, 'E4': 0.821, 'E5': 0.821, 'E6': 0.822, 'E7': 0.819} |
| 27 | 7 | move_cost_shock | E7_Joint | 13 | {'E1': 0.702, 'E2': 1.0, 'E3': 0.804, 'E4': 0.7, 'E5': 0.7, 'E6': 0.617, 'E7': 0.372} |

## Winner switching(T0 核心)

- 总期次 = 21(=3 seeds × 7 phases)
- winner 分布: {'E1_StaticABC': 4, 'E3_Affinity': 2, 'E7_Joint': 11, 'E5_Robust': 1, 'E4_Forecast': 1, 'E6_DDSR': 2}
- **top expert share = E7_Joint 11/21 = 52%**(阈值:<80% Go,≥95% No-Go)
- distinct winners = 6(要求 ≥3)

## Phase → winner 对齐

| phase | modal winner | 分布 |
|-------|--------------|------|
| affinity_shift | E7_Joint | {'E7_Joint': 1, 'E3_Affinity': 1, 'E1_StaticABC': 1} |
| move_cost_shock | E7_Joint | {'E7_Joint': 3} |
| promo_decay | E7_Joint | {'E7_Joint': 2, 'E4_Forecast': 1} |
| promo_peak | E3_Affinity | {'E3_Affinity': 1, 'E5_Robust': 1, 'E7_Joint': 1} |
| promo_ramp | E1_StaticABC | {'E1_StaticABC': 2, 'E7_Joint': 1} |
| reversal | E7_Joint | {'E7_Joint': 3} |
| stable2 | E6_DDSR | {'E1_StaticABC': 1, 'E6_DDSR': 2} |

## 各相位 winner 与第二名差距(切换信号强度)

| phase | mean margin |
|-------|-------------|
| affinity_shift | 1.3% |
| move_cost_shock | 29.3% |
| promo_decay | 0.1% |
| promo_peak | 0.5% |
| promo_ramp | 1.7% |
| reversal | 0.7% |
| stable2 | 2.9% |

## Always-X / Fixed-Best / Myopic(每 seed)

- seed 7: fixed-best=E7_Joint(31036) myopic=30670 always-E1=33762 always-E4=33716
- seed 17: fixed-best=E7_Joint(38455) myopic=38106 always-E1=41466 always-E4=41256
- seed 27: fixed-best=E7_Joint(31894) myopic=31794 always-E1=35439 always-E4=34677

## Gates
- capacity violations across ALL expert-periods: **0** (PASS)
- validate_pipeline (non-vacuous): hard-fails = **0**
- T0 verdict: **GO**(share=52%, distinct=6)

## 判读
- **GO**:expert 最优性随相位切换且可解释 → 继续 T1(Myopic vs Dynamic Oracle)。
- 本 T0 在合成平台(构造性 regime);T 关通过后按 v1.2 §12 切 WEPA/SLAPStack 复核。
