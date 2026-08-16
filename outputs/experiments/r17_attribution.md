# R17 — 归因实验:为什么 capture≈0(SPEC v1.5 §3.1)

**Date**: 2026-08-16T16:40:06.926660+00:00 | seeds = [17, 37, 97, 117] | RHC beam = 8 | BFIP beam = 30 | world = 120 SKU
**设计**: 固定 warehouse trajectory,仅换内部成本模型(L1 线性 / L2 stop-aware / L3 route 代理)× H ∈ (1, 2, 3, 7);每级记 RankingFidelity(ρ/τ)+ Top-1 hit + CaptureRate(vs BFIP)

## 结果(model × H)

| model | H | schedule | Spearman ρ | Top-1 hit | CaptureRate |
|-------|---|-----------|-----------|-------------|
| L1_linear | 1 | aware | +0.73 | 39% | +43.4% |
| L1_linear | 1 | blind | +0.73 | 39% | +43.4% |
| L1_linear | 2 | aware | +0.75 | 43% | +43.4% |
| L1_linear | 2 | blind | +0.73 | 39% | +43.4% |
| L1_linear | 3 | aware | +0.75 | 43% | +33.5% |
| L1_linear | 3 | blind | +0.73 | 39% | +43.4% |
| L1_linear | 7 | aware | +0.75 | 43% | +43.4% |
| L1_linear | 7 | blind | +0.75 | 43% | +44.2% |
| L2_stopaware | 1 | aware | +0.52 | 43% | -57.0% |
| L2_stopaware | 1 | blind | +0.52 | 43% | -57.0% |
| L2_stopaware | 2 | aware | +0.52 | 43% | +4.4% |
| L2_stopaware | 2 | blind | +0.52 | 43% | -59.1% |
| L2_stopaware | 3 | aware | +0.51 | 46% | +4.4% |
| L2_stopaware | 3 | blind | +0.52 | 43% | -59.1% |
| L2_stopaware | 7 | aware | +0.51 | 46% | +4.4% |
| L2_stopaware | 7 | blind | +0.52 | 43% | -59.1% |
| L3_route | 1 | aware | +0.62 | 43% | +24.6% |
| L3_route | 1 | blind | +0.62 | 43% | +24.6% |
| L3_route | 2 | aware | +0.62 | 43% | +24.6% |
| L3_route | 2 | blind | +0.62 | 43% | +24.6% |
| L3_route | 3 | aware | +0.62 | 43% | +24.6% |
| L3_route | 3 | blind | +0.62 | 43% | +24.6% |
| L3_route | 7 | aware | +0.62 | 43% | +24.6% |
| L3_route | 7 | blind | +0.62 | 43% | +24.6% |

## RF → Capture 曲线
`outputs/figures/rf_capture.png`

## 归因判读(预声明框架)
- 若 ρ 随模型升级上升且 capture 同步上升 → **cost-model error 是绑定约束**
  (SPEC v1.5 核心假设:sequential opportunity 需要内部模型保持候选相对排序)
- 若 ρ 高但 capture 仍 ~0 → 绑定约束转向 **horizon insufficiency**(H 不够)
  或 forecast error;H 扫描行给出 horizon 维度
- 若 L3(与真实度量同构)capture 仍为 0 → 剩余差距 = forecast error +
  BFIP 的 clairvoyance 不可弥补部分
