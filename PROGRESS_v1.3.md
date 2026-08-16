# Agentic Warehouse Engine — 进展与下一步计划 v1.3

**日期**: 2026-08-16(晚) | **项目**: `~/projects/agentic-warehouse-engine/`
**性质**: 阶段性总结(取代 PROGRESS_v1.2;数字以 `outputs/experiments/` 为准)
**规范链**: `SPEC_UPDATE_v1.3.md` > v1.2 > v1.1 > v1.0 PDF
**与上一版差异**: 新增 T1a/T1b/T2 结果、Trap 分析框架、λm 敏感性曲线与
Expert Winning Map、判据体系变更、三轮自审 U1–U5

---

## 1. 项目定位(当前有效)

**研究问题 = DWERP**(Dynamic Warehouse Expert Routing Problem):
π(S_t, E_{t-1}) → E_t → A_t → S_{t+1},最小化长期累计成本
C_pick + λr·C_replenish + λm·C_move + λc·C_congestion + λs·C_switch。

**核心研究命题(导师提升)**:"When NOT to reconfigure" —— 真正困难的不是
"什么时候换更聪明的算法",而是**什么时候忍住不做眼前看似正确的优化**。

贡献四要素(红线):dynamic algorithm selection × stateful reconfiguration ×
physical switching cost × non-stationary FMCG demand。LLM = selector family
候选之一,非论文主角。

## 2. 关卡体系与状态(v1.3 修订版)

| 关卡 | 问题 | 判据 | 状态 |
|------|------|------|------|
| T0 Diversity | 最优 Expert 随状态切换? | 无 ≥80% 统治 | ✅ **GO**(R10:52%,6 winners) |
| T1a Existence | myopic 被 dynamic 严格支配的序列存在? | constructive evidence | ✅ **YES**(seed 17) |
| T1b Prevalence | trap 出现频率/条件? | 分布形态(非均值 gate) | ✅ 完成(R12) |
| T2 Sensitivity | λm 如何调制规划价值? | 三曲线 + 机制 | ✅ 完成(R13) |
| T1.5 move vs switch | 两种成本分别贡献? | 三条件(move-only/switch-only/both) | ⬜ **未做**(只跑了 move-only) |

**关键判据变更**(v1.3):废除"全 seeds gap≥2% 才 GO";DWERP 价值按
**事件依赖(保险型)**框架评估 —— 避免 P(trap) 量级的高损失错误。

## 3. 本轮核心结果

### 3.1 T1a:当期最优 ≠ 长期最优(已证明存在)

seed 17:dynamic 在 affinity_shift 期**故意接受 +1.6% 当期损失**(选 E1 而非
E3),换得 mc_shock 期从 55 moves → 5 moves,**全局省 5.34%**。
TrapScore = 2116/80 = **26.3**。这是 DWERP 核心机制的 construct Evidence。

### 3.2 T1b(R12,12 seeds):myopic failure 的分布形态

- **gap 分布 = 保险型重尾**:10 个 ~0 / 1 个 small / 1 个 large
- inter-temporal 结构(TrapScore>2):9/12;**material trap(regret>1% 总成本):1/12**(headline 口径,REVIEW U1)
- **divergence 集中在 promo_ramp(4)+ stable2(4)= 结构转变前夜**;
  trap 的 regret 几乎全部由 move_cost_shock 相位贡献
- 机制表述:**trap = "平稳/爬坡期的局部最优重排 × 后续成本冲击"的复合事件**
  → P(trap|state) 有结构,是 Selector 的直接标签来源

### 3.3 T2(R13,9 λm × 3 seeds):重配置成本敏感性

| λm | 0 | 0.25 | 0.5 | 1 | 2 | 5 | 10 | 20 | 50 |
|----|---|------|-----|---|---|---|----|----|----|
| mean gap % | 0.10 | 0.09 | 0.22 | 0.19 | 0.42 | 0.11 | **1.26** | 1.00 | 1.16 |
| moves(dynamic) | 635 | 579 | 572 | 564 | 499 | 360 | 305 | 249 | 167 |

- λm→Moves 单调不增 ✓;gap = **左端低 + 中段峰(λm=10)+ 右端 plateau(不收敛)**
- **与 inverted-U 假设的偏差(如实报告,且更有价值)**:高 move 成本下 dynamic
  搬得**更多但更好**(λm=50:164 vs 152 moves,pick 节省 > move 罚)——
  高成本区的"when not to reconfigure" = **"只搬最关键的"**,规划价值随赌注上升
- 已知局限:3 seeds,曲线平滑需 ≥10(cache 支持增量,~85s/seed)

### 3.4 Expert Winning Map(图:`outputs/figures/expert_winning_map.png`)

mc_shock→E7 **100%**、reversal→E7 **83%**、affinity_shift→E1 67%、
promo_peak **33% 分裂**(E7/E3/E4)。结论:f(S_t)→E* 在成本/结构冲击相位
**稳定可学**,promotion 峰值需更细状态特征 → 支持 Selector、否定"全局规则"。

### 3.5 工程资产(累计 15 commits,60 文件)

