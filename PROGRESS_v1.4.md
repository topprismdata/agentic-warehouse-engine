# Agentic Warehouse Engine — 进展与下一步计划 v1.4

**日期**: 2026-08-16(深夜)| **项目**: `~/projects/agentic-warehouse-engine/`
**性质**: 阶段性总结(取代 PROGRESS_v1.3 附录;数字以 `outputs/experiments/` 为准)
**规范链**: `SPEC_UPDATE_v1.4.md` > v1.3 > v1.2 > v1.1 > v1.0 PDF
**本版要点**: 审稿防御性实验(T1.5/T3/T4)完成;研究叙事从"机会存在"推进到
"朴素可部署策略捕获为零"—— 研究前沿被精确定位;发现并修复 oracle 非可采纳缺陷

---

## 1. 项目定位(未变,强化)

**DWERP** = π(S_t) → E_t → A_t, S_{t+1} = f(S_t, A_t, ξ_{t+1})。
**核心命题 "When NOT to reconfigure"**:真正困难的不是何时换更聪明的算法,
而是**何时忍住不做眼前看似正确的优化**。
论文题目候选:**When Not to Reconfigure: Sequential Expert Routing for
Dynamic Warehouse Slotting under Non-Stationary Demand**(中文:何时不应
重配置:非平稳需求下考虑物理重配置成本的仓储动态专家路由)。

## 2. 关卡全景(v1.4 终版状态)

| 关卡 | 问题 | 状态 | 关键数字 |
|------|------|------|---------|
| T0 Diversity | 最优 Expert 随状态切换? | ✅ GO | E7 占 52%,6 winners |
| T1a Existence | myopic 被严格支配存在? | ✅ YES | seed 17:TrapScore 26.3 |
| T1b Prevalence | trap 频率/条件? | ✅ 完成 | 保险型重尾;material 1/12;divergence 集中转变前夜 |
| T2 Sensitivity | λm 调制规划价值? | ✅ 完成 | 左低+中峰(λm=10)+右 plateau;"只搬最关键的" |
| **T1.5 代理失真** | 指示罚合格吗? | ✅ **不合格** | Hidden Reconfig **17–69%**(λs=20 时被 gaming 至 69%) |
| **T3 信息边界** | 可部署捕获多少? | ✅ **≈0%** | aware −0.2%(混合),blind 12/12 严格 0 |
| **T4 Trap 相图** | 什么条件造 trap? | ✅ 完成 | **Δt=1 中间导程全 M material**(1.26–1.69%);dynamic 廉价期预置 |
| Anticipatory v2 | 提升内部模型→capture>0? | ⬜ **下一步(最优先)** | — |

## 3. 论文三层主线(已完整成形)

1. **机会存在**:T1a(oracle gap 5.34% 构造证据)+ T4(可控网格复现 trap 带)
2. **朴素可部署捕获 ≈ 0**(T3):绑定约束 = **内部成本模型保真度**
   (线性 Σp50×dist 无 stop 结构 → 专家错排序),不是日程知识;
   附带发现:seed 17 上 greedyFC < 事后 myopic —— 预测"懒惰" = 隐式
   stickiness,部分规避 trap(连向 hysteresis/real-options 文献)
3. **代理失真**(T1.5):"algorithm-switch count is an inadequate surrogate
   for warehouse reconfiguration cost" → C_transition = d(L_t, L_{t+1})
   公式化的硬证据(且 λs 大时策略学会"换内容不换名"规避指示罚 —— gaming 证据)

三个受保护的机制(项目核心资产):
① 不同状态→不同 Expert 最优 ② 当前最优≠长期最优 ③ 重配置成本越重要,
"是否行动"本身成为决策变量(Option value of waiting)。

## 4. 本轮关键工程修复

**Y1:beam oracle 非可采纳**(REVIEW_v1.4 第一发现):
宽 20 的 oracle 在 seed 17 给 38106 > greedyFC 36444 —— 有限宽度会剪掉
后期才显优的轨迹。修复:统一 width 30,排序恢复;**制度化**:oracle 宽度
= 全仓声明常量,beam 只保证 ≤ myopic,不保证 ≤ optimum。所有引用 oracle
为"上界"的表述改为"近似上界(beam-limited)"。

## 5. 指标体系(已冻结,累计)

- 基础:NormalizedCost / L0 route / L1 flow
- 序列:OracleGap / Dynamic Regret / **CaptureRate** / Over-Reslotting / Policy Stability
- Trap:TrapScore / **NormalizedTrapGain(NTG)** / MaterialTrap(τ=1%)/ **LeadTimeToShock**
- 代理失真:**False Switch Penalty / Hidden Reconfiguration**
- 规划中:VPM / Marginal Move Quality(SPEC §6 欠账)
- 纪律:gap 类一律 mean/median/max 三统计;NaN 不美化

