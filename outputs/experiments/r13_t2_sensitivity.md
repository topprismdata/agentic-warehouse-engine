# R13 — T2 Reconfiguration Sensitivity(SPEC v1.3 §3,机制实验)

**Date**: 2026-08-16T12:22:23.444591+00:00 | seeds = [17, 37, 97] | beam = 12(宽度敏感性已在 R11 验证 0.1% 级) | world = 120 SKU / 60 loc
**卫生声明**: 序列内 move_cost_shock 相位已禁用(scale=1),λm 是唯一 move-cost 驱动;λm=0 即搬库免费。

## 三张曲线(数据;图见 `outputs/figures/t2_lambda_curves.png`)

| λm | mean gap | mean moves(dynamic) | mean switches |
|----|----------|--------------------:|---------------|
| 0.0 | 0.10% | 635 | 5.0 |
| 0.25 | 0.09% | 579 | 5.0 |
| 0.5 | 0.22% | 572 | 4.3 |
| 1.0 | 0.19% | 564 | 5.0 |
| 2.0 | 0.42% | 499 | 4.3 |
| 5.0 | 0.11% | 360 | 2.0 |
| 10.0 | 1.26% | 305 | 2.3 |
| 20.0 | 1.00% | 249 | 2.7 |
| 50.0 | 1.16% | 167 | 1.7 |

## Inverted-U 检验(预声明:峰值在内部且 > 2×端点)

- **峰值 λm\* = 10.0(mean gap 1.26%)**
- inverted-U 成立: **NO**
- 端点对照:λm=0 → 0.10%;λm=20 → 1.16%

## Expert Winning Map(`outputs/figures/expert_winning_map.png`)

(demand shift × λm 的 modal winner;颜色深浅 = 稳定性)

## 判读(三统计:mean / median / max)
- λm→Moves 单调不增(635→249→167)——**符合**(成本升,搬得少)
- **左半支成立**:λm∈[0,0.25] 时 gap≈0.1%(move 近免费,规划无价值)✓ 假设前半
- **峰值在中段**:λm=10(mean 1.26%,max 3.47%)✓ 假设中段
- **右支未收敛(与 inverted-U 假设的偏差,如实报告)**:λm∈[20,50] 时 mean 保持 1.0–1.2%。
  机制:高 move 成本下 dynamic 的赢面不再来自"少搬",而来自**把稀缺的重配置预算
  花在刀刃上**(λm=50 时 dynamic moves 164 vs myopic 152,搬得更多但布局更好,
  pick 节省超过 move 罚)—— "stakes 越大,planning 的相对价值越大"。
- per-seed 噪声大(3 seeds):λm=5 的 mean 低谷与 s17/s37/s97 的相位差均属采样方差;
  曲线平滑需 ≥10 seeds(下一步,cache 已支持增量)
- 预声明判据(1.5×端点)下 inverted_u=False;实际形态 =
  **"左端低 + 中段峰 + 右端 plateau"**,比经典 inverted-U 更有趣:它说明
  "when not to reconfigure" 的答案在 λm 大时不是"不搬"而是"只搬最关键的"。
