# SPEC UPDATE v1.2 — Research Update(强制,取代 v1.1 研究边界)

**日期**: 2026-08-16 | **来源**: `FMCG_..._v1.2_Research_Update.docx`
**效力层级**: 本文件 > SPEC_UPDATE_v1.1 > v1.0 PDF。冲突处以本文件为准。

> **强制指令(v1.2 §11 原文)**:当前不要实现"大而全"的 Agentic Warehouse
> Decision Engine,也不要先开发多 Agent/MCP/Digital Twin。首先围绕 **DWERP**
> 建立 Dynamic Slotting OR Expert Benchmark,验证 **Expert Diversity、
> Myopic vs Dynamic Oracle 差异、Switch-cost Sensitivity**。只有这三个假设
> 成立后,才进入 Rule/XGBoost/MLP/LLM Selector 开发。

---

## 1. 研究问题升级(冻结)

**名称**: Dynamic Warehouse Expert Routing Problem(DWERP);
学术名 Sequential Warehouse OR Expert Selection Problem with Reconfiguration Costs。

**定义**: 时间 t=1..T,状态 S_t(需求/预测/库存/库位/affinity/资源/约束),
Expert Library E={E1..EK},每个 Expert 是**完整仓储决策 policy**。

π(S_t, E_{t-1}) → E_t → A_t → S_{t+1} = f(S_t, A_t, D_{t+1})

**目标(长期累计)**:
min Σ_t [ C_pick,t + λr·C_replenish,t + λm·C_move,t + λc·C_congestion,t + **λs·C_switch,t** ]

C_switch(策略切换的重配置/扰动成本)是 v1.2 新增分量;T2 专门扫它。

**Novelty 约束(§1,硬性)**: 不得声称首次做 warehouse algorithm selection /
learning-based dynamic slotting / LLM+slotting+simulation。贡献四要素:
dynamic algorithm selection × stateful reconfiguration × physical switching
cost × non-stationary FMCG demand。

## 2. Oracle 对照体系(冻结)

| 角色 | 定义 | 用途 |
|------|------|------|
| Myopic Oracle | 每期事后选当期成本最低 Expert | 传统 instance-wise 上界 |
| Dynamic Oracle | 全 horizon 最优 Expert trajectory | 检验 sequential 价值 |
| Fixed-Best | 全程固定整体最优 Expert | 最重要非智能基线 |
| Learned Selector | Rule / XGB / MLP / LLM / LLM+feedback | Step 7 才开发 |

**T1 判据**: Dynamic ≈ Myopic → sequential 无价值(No-Go);Dynamic 显著
优于 Myopic(过度重配置被避免)→ DWERP 成立。

## 3. Go/No-Go:三道前置实验(取代 v1.1 单道)

| # | 测试 | Go 条件 | No-Go 含义 |
|---|------|---------|-----------|
| T0 | Expert Diversity | 无单一 Expert 统治绝大多数期次 | Selector 研究价值不足 |
| T1 | Myopic vs Dynamic Oracle | Dynamic 总成本显著低于 Myopic | Sequential 价值弱 |
| T2 | Switch-cost Sensitivity | λm/λs 变化使最优 trajectory 合理变化 | 模型未捕捉执行经济性 |

## 4. Expert Library v3.1(policy 化,冻结名单)

Expert = policy:输入 (state, **current layout**) → 输出 (new layout, moves,
成本分解, feasibility, state-impact 预期)。

| ID | v3.1 Expert | 行为 | 本仓实现 |
|----|------------|------|---------|
| E1 | Static ABC | 稳定布局、低搬库(全历史频率 → 慢变) | ✅ policy 化 |
| E2 | COI | 空间×周转平衡 | ✅ policy 化 |
| E3 | Affinity | 共拣关系优先(recency-weighted) | ✅ policy 化 |
| E4 | Forecast | 未来 velocity(促销等已知事件) | ✅ policy 化 |
| E5 | Robust | 不确定性稳健(spread 罚) | ✅ policy 化 |
| E6 | **DDSR-like** | 已知未来订单 + 机会式 reposition(payback 阈值) | 🆕 本轮实现 |
| E7 | **Joint Optimizer** | 联合 pick+relocation(move 罚 CP-SAT;replenish 分量后续) | ✅ 由 v1.1 e7 升级 |