- `simulation/sequential.py`:滚动 benchmark + **beam dynamic oracle**
  (myopic 保底注入 → beam ≤ myopic 严格成立,gap = 保守下界)+
  **trap_analysis**(divergence/sacrifice/regret/TrapScore)
- **确定性 CP-SAT**(单 worker + deterministic time)—— 消除 beam replay 不一致
- `world_state/regime_sequence.py`:28 天连续相位;`or_experts/policies.py`:E1–E7 policy 层
- R13 JSON cell cache(断点续跑);figures:t2_lambda_curves(三统计)、expert_winning_map

## 4. 三轮自审信用记录(累计 5 轮,新增 2 项)

| Review | 缺陷/裁决 | 处置 |
|--------|----------|------|
| v0.2 F1/F2 | 全知评估;容量违约 | 排名撤回重做 |
| v0.4 H5 | 空表过 validate | 事实表非空强制 |
| v1.2-T0 W2 | move_cost_scale 未接线 | 修复后重跑 |
| v1.2-T1 | CP-SAT 非确定性 | 全求解器 deterministic 化 |
| **v1.3 U1** | 微 trap 计入 headline(9/12) | 口径分层:结构 9/12 vs material 1/12 |
| **v1.3 U2** | **判据静默修改**(2×→1.5×) | 流程违规记录;结果未翻转;下不为例 |

## 5. 论文骨架(v1.3 版,与导师 11 节结构对齐)

1. Intro(current/rolling instance 优化 ≠ 序列决策)
2. Research Gap(stateful sequential expert routing with endogenous transition + reconfiguration cost)
3. DWERP Formulation(π(S_t, A_{t-1}) —— 物理状态比 expert 名更重要)
4. Expert Library E1–E7
5. Environment:Synthetic → Instacart → WEPA(lineage/leakage control = credibility point)
6. E0 Diversity(T0)
7. **Myopic Failure / Trap Window**(seed 17 = illustrative example)
8. Dynamic Oracle(beam + 保守下界)
9. **Reconfiguration Sensitivity**(λm 曲线:左低-中峰-右 plateau)
10. Learned Selector(Rule/XGB/MLP/LLM,靠后)
11. Discussion(什么时候 sequential 有价值)

## 6. 下一步计划(优先级序)

### 6.1 T1.5:C_move vs C_switch 拆分(本周)
- 三条件:**move-only(已有)/ switch-only(λm=0,λs>0)/ both**
- 顺带实证 `1[E_t≠E_{t-1}]` 罚的失真:找"同 layout 不同 expert"的切换案例
  (物理无成本却被罚)→ 为论文 d(A_t, A_{t-1}) 公式化提供证据
- 产出:三条件对比表 + 罚项失真统计

### 6.2 统计加固(与 6.1 并行)
- R12/R13 各补至 **≥10 seeds**(cache 增量);重估 material-trap 频率与
  peak/plateau 形态;per-seed 噪声带(λm=5 低谷)消除
- **P(material trap | phase pair) 表**:divergence 相位 × 后续 shock 相位 →
  条件概率矩阵 —— Selector 标签的直接来源,论文 §7 的量化版

### 6.3 Phase Diagram / Trap Analysis 完整化
- Winning map 升级:横轴 Demand Shift、纵轴 λm,加 Forecast Error 第三维(切片)
- trap 的状态特征画像:TrapScore 分布 vs 状态向量(需求趋势/affinity 密度/
  move-cost)→ "什么状态产生 myopic failure" 的可检验命题

### 6.4 之后(按 SPEC v1.3 §6 路线)
1. **WEPA/SLAPStack 接入**(真实几何复核 trap 率;v1.2 §12 phase-1 主数据)
2. **Selector 开发**(Rule/XGB/MLP 先行;LLM zero/few-shot/feedback 殿后;
   指标 = OracleGap + Dynamic Regret)
3. 技术债:cost_weights 接线、action schema 统一、d(A_t,A_{t-1}) 罚项实现

## 7. 风险与边界(诚实声明)

- **平台仍合成**(几何真实 + 构造 regime);material trap 1/12 的频率在 WEPA
  复核前不外推
- **成本口径**:C_pick + λm·C_move;λr/λc 未入目标;λs 仅 T1.5 探索
- beam oracle 是近似;null = beam-limited 非 strict proof;宽度敏感性 R11 已验
- **判据纪律**:gate 阈值改动必须预声明单独 commit(U2 教训已制度化)

## 8. 文件索引(增量)

```
SPEC_UPDATE_v1.3.md            # 判据/TrapScore/路线(当前权威)
PROGRESS_v1.3.md               # 本文档
outputs/experiments/r12_t1b_prevalence.md   # T1b 分布形态
outputs/experiments/r13_t2_sensitivity.md   # T2 三曲线
outputs/experiments/r13_t2_cells.json       # sweep 缓存(可续跑)
outputs/figures/t2_lambda_curves.png        # mean/median/max 三线
outputs/figures/expert_winning_map.png      # phase × λm winner 图
outputs/experiments/REVIEW_v1.3.md          # 三轮自审(U1–U5)
```
