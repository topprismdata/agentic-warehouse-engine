# SPEC UPDATE v1.1 — 研究方向增量更新(强制)

**日期**: 2026-08-16 | **性质**: 旧设计文档(v1.0 PDF)继续作为产品架构与资料库;**研究开发优先级已变更**。本文件优先级高于 v1.0 中与之冲突的一切内容。

> **最重要的一句话**:当前不要实现"大而全"的 Agentic Warehouse Decision Engine;
> 首先围绕 Paper 1 建立 **Dynamic Slotting OR Expert Benchmark**,验证不同
> warehouse states 下 Expert ranking 是否发生显著切换。**只有该假设成立后,
> 才开发 Agentic Selector。**

---

## 1. 沿用 v1.0 的部分

- **Warehouse World State**(S_t = Orders/Demand/Forecast/Inventory/Locations/Labor/Equipment/Tasks/Constraints)— 已落地为 9 表 canonical schema
- **数据与 Benchmark 基础**: WEPA/SLAPStack, Instacart, Favorita/M5, SLAPRP, Real Warehouse Dataset
  - **论文第一阶段优先 WEPA/SLAPStack + controlled demand perturbation**;其余作补充验证,不一开始拼复杂 synthetic dataset
  - 本仓现状:Instacart 已接入(R07/R08,Track B 补充验证);WEPA/SLAPStack 待接入(Go/No-Go 通过后)
- **工具栈**: OR-Tools/CP-SAT, MILP, heuristic/local search, SimPy, SLAPStack, SLAPRP, Digital Twin

## 2. 废弃/修正的旧假设

| 废弃 | 修正为 |
|------|--------|
| 固定 Multi-Agent 拆分(Forecast Agent / Slotting Agent / Routing Agent / …) | **业务模块 ≠ Agent 边界**;按问题动态组合 Skills/Solvers |
| LLM 自由生成数学模型并直接执行 | LLM = Problem Formulator + **OR Expert Selector** + Hypothesis Generator;候选 formulation 必须过 Solver 验证 |
| Digital Twin 是最终 Judge | **三重验证**: Solver Verification + Historical Replay + Counterfactual Simulation;Digital Twin 只是 Counterfactual Evaluator |

## 3. 最新架构(权威)

```
BUSINESS OBJECTIVE → WAREHOUSE WORLD STATE → REASONING/DIAGNOSIS
→ PROBLEM FORMULATION → OR EXPERT LIBRARY → SOLVER EXECUTION
→ VERIFICATION LAYER (Solver+Replay+Sim, Reject/Refine) → EXECUTION (WMS/WES)
→ ACTUAL OUTCOME → MEMORY/LEARNING
```

## 4. 产品与论文拆分

- **产品**: Agentic Warehouse Decision Engine,按 v1.0 总体架构长期演进
- **Paper 1(当前唯一研究焦点)**: *Agentic Dynamic Slotting with Solver-Verified OR Expert Selection under Non-Stationary FMCG Demand*
- **研究问题**: 不同需求 regime 下,不同 Slotting 方法是否存在**实例级**性能差异?若存在,读 Warehouse State 动态选 Expert 的 Selector 能否比固定 Expert 更低长期成本,并逼近 ex-post Oracle?

**Paper 1 明确不做**:自动发现"这是 Routing 还是 Replenishment 还是 Slotting 问题"(Paper 3)。Paper 1 已知问题域 = Dynamic Slotting,只判断"当前状态用哪个 Slotting Expert"。

## 5. OR Expert Library v1(固定七类)

| ID | Expert | 本仓状态 |
|----|--------|---------|
| E1 | Static ABC(历史 pick freq) | ✅ b1_static_abc |
| E2 | COI(cube-per-order) | ✅ b2_coi(volume 合成,声明) |
| E3 | Affinity(co-pick/basket) | ✅ b3_affinity |
| E4 | Forecast Dynamic ABC(未来需求) | ⬜ 本轮实现 |
| E5 | Robust(forecast uncertainty) | ⬜ 本轮实现 |
| E6 | Forecast + Affinity 联合 | ⬜ 本轮实现(CP-SAT) |
| E7 | Rolling-Horizon(pick+replenish+relocate) | ⬜ 本轮实现简化版(move-cost 罚项;完整多期滚动留 Step 10) |

## 6. 两个特殊 Selector(benchmark 组成)

- **Fixed-Best**:训练/验证整体最优 Expert,全状态固定使用 — **最重要 baseline**
- **Oracle Selector**:事后跑全部 E_1..E_7,每状态选真实最低成本;不可部署,给出上界
- 核心指标: **OracleGap = (Cost_Selector − Cost_Oracle) / Cost_Oracle**;Regret_t = Cost(E_selected,S_t) − Cost(E_oracle,S_t)

