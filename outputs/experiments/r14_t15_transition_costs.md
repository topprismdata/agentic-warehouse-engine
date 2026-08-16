# R14 — T1.5:C_move vs C_switch 拆分(SPEC v1.4 §3,Methodology Result)

**Date**: 2026-08-16T13:02:39.995030+00:00 | seeds = [7, 17, 27, 37, 97, 117] | beam = 20 | world = 120 SKU / 60 loc
**d(A,A_prev) 代理**: n_moves(SPEC v1.4 声明)| FalseSwitch 阈: moves <= 2;HiddenReconfig 阈: moves >= 20

## 两类代理失真(指示罚 1[expert_changed] 的缺陷)

| 条件 | False Switch(myopic) | False Switch(dynamic) | Hidden Reconfig(myopic) | Hidden Reconfig(dynamic) | mean gap |
|------|----------------------|----------------------|-------------------------|--------------------------|----------|
| move_only | 0/36 (0%) | 0/36 (0%) | 6/36 (17%) | 4/36 (11%) | 0.35% |
| switch_only(s=1) | 0/36 (0%) | 0/36 (0%) | 14/36 (39%) | 14/36 (39%) | 0.05% |
| switch_only(s=5) | 0/36 (0%) | 0/36 (0%) | 16/36 (44%) | 17/36 (47%) | 0.05% |
| switch_only(s=20) | 0/36 (0%) | 0/36 (0%) | 18/36 (50%) | 25/36 (69%) | 0.40% |
| both(m=1,s=5) | 0/36 (0%) | 0/36 (0%) | 7/36 (19%) | 7/36 (19%) | 1.10% |

- **False Switch** = 换了 expert 名但仓库几乎没动 —— 指示罚收取了物理上不存在的成本
- **Hidden Reconfig** = expert 没换但大量搬库 —— 指示罚漏掉真实成本

## 判读
- 若任一失真率显著(≥10% 的期次),则 **"algorithm-switch count is an inadequate
  surrogate for warehouse reconfiguration cost"** 成立 → 支持 C_transition =
  d(layout_t, layout_t+1) 的公式化(SPEC v1.4 §2)
- switch-only 条件下 gap 的变化 = 纯策略切换成本对 sequential 价值的贡献
- move-only vs both 的 gap 差 = 两种成本的交互

## 后续
T3 信息边界实验(anticipatory receding-horizon + CaptureRate)—— SPEC v1.4 §1。
