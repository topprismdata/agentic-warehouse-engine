# R10 — T0 Expert Diversity(v1.2 序列协议,28 天 / 8 相位,warm-up 除外 7 期)

**Date**: 2026-08-16T10:38:29.209289+00:00 | seeds = [7, 17, 27] | world = 120 SKU / 60 loc
**Cost**: per-period pick(L0 route)+ λm·moves(λs=0,SPEC §9 声明)| myopic path 评估

## Per-period detail(cost 相对当期最差 expert 归一)

| seed | t | phase | myopic winner | #moves | costs by expert |
|------|---|-------|---------------|--------|-----------------|
| 7 | 1 | promo_ramp | E1_StaticABC | 0 | {'E1': 0.569, 'E2': 1.0, 'E3': 0.607, 'E4': 0.591, 'E5': 0.591, 'E6': 0.594, 'E7': 0.586} |
| 7 | 2 | promo_peak | E3_Affinity | 61 | {'E1': 0.809, 'E2': 1.0, 'E3': 0.799, 'E4': 0.81, 'E5': 0.81, 'E6': 0.823, 'E7': 0.804} |
| 7 | 3 | promo_decay | E7_Joint | 76 | {'E1': 0.603, 'E2': 1.0, 'E3': 0.661, 'E4': 0.505, 'E5': 0.505, 'E6': 0.509, 'E7': 0.49} |
| 7 | 4 | stable2 | E1_StaticABC | 104 | {'E1': 0.697, 'E2': 1.0, 'E3': 0.872, 'E4': 0.775, 'E5': 0.775, 'E6': 0.781, 'E7': 0.742} |
| 7 | 5 | reversal | E7_Joint | 64 | {'E1': 0.865, 'E2': 1.0, 'E3': 0.912, 'E4': 0.86, 'E5': 0.86, 'E6': 0.87, 'E7': 0.843} |
| 7 | 6 | affinity_shift | E7_Joint | 93 | {'E1': 0.8, 'E2': 1.0, 'E3': 0.839, 'E4': 0.794, 'E5': 0.794, 'E6': 0.816, 'E7': 0.785} |
| 7 | 7 | move_cost_shock | E7_Joint | 12 | {'E1': 0.776, 'E2': 1.0, 'E3': 0.909, 'E4': 0.776, 'E5': 0.776, 'E6': 0.831, 'E7': 0.423} |
| 17 | 1 | promo_ramp | E1_StaticABC | 0 | {'E1': 0.781, 'E2': 1.0, 'E3': 0.845, 'E4': 0.793, 'E5': 0.793, 'E6': 0.804, 'E7': 0.794} |
| 17 | 2 | promo_peak | E5_Robust | 113 | {'E1': 0.822, 'E2': 1.0, 'E3': 0.857, 'E4': 0.782, 'E5': 0.781, 'E6': 0.825, 'E7': 0.821} |
| 17 | 3 | promo_decay | E7_Joint | 83 | {'E1': 0.718, 'E2': 1.0, 'E3': 0.794, 'E4': 0.673, 'E5': 0.673, 'E6': 0.699, 'E7': 0.665} |
| 17 | 4 | stable2 | E7_Joint | 62 | {'E1': 0.75, 'E2': 1.0, 'E3': 0.82, 'E4': 0.747, 'E5': 0.747, 'E6': 0.761, 'E7': 0.736} |
| 17 | 5 | reversal | E7_Joint | 65 | {'E1': 0.897, 'E2': 1.0, 'E3': 0.925, 'E4': 0.893, 'E5': 0.893, 'E6': 0.911, 'E7': 0.878} |
| 17 | 6 | affinity_shift | E3_Affinity | 116 | {'E1': 0.743, 'E2': 1.0, 'E3': 0.73, 'E4': 0.759, 'E5': 0.759, 'E6': 0.783, 'E7': 0.756} |
| 17 | 7 | move_cost_shock | E7_Joint | 55 | {'E1': 0.838, 'E2': 1.0, 'E3': 0.79, 'E4': 0.846, 'E5': 0.846, 'E6': 0.952, 'E7': 0.602} |
| 27 | 1 | promo_ramp | E7_Joint | 16 | {'E1': 0.751, 'E2': 1.0, 'E3': 0.805, 'E4': 0.755, 'E5': 0.753, 'E6': 0.762, 'E7': 0.749} |
| 27 | 2 | promo_peak | E7_Joint | 64 | {'E1': 0.743, 'E2': 1.0, 'E3': 0.775, 'E4': 0.647, 'E5': 0.647, 'E6': 0.648, 'E7': 0.645} |
| 27 | 3 | promo_decay | E7_Joint | 81 | {'E1': 0.741, 'E2': 1.0, 'E3': 0.728, 'E4': 0.693, 'E5': 0.693, 'E6': 0.707, 'E7': 0.687} |
| 27 | 4 | stable2 | E7_Joint | 66 | {'E1': 0.831, 'E2': 1.0, 'E3': 0.81, 'E4': 0.809, 'E5': 0.808, 'E6': 0.833, 'E7': 0.794} |
| 27 | 5 | reversal | E7_Joint | 60 | {'E1': 0.937, 'E2': 0.932, 'E3': 1.0, 'E4': 0.95, 'E5': 0.95, 'E6': 0.959, 'E7': 0.927} |
| 27 | 6 | affinity_shift | E1_StaticABC | 109 | {'E1': 0.8, 'E2': 1.0, 'E3': 0.832, 'E4': 0.822, 'E5': 0.822, 'E6': 0.844, 'E7': 0.811} |
| 27 | 7 | move_cost_shock | E7_Joint | 13 | {'E1': 0.697, 'E2': 1.0, 'E3': 0.8, 'E4': 0.695, 'E5': 0.695, 'E6': 0.826, 'E7': 0.377} |