## 7. Selector 对比矩阵(不预设 LLM 最优)

Rule-based / XGBoost/LightGBM / MLP / LLM zero-shot / LLM few-shot / LLM+Solver-Feedback。
真正的research question:**在什么状态复杂度下 LLM reasoning 产生额外价值?**(XGBoost 更好也是有效结论)

## 8. Warehouse State v1(Selector 输入特征)

结构化特征而非原始订单:X_t = [DemandTrend, DemandCV, PromotionIntensity, VelocityShift,
ForecastError, ForecastUncertainty, AffinityDensity, AffinityShift, InventoryImbalance,
StockoutRisk, Occupancy, Congestion, ReplenishmentPressure, MoveCost, ExpectedPayback]

## 9. Demand Regimes(实验关键,人为构造并标记)

| Regime | 内容 | 预期最优 |
|--------|------|---------|
| R1 Stable | 稳定需求 | ABC/E1 |
| R2 Promotion Shock | 中腰 SKU demand ×3~10 | Forecast/E4 |
| R3 Velocity Reversal | A 类渐变 C,C 渐变 A | Forecast/E4 |
| R4 Affinity Shift | 共购关系重组 | Affinity/E3 |
| R5 Forecast Uncertainty | 预测误差 10/20/40% | Robust/E5 |
| R6 Move-Cost Shock | relocation cost 上升 | Static/E1(不值得搬) |
| R7 Capacity/Labor Shock | 可用库位/人员下降 | 视容量压力 |

**这是检验"Expert ranking 是否真随 state 改变"的机制。**

## 10. Go/No-Go 实验(Step 4,先于一切 Selector 开发)

对大量 state S_1..S_n 跑全部 E_1..E_7,得 Cost(E_i, S_j):
- 若某 Expert 在 ≥95% 场景最优 → **Selector 研究问题不成立(No-Go)**
- 若出现可解释的切换模式(Stable→ABC, Promotion→Forecast, AffinityShift→Affinity,
  HighError→Robust, HighMoveCost→Static)→ **Go**,才开发 Selector

## 11. 评价指标

- 主: Realized Warehouse Cost C = C_pick + λ_r·C_replenish + λ_m·C_relocation + λ_c·C_congestion
  - 本仓现状:仅 C_pick(L0/L1);replenish/relocate/congestion 分量随 E7/R6/R7 完整化逐步加入,λ 权重接线(原 F7)
- 辅: Picking Distance / Replenishment Distance / Relocation Distance / #Moves /
  Order Completion Time / Service Level / Constraint Violations / Slot Stability
- Selector: Selection Accuracy / Regret / Oracle Gap / Fixed-Best Improvement

## 12. Ablation 预留

No Forecast / No Affinity / No Solver Feedback / No Historical Replay /
No Demand Regime Features / No Memory

## 13. 开发顺序(权威,替代旧路线图)

1. Warehouse Simulator ✅(SimPy L1,R04;升级随 regimes 需要)
2. 统一实现 7 个 OR Experts ⬜(缺 E4/E5/E6/E7 — 本轮)
3. 生成 Demand Regimes ⬜(R1–R7 — 本轮)
4. **Expert Ranking Stability(Go/No-Go)** ⬜(本轮,R09)
5. 确认 Expert 会随 state 切换(若 No-Go → 停,报告)
6. 构造 Oracle labels
7. Rule / XGBoost / MLP Selector
8. LLM Selector(zero/few-shot)
9. Solver Feedback
10. 长期 rolling-horizon evaluation

## 14. 本仓已有资产 → 新路线的映射

| 资产 | 新路线中的角色 |
|------|---------------|
| canonical schema + validate + 容量审计 | Step 1 的 World State 基座 ✅ |
| SimPy replay(L1 flow time) | Step 1 Simulator ✅ |
| E1/E2/E3 + B4 CP-SAT(λ=0) | E1/E2/E3 即用;B4 框架升级为 E6 |
| R05 honest protocol(时间切分/审计/非空 validate) | 一切 Expert 评估的强制纪律 ✅ |
| R07 Instacart / R08 多切分 | Track B 补充验证;结论格式(mean±std+全胜)沿用 |
| R06 Execution Gateway | Verification 层执行端(暂挂,Step 9+ 复用) |
| REVIEW 三轮自审规则 | 继续强制 ✅ |

**平台声明(务实边界)**:本轮 Go/No-Go pilot 在合成平台(真实几何 + Zipf + basket 结构
+ controlled regimes)上执行 — 构造性极端 regime 下若仍无切换,是更强的 No-Go 信号;
若 Go,Step 5 之后切 WEPA/SLAPStack 复核(spec §1 第一阶段数据优先级)。
