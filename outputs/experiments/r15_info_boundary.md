# R15 — T3 信息边界:可部署策略能否捕获 inter-temporal 机会(SPEC v1.4 §1)

**Date**: 2026-08-16T13:58:47.695422+00:00 | seeds = 12 | H = 2 | oracle beam = 30 | world = 120 SKU / 60 loc
**Anticipatory 内部成本模型**: Σ p50×dist 线性代理(部署者拿不到 realized TSP;模型失配是问题的一部分)

## 信息体制阶梯(cost:oracle ≤ 可部署 ≤ 贪心)

| seed | greedyFC(H=1) | ant H=2 aware | ant H=2 blind | myopic(ex-post) | oracle(ex-post) | Capture aware | Capture blind |
|------|---------------|----------------------|----------------------|-----------------|------------------|---------------|---------------|
| 7 | 31033 | 31033 | 31033 | 30597 | 30523 | 0.0% | 0.0% |
| 17 | 36444 | 36444 | 36444 | 38106 | 36070 | 0.0% | 0.0% |
| 27 | 32011 | 32011 | 32011 | 31794 | 31766 | 0.0% | 0.0% |
| 37 | 33818 | 33775 | 33818 | 33264 | 33180 | 6.7% | 0.0% |
| 47 | 36328 | 36328 | 36328 | 36055 | 36055 | 0.0% | 0.0% |
| 57 | 35581 | 35581 | 35581 | 35380 | 35342 | 0.0% | 0.0% |
| 67 | 36873 | 36897 | 36873 | 37010 | 36873 | nan% | nan% |
| 77 | 34451 | 34451 | 34451 | 33740 | 33667 | 0.0% | 0.0% |
| 87 | 37597 | 37597 | 37597 | 36839 | 36804 | 0.0% | 0.0% |
| 97 | 30837 | 30900 | 30837 | 29923 | 29825 | -6.2% | 0.0% |
| 107 | 39630 | 39682 | 39630 | 39274 | 39160 | -11.1% | 0.0% |
| 117 | 32306 | 32269 | 32306 | 32216 | 31862 | 8.3% | 0.0% |

- mean: greedyFC=34742 | aware=34747 | blind=34742 | myopic=34516 | oracle=34261
- **mean CaptureRate: aware = -0.2%,blind = 0.0%**
- oracle headroom 为正的 seeds:11/12(其余 seed oracle≈greedy,分母≈0,capture 无意义)

## Trajectories(greedyFC / anticipatory-aware / anticipatory-blind)

| seed | greedyFC | ant aware | ant blind |
|------|----------|-----------|-----------|
| 7 | E7 → E7 → E7 → E7 → E7 → E7 → E7 | E7 → E7 → E7 → E7 → E7 → E7 → E7 |E7 → E7 → E7 → E7 → E7 → E7 → E7 |
| 17 | E7 → E7 → E7 → E7 → E7 → E7 → E7 | E7 → E7 → E7 → E7 → E7 → E7 → E7 |E7 → E7 → E7 → E7 → E7 → E7 → E7 |
| 27 | E7 → E7 → E7 → E7 → E7 → E7 → E7 | E7 → E7 → E7 → E7 → E7 → E7 → E7 |E7 → E7 → E7 → E7 → E7 → E7 → E7 |
| 37 | E7 → E7 → E7 → E7 → E7 → E7 → E7 | E7 → E7 → E6 → E7 → E7 → E7 → E7 |E7 → E7 → E7 → E7 → E7 → E7 → E7 |
| 47 | E7 → E7 → E7 → E7 → E7 → E7 → E7 | E7 → E7 → E7 → E7 → E7 → E7 → E7 |E7 → E7 → E7 → E7 → E7 → E7 → E7 |
| 57 | E7 → E7 → E7 → E7 → E7 → E7 → E7 | E7 → E7 → E7 → E7 → E7 → E7 → E7 |E7 → E7 → E7 → E7 → E7 → E7 → E7 |
| 67 | E7 → E7 → E7 → E7 → E7 → E7 → E7 | E7 → E7 → E7 → E7 → E7 → E6 → E7 |E7 → E7 → E7 → E7 → E7 → E7 → E7 |
| 77 | E7 → E7 → E7 → E7 → E7 → E7 → E7 | E7 → E7 → E7 → E7 → E7 → E7 → E7 |E7 → E7 → E7 → E7 → E7 → E7 → E7 |
| 87 | E7 → E7 → E7 → E7 → E7 → E7 → E7 | E7 → E7 → E7 → E7 → E7 → E7 → E7 |E7 → E7 → E7 → E7 → E7 → E7 → E7 |
| 97 | E7 → E7 → E7 → E7 → E7 → E7 → E7 | E7 → E7 → E7 → E6 → E7 → E7 → E7 |E7 → E7 → E7 → E7 → E7 → E7 → E7 |
| 107 | E7 → E7 → E7 → E7 → E7 → E7 → E7 | E7 → E7 → E7 → E6 → E7 → E4 → E7 |E7 → E7 → E7 → E7 → E7 → E7 → E7 |
| 117 | E7 → E7 → E7 → E7 → E7 → E7 → E7 | E7 → E7 → E7 → E7 → E7 → E4 → E7 |E7 → E7 → E7 → E7 → E7 → E7 → E7 |

## 判读(回应审稿人"凭什么知道明天搬库变贵")
- **schedule-aware**: 已排期成本(tariff/labor calendar)是合法 Information_t;
  capture 高 → 机会主要来自可预知日程
- **schedule-blind**: 假设当前成本持续(纯 surprise shock);capture 低 →
  机会依赖不可预知冲击时,DWERP 仍需 robustness/option-value 机制
- greedyFC vs myopic(ex-post)的差 = 贪心 oracle 的"作弊量";本实验的可部署
  基线是 greedyFC(不是 ex-post myopic),CaptureRate 以它为分母
- 已知限制:H=2 的前瞻窗覆盖 mc_shock 需 Δt≤H;更优 anticipatory
  (probabilistic shock model / option-value hold)是后续工作,当前结果为
  **下界**意义上的可部署性证据

## 与 T1a/T1b 的衔接
seed 17(oracle gap 5.34%)在本表中的 capture 见明细行 —— 它回答:
"知道日程的部署者能拿到多少;不知道的损失多少"。
