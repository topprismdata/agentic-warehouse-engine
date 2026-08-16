# R11 — T1 Myopic vs Dynamic Oracle(v1.2 §3,序列协议,λs=0)

**Date**: 2026-08-16T11:13:45.392004+00:00 | seeds = [7, 17, 27, 37, 47] | beam = 30 | world = 120 SKU / 60 loc
**口径**: mc_unit 锚定冷启动 layout(trajectory 无关);myopic 与 beam 共用同一 benchmark 实例与评估函数(单一记账权威)

## 方法
- Myopic Oracle:逐期事后 argmin(含当期 move 罚;路径依赖 rollout)
- Dynamic Oracle(近似):宽度 30 beam search,**myopic trajectory 每层注入保底** → beam ≤ myopic 严格成立;报告的 gap 是真实 oracle gap 的**保守下界**(beam 更优 x% 即证明 oracle ≥ x%)
- 判据(预先声明):GO = 全 seeds gap ≥ 2%;NO-GO = 全 seeds < 0.5%;之间 BORDERLINE(先加宽 beam 再定)

## 结果

| seed | myopic total | beam total | gap | fixed-best | Σmoves my/dy | switches my/dy |
|------|-------------|------------|-----|------------|--------------|----------------|
| 7 | 30597 | 30523 | **0.24%** | E7_Joint(30952) | 415/437 | 4/6 |
| 17 | 38106 | 36070 | **5.34%** | E7_Joint(38455) | 515/460 | 6/6 |
| 27 | 31794 | 31766 | **0.09%** | E7_Joint(31894) | 422/423 | 4/4 |
| 37 | 33263 | 33180 | **0.25%** | E7_Joint(33576) | 427/424 | 5/5 |
| 47 | 36054 | 36054 | **0.00%** | E7_Joint(36558) | 506/506 | 3/3 |

**mean gap = 1.18%**(全 seeds: 0.24%, 5.34%, 0.09%, 0.25%, 0.00%)

## Trajectories(myopic vs beam)

| seed | myopic | beam(dynamic) |
|------|--------|---------------|
| 7 | E1 → E3 → E7 → E1 → E7 → E7 → E7 | E1 → E3 → E7 → E1 → E7 → E4 → E7 |
| 17 | E1 → E5 → E4 → E6 → E7 → E3 → E7 | E1 → E5 → E4 → E6 → E7 → E1 → E7 |
| 27 | E7 → E7 → E7 → E6 → E7 → E1 → E7 | E7 → E7 → E6 → E6 → E7 → E1 → E7 |
| 37 | E6 → E7 → E1 → E7 → E1 → E1 → E7 | E6 → E7 → E1 → E1 → E7 → E1 → E7 |
| 47 | E1 → E4 → E3 → E3 → E7 → E7 → E7 | E1 → E4 → E3 → E3 → E7 → E7 → E7 |

## Beam-width 敏感性(seed 7)

| width | total |
|-------|-------|
| 8 | 30597 |
| 30 | 30523 |
| 80 | 30296 |

- spread(最大-最小)/best = **0.993%**(≤0.3% 视为收敛)

## Gates
- beam ≤ myopic(全 seeds,内部 assert): **PASS**
- beam-width 收敛: **WARN**(0.993%)
- **T1 verdict: BORDERLINE**

## 判读
- **BORDERLINE**:2%/0.5% 之间 → 加宽 beam/加 seeds 后复跑再定。
- Over-Reslotting(v1.2 §8):若 myopic Σmoves > dynamic Σmoves 且 gap>0,即贪婪过度重配置的直接证据(逐行见上表)。
- 口径变更声明:mc_unit 从 R10 的 myopic-path 锚定改为冷启动锚定(beam 可比性要求);myopic 数字与 R10 有微小差异,以本报告为准。