## 6. 三轮自审信用记录(累计 7 轮)

| 轮 | 重大捕获 |
|----|---------|
| v0.2 | 全知评估 + 容量违约 → 撤回 R02–R04 排名 |
| v0.4 | 空表过 validate → 事实表非空强制 |
| v1.2-T0 | move_cost_scale 未接线 → 重跑 |
| v1.2-T1 | CP-SAT 非确定性 → 全求解器 deterministic 化 |
| v1.3 | 微 trap 口径 + 判据静默修改(流程违规自曝) |
| **v1.4** | **beam oracle 非可采纳(宽 20 弱于 greedy)→ 统一 30 + 制度化**;capture 负值/NaN 如实保留 |

## 7. 资产清单

- 代码:~7600 行 Python(83 tracked files);确定性 CP-SAT;anticipatory
  receding-horizon;trap_analysis;beam(myopic 保底注入);cache-resume(R13/R16)
- 数据:Instacart(340 万订单，user 级切分);合成 regime 序列(28 天 8 相位)
  + controlled trap 网格(Δt×M)
- 实验报告:R01–R16 + REVIEW×7;图:t2_lambda_curves / expert_winning_map /
  trap_phase_diagram(论文三张核心图已有雏形)

## 8. 下一步计划(优先级序,导师路线)

### 8.1 Anticipatory v2(最优先 —— 冲着 capture≈0 去)
- 内部成本模型升级:**stop-count 感知**(订单级 route 近似,而非每行线性求和)
- H ∈ {1,2,3} 扫描 × schedule-aware/blind 双档
- 成功标准(预声明):aware capture 从 ~0 提到 **>20%**(哪怕只在高 headroom
  seeds);若仍为 0 → 论文叙事转为"朴素前瞻不足,需要 X(结构化内部模型/
  option-value 机制)",同样是有价值的负结果
- 关联:这直接决定 Selector 是"成本感知排序"还是"更根本的机制设计"

### 8.2 统计加固 + 欠账指标
- R16 网格补 seeds(2→6,cache 增量);R12/R13 补至 ≥10
- **VPM** = (FuturePickingSaving − MoveCost)/N_moves;**Marginal Move
  Quality**(dynamic 多做的 moves 净收益)—— 支撑 "Not fewer moves, better
  moves" 的量化
- λs>0 罚项用 d(layout) 重实现(替代指示罚)后,R13 曲线复核

### 8.3 WEPA-Natural / WEPA-Stress(数据可达性调研先行)
- Natural:纯真实 order stream(external validity:natural trap 存在吗?)
- Stress:真实几何/库存/订单 + 受控 promo·move-shock·reversal(mechanism
  validation);论文表述 = natural + controlled counterfactual,不混为一谈

### 8.4 Selector(最后)
- 输入:online-observable 状态变量(**禁 phase** —— known_at_time 原则延续)
- 方法:cost-sensitive Ĉ(E_i|S_t) 预测 + argmin(learning-to-rank 辅助),
  非纯分类;评价 = DynamicRegret / OracleGap
- 家族:Rule → XGBoost/LightGBM → MLP → LLM zero/few-shot → LLM+Solver-Feedback
  (LLM 殿后,不预设最优)

## 9. 风险与边界(诚实声明)

- 平台仍合成;WEPA 复核前 material-trap 频率不外推
- oracle 是 beam-limited 近似(宽 30);gap 均为保守下界
- 成本口径:C_pick + λm·C_move(λr/λc 未入;λs 已探索性拆分)
- T3 的 anticipatory v1 是**朴素实现**(线性内部模型 + 小 H);capture=0 的
  归因("模型保真度")是假设,8.1 的 v2 就是它的检验
- R16 网格 2 seeds 是扫描非推断;"带"的表述在补 seeds 前保持

## 10. 文件索引(本版新增)

```
SPEC_UPDATE_v1.4.md                      # 信息边界/过渡成本/题目(当前权威)
simulation/anticipatory.py               # 可部署前瞻策略(rolling + 双知情档)
scripts/run_r14_t15_transition_costs.py  # 代理失真
scripts/run_r15_info_boundary.py         # CaptureRate
scripts/run_r16_trap_phase_diagram.py    # 可控 trap 网格(cache)
outputs/experiments/r14/r15/r16_*.md     # 三份报告
outputs/figures/trap_phase_diagram.png   # 论文核心图 #3 雏形
outputs/experiments/REVIEW_v1.4.md       # Y1–Y6
```
