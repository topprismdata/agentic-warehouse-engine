# R18 — 小实例精确全信息 Oracle(SPEC v1.5 §3.2)

**Date**: 2026-08-16T17:01:12.590440+00:00 | 实例 = 60 SKU / 30 loc / 5 期 | seeds = [17, 42, 107, 37] | 变体 = shock

## 目的
在可穷举的小实例上求出真最优轨迹(exhaustive enumeration,含剪枝),
量化 beam-30 与真最优的差距,并将 trap 机制升级为 exact constructive evidence。

## 结果

| seed | variant | C_myopic | C_beam30 | **C_exact** | gap beam→exact | gap myopic→exact | 排序 |
|------|---------|----------|----------|-------------|----------------|------------------|------|
| 17 | shock | 4324 | 4305 | 4305 | 0.00% | 0.46% | OK |
| 42 | shock | 3526 | 3452 | 3452 | 0.00% | 2.13% | OK |
| 107 | shock | 3865 | 3835 | 3835 | 0.00% | 0.77% | OK |
| 37 | shock | 4404 | 4289 | 4289 | 0.00% | 2.68% | OK |

- mean gap beam→exact: **0.00%**
- mean gap myopic→exact: **1.51%**
- C_exact ≤ C_beam ≤ C_myopic 全部成立: **YES**

## 轨迹对比
- seed 17: exact=E2 → E5 → E7 → E7 | beam=E2 → E5 → E7 → E7 | myopic=E2 → E6 → E7 → E1
- seed 42: exact=E3 → E1 → E7 → E7 | beam=E3 → E1 → E7 → E7 | myopic=E3 → E5 → E7 → E7
- seed 107: exact=E3 → E4 → E7 → E1 | beam=E3 → E4 → E7 → E1 | myopic=E3 → E1 → E7 → E1
- seed 37: exact=E1 → E6 → E7 → E4 | beam=E1 → E6 → E7 → E4 | myopic=E1 → E2 → E7 → E7

## 判读
- gap beam→exact = 0.00% → beam-30 是 可靠 的真最优代理
- 若 exact 轨迹与 beam 轨迹不同但成本差 <1% → 多个近优轨迹存在(平坦盆地),beam 的具体选择不重要
- myopic→exact gap 的大小 = 该小实例上 trap 机会的直接度量