## Winner switching(T0 核心)

- 总期次 = 21(=3 seeds × 7 phases)
- winner 分布: {'E1_StaticABC': 4, 'E3_Affinity': 2, 'E7_Joint': 14, 'E5_Robust': 1}
- **top expert share = E7_Joint 14/21 = 67%**(阈值:<80% Go,≥95% No-Go)
- distinct winners = 4(要求 ≥3)

## Phase → winner 对齐

| phase | modal winner | 分布 |
|-------|--------------|------|
| affinity_shift | E7_Joint | {'E7_Joint': 1, 'E3_Affinity': 1, 'E1_StaticABC': 1} |
| move_cost_shock | E7_Joint | {'E7_Joint': 3} |
| promo_decay | E7_Joint | {'E7_Joint': 3} |
| promo_peak | E3_Affinity | {'E3_Affinity': 1, 'E5_Robust': 1, 'E7_Joint': 1} |
| promo_ramp | E1_StaticABC | {'E1_StaticABC': 2, 'E7_Joint': 1} |
| reversal | E7_Joint | {'E7_Joint': 3} |
| stable2 | E7_Joint | {'E1_StaticABC': 1, 'E7_Joint': 2} |

## 各相位 winner 与第二名差距(切换信号强度)

| phase | mean margin |
|-------|-------------|
| affinity_shift | 1.4% |
| move_cost_shock | 38.4% |
| promo_decay | 1.6% |
| promo_peak | 0.4% |
| promo_ramp | 1.5% |
| reversal | 1.4% |
| stable2 | 3.1% |

## Always-X / Fixed-Best / Myopic(每 seed)

- seed 7: fixed-best=E7_Joint(30929) myopic=30627 always-E1=34504 always-E4=34463
- seed 17: fixed-best=E7_Joint(38904) myopic=38428 always-E1=41978 always-E4=41762
- seed 27: fixed-best=E7_Joint(31993) myopic=31937 always-E1=35311 always-E4=34575

## Gates
- capacity violations across ALL expert-periods: **0** (PASS)
- validate_pipeline (non-vacuous): hard-fails = **0**
- T0 verdict: **GO**(share=67%, distinct=4)

## 判读
- **GO**:expert 最优性随相位切换且可解释 → 继续 T1(Myopic vs Dynamic Oracle)。
- 本 T0 在合成平台(构造性 regime);T 关通过后按 v1.2 §12 切 WEPA/SLAPStack 复核。
