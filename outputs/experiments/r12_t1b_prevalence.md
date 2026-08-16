# R12 — T1b Prevalence:myopic failure 的分布形态(SPEC v1.3)

**Date**: 2026-08-16T11:38:27.443454+00:00 | seeds = 12 | beam = 30 | τ = 2.0 | world = 120 SKU / 60 loc

## T1a(已固化,YES)
seed 17 构成 constructive evidence:divergence@affinity_shift,sacrifice=80,
regret=2116(TrapScore=26.33),shock 落在
move_cost_shock。**当期最优 ≠ 长期最优已被证明存在。**

## T1b:逐 seed Trap 分析

| seed | gap | div@t | div phase | sacrifice | future regret | TrapScore | 类型 |
|------|-----|-------|-----------|-----------|---------------|-----------|------|
| 7 | 0.00% | — | — | 0 | 0 | 0.00 | — |
| 17 | 5.34% | 5 | affinity_shift | 80 | 2116 | 26.33 | **TRAP** |
| 27 | 0.09% | 2 | promo_decay | 5 | 34 | 6.19 | **TRAP** |
| 37 | 0.25% | 3 | stable2 | 22 | 105 | 4.81 | **TRAP** |
| 47 | 0.00% | — | — | 0 | 0 | 0.00 | — |
| 57 | 0.11% | 3 | stable2 | 18 | 55 | 3.15 | **TRAP** |
| 67 | 0.28% | 3 | stable2 | 5 | 109 | 22.70 | **TRAP** |
| 77 | 0.22% | 0 | promo_ramp | 27 | 100 | 3.65 | **TRAP** |
| 87 | 0.02% | 3 | stable2 | 33 | 42 | 1.27 | — |
| 97 | 0.33% | 0 | promo_ramp | 17 | 115 | 6.68 | **TRAP** |
| 107 | 0.40% | 0 | promo_ramp | 48 | 208 | 4.28 | **TRAP** |
| 117 | 1.16% | 0 | promo_ramp | 12 | 384 | 32.09 | **TRAP** |

## 分布形态(预声明 buckets)

- gap: mean = 0.68%,median = 0.23%
- ~0(<0.5%): **10** | small(0.5–2%): **1** | mid(2–5%): **0** | large(≥5%): **1**  (共 12)
- traps(TrapScore>τ): **9/12**;free wins: 0;轨迹全同: 2
- **P(trap | 存在分叉) = 9/10**
- divergence 落点: {'affinity_shift': 1, 'promo_decay': 1, 'stable2': 4, 'promo_ramp': 4}
- trap 的后续 shock 相位: {'move_cost_shock': 4, 'stable2': 2, 'reversal': 7, 'affinity_shift': 3, 'promo_peak': 4, 'promo_decay': 2}

## Expert Winning Map 数据(phase × winner,myopic 路径)

| phase | modal winner | 稳定性 | 全分布 |
|-------|--------------|--------|--------|
| affinity_shift | E1_StaticABC | 67% | {'E7_Joint': 3, 'E3_Affinity': 1, 'E1_StaticABC': 8} |
| move_cost_shock | E7_Joint | 100% | {'E7_Joint': 12} |
| promo_decay | E1_StaticABC | 42% | {'E7_Joint': 2, 'E4_Forecast': 3, 'E1_StaticABC': 5, 'E3_Affinity': 1, 'E6_DDSR': 1} |
| promo_peak | E7_Joint | 33% | {'E3_Affinity': 1, 'E5_Robust': 2, 'E7_Joint': 4, 'E4_Forecast': 1, 'E1_StaticABC': 1, 'E6_DDSR': 3} |
| promo_ramp | E1_StaticABC | 58% | {'E1_StaticABC': 7, 'E7_Joint': 3, 'E6_DDSR': 2} |
| reversal | E7_Joint | 83% | {'E7_Joint': 10, 'E1_StaticABC': 1, 'E2_COI': 1} |
| stable2 | E7_Joint | 42% | {'E1_StaticABC': 2, 'E6_DDSR': 3, 'E7_Joint': 5, 'E3_Affinity': 1, 'E4_Forecast': 1} |

## 判读(不以均值 gate)

1. **形态**:gap 呈「多数 ~0 + 少数大」的事件依赖分布 → DWERP 价值是
   event-dependent(保险型:避免少量高损失错误),与导师预判一致。
2. **机制**:divergence 集中出现在 affinity_shift(1), promo_decay(1), stable2(4), promo_ramp(4);
   trap 的 regret 几乎全部由 move_cost_shock, stable2, reversal, affinity_shift, promo_peak, promo_decay 相位贡献 ——
   **trap = "结构转变期的不当重排 × 后续成本冲击"的复合事件**。
3. **可学习结构(Selector 前置检查)**:winner 稳定性最高的相位
   move_cost_shock(100%), reversal(83%), affinity_shift(67%);
   若关键相位稳定性 ≥70%,f(S_t)→E* 有监督学习结构;若大面积低稳定,
   winner 更接近 seed noise → Selector 需要更强的状态特征而非直接监督。
4. null seeds(轨迹全同)是**信息性结果**:beam 未找到更好路径 ≠ myopic 最优
   (beam-limited),但与 trap seeds 合并即给出 P(trap) 的经验分布。

## 下一步
T2(SPEC v1.3 §3):λm ∈ 8 点 sweep,inverted-U 检验(move 成本中间区域
规划价值最大),三张曲线 + winning map 正式图。
