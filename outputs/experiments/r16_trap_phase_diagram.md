# R16 — T4 Controlled Trap Phase Diagram(SPEC v1.4 §5)

**Date**: 2026-08-16T14:09:51.381076+00:00 | seeds = [17, 97] | beam = 12 | world = 120 SKU / 60 loc
**序列**: warmup(4d)→transition(3d affinity-remap)→gap(Δt)→shock(3d,move-cost ×M)→tail(1d);NTG = (C_my − C_dy)/C_my(全评估视野)

## NTG 网格(rows = Δt = LeadTimeToShock,cols = shock magnitude)

| Δt | M | NTG | material trap(>1%) | my moves@transition | my moves@shock | dy moves@shock |
|----|---|-----|--------------------|--------------------|----------------|----------------|
| 0 | ×2 | 0.36% | — | 0 | 58 | 58 |
| 0 | ×5 | 0.08% | — | 0 | 56 | 52 |
| 0 | ×10 | 0.31% | — | 0 | 42 | 43 |
| 0 | ×20 | 1.34% | **TRAP** | 0 | 30 | 27 |
| 1 | ×2 | 1.26% | **TRAP** | 0 | 67 | 35 |
| 1 | ×5 | 1.48% | **TRAP** | 0 | 28 | 28 |
| 1 | ×10 | 1.69% | **TRAP** | 0 | 24 | 22 |
| 1 | ×20 | 1.58% | **TRAP** | 0 | 12 | 12 |
| 2 | ×2 | 0.25% | — | 0 | 48 | 49 |
| 2 | ×5 | 0.71% | — | 0 | 36 | 38 |
| 2 | ×10 | 0.56% | — | 0 | 26 | 28 |
| 2 | ×20 | 0.84% | — | 0 | 18 | 18 |
| 4 | ×2 | 0.13% | — | 0 | 88 | 64 |
| 4 | ×5 | 0.20% | — | 0 | 52 | 52 |
| 4 | ×10 | 0.20% | — | 0 | 43 | 43 |
| 4 | ×20 | 0.10% | — | 0 | 30 | 30 |

**热力图**: `outputs/figures/trap_phase_diagram.png`

## 判读(先验:短 Δt × 大 M = trap 区域)
- 观察 trap 区域的实际边界与 NTG 梯度:Δt 变大(离 shock 远)→ myopic 的错误重配有更多
  时间摊销 → NTG 下降;M 变大 → 同样错误更贵 → NTG 上升
- my_shock_moves vs dy_shock_moves:dynamic 在 shock 期的"少搬/搬得准"签名
- 本图回答的是科学问题(什么条件组合产生 inter-temporal trap),不依赖随机 seed 运气
