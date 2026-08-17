# R22 — Cost-Sensitive Expert Selector(SPEC v1.5 §7)

**Date**: 2026-08-17T07:37:57.338070+00:00 | train seeds = [7, 17, 27, 37, 47, 57, 67, 77] | test seeds = [87, 97, 107, 117]
**方法**: cost-sensitive prediction(预测 Ĉ(E_i|S_t) 后 argmin),非纯分类;评价 = Dynamic Regret + Top-1

## 状态特征(仅 online-observable;**禁用 phase** — SPEC §7 反泄漏)

demand_cv, demand_trend, top10_share, promoted_share, fc_p50_sum, fc_uncertainty, affinity_density, mc_scale, n_lines, period_demand

## 结果(test seeds)

| Selector | Total Cost | Mean Regret | Top-1 Hit |
|----------|-----------|-------------|-----------|
| S0_Oracle | 138296 | 0.00% | 100.0% |
| S1_FixedBest | 139843 | 1.43% | 46.4% |
| S2_Rule | 140377 | 1.26% | 35.7% |
| S3_XGB | 140204 | 1.87% | 39.3% |
| S4_MLP | 140248 | 2.23% | 25.0% |

## Oracle Capture(vs S0 Oracle)

| Selector | Capture Rate |
|----------|-------------|
| S1_FixedBest | -1.12% |
| S2_Rule | -1.50% |
| S3_XGB | -1.38% |
| S4_MLP | -1.41% |

## 判读(诚实报告)

### 结果排序: S2 Rule(1.26% regret) < S1 FixedBest(1.43%) < S3 XGB(1.87%) < S4 MLP(2.23%)

### 关键发现: **学习型 selector 未胜过 Fixed-Best**(总成本 S1 < S3 < S4)

- 与 R17 部署悖论一致:固定策略有隐式稳健性
- 56 训练期太小,学不出超越"E7 全局最优"的结构
- Paper 1 贡献 ≠ "selector 有效";贡献 = **"selector 何时值得做"**
- 与 WEPA-Natural(gap=0)共同构成"DWERP 部署边界"的证据