**移出名单**: v1.1 E6(Forecast+Affinity CP-SAT)→ 代码保留为 Joint 内核组件,
不再作为独立 Expert 参赛(诚实理由:与 E7 目标重叠,v3.1 名单以文档为准)。

## 5. Demand Regime = 连续时间序列(重造)

- Regime 不再是独立样本标签;时间轴分 **phase**,每 phase 有起止,可产生状态转移压力。
- Promotion 必须 **ramp-up / peak / decay** 三相位(非阶跃常数)。
- 默认序列(28 天 / 8 期):stable×4 → promo-ramp×2 → promo-peak×4 → promo-decay×2
  → stable×3 → velocity-reversal(渐变)×6 → affinity-shift×4 → move-cost-shock×3。
- 每个 DayParams: promo_mult / velocity_mix / affinity_remap / move_cost_scale /
  forecast_noise / regime_label。

## 6. 指标体系(v1.2 §8)

传统成本分解保留;新增序列指标:
- **Dynamic Regret** = Cost(policy) − Cost(dynamic oracle)
- **Over-Reslotting**:myopic 导致的无效/反复搬库量
- **Policy Stability**:trajectory 稳定性(切换次数、每次 layout 变化幅度)
- **State Impact**:动作对下一期库存/布局/补货/拥堵的影响
- 执行可靠性:Constraint Violation = 0、Service Level

## 7. 开发顺序(冻结,v1.2 §9)

Step 1 Simulator → Step 2 7 Expert Policies → Step 3 Regime Sequences →
Step 4 Myopic Oracle → Step 5 Dynamic Oracle → Step 6 Switch-cost Sensitivity →
Step 7 Selector Benchmark(Rule/XGB/MLP/LLM/LLM+feedback)

本仓映射:Step 1 = SimPy 内核 + 🆕 SequentialBenchmark;Step 2 = policies.py;
Step 3 = regime_sequence.py;Step 4/5/6 = R10(T0)/R11(T1)/R12(T2)。

## 8. v1.1 资产处置表

| 资产 | 处置 |
|------|------|
| canonical schema / validate(非空事实表) / 容量审计 | 保留 |
| SimPy replay(L1) | 保留为 Step 1 单期评估内核 |
| E1–E5 求解内核 | 保留,policy 化包装 |
| v1.1 e6(FcAff CP-SAT) | 移出 v3.1 名单,留作 Joint 内核 |
| v1.1 e7(rolling-lite) | 升级为 E7 Joint(policy 化) |
| R05 honest 纪律(时间切分/审计/非空 validate) | 保留,适用于每个 period |
| R06 Execution Gateway | 保留,挂起(Step 7+) |
| R09(v1.1 单道 Go/No-Go) | **终止**:regime 生成器按 §5 重造;其修复的 4 个实现 bug 全部继承 |
| Instacart adapter / R07/R08 | 保留为 Track B 补充验证(WEPA/SLAPStack 仍为 phase-1 主数据,待 T 关通过后接) |

## 9. 本轮范围声明(T0)

- 成本口径: C_pick(L0 route)+ λm·C_move;**λs=0**(C_switch 在 T2 启用);
  C_replenish/C_congestion 分量随 Joint 完整化(声明,不隐藏)。
- T0 的 per-period 比较在 myopic 路径的 layout_{t-1} 上评估(即 myopic 决策本身);
  trajectory 级严格 counterfactual 留给 T1 的 beam-search rollout。
- Myopic Oracle 标签与 per-period cost matrix 本轮即产出,直接作为 T1 输入。
