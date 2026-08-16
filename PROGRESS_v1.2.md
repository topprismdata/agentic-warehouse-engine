# Agentic Warehouse Engine — 进展与下一步计划

**日期**: 2026-08-16 | **项目**: `~/projects/agentic-warehouse-engine/`
**性质**: 阶段性总结文档(供审阅/交接;数字以 `outputs/experiments/` 各报告为准)
**当前权威规范**: `SPEC_UPDATE_v1.2.md` > `SPEC_UPDATE_v1.1.md` > v1.0 PDF

---

## 1. 项目定位(经三次演进)

| 阶段 | 研究问题 | 状态 |
|------|---------|------|
| v1.0 | Agentic Warehouse Decision Engine(大而全产品架构) | 作为资料库保留 |
| v1.1 | 单期:state → 选哪个 Slotting Expert | **被 v1.2 取代**(novelty audit 判定贡献不足) |
| **v1.2(当前)** | **DWERP**:序列决策 π(S_t, E_{t-1}) → E_t → A_t → S_{t+1},带物理重配置成本 λm·C_move 与策略切换成本 λs·C_switch,长期累计成本最小化 | 进行中 |

论文贡献四要素(红线):dynamic algorithm selection × stateful warehouse
reconfiguration × physical switching cost × non-stationary FMCG demand。
LLM 已降级为 selector family 候选之一(Step 7),不是论文主角。

## 2. Go/No-Go 三道关卡(v1.2 §5)与当前状态

| 关卡 | 问题 | 判据(预声明) | 状态 |
|------|------|--------------|------|
| **T0 Expert Diversity** | 最优 Expert 是否随状态切换? | 无单一 Expert ≥80% 统治 + ≥3 distinct winners | ✅ **GO**(R10:E7 占 52%,6 个 distinct winner,切换与相位对齐) |
| **T1a Existence** | myopic 被 dynamic 严格支配的序列存在? | constructive evidence | ✅ **YES**(seed 17:sac 80 → regret 2116,TrapScore 26.3) |
| **T1b Prevalence** | trap 在多少条件下出现? | 分布形态(非均值 gate) | ✅ 完成(R12,12 seeds:保险型重尾;结构 9/12,material 1/12;divergence 集中在转变前夜) |
| **T2 Sensitivity** | λm 如何调制规划价值? | 三张曲线 + 机制 | ✅ 完成(R13:左端低+中段峰(λm=10)+右端 plateau;高成本区"只搬最关键的") |
| **T1.5 move vs switch** | C_move/C_switch 分别贡献? | 三条件分别跑 | ⬜ 未做(只跑了 move-only;REVIEW_v1.3 U 项记录) |

## 3. 已交付资产(12 commits,39 个 Python 模块,~6000 行)

### 3.1 世界与数据层
- **canonical schema(9 表)+ 反泄漏字段**(known_at_time / lineage / constraint_version / model_version)+ 非空事实表强制校验
- 合成世界:真实 DC 几何(120m 深)、Zipf 频率、basket 结构
- **Instacart 接入**(CC0,340 万订单):user 级切分防身份泄漏;top-120 SKU
- **regime_sequence.py**:28 天连续相位序列(promo ramp/peak/decay、渐变 reversal、affinity 重映射、move-cost/噪声窗口)

### 3.2 OR Expert Library v3.1(policy 化)
E1 StaticABC / E2 COI / E3 Affinity(recency 加权)/ E4 Forecast(促销已知事件)/ E5 Robust(spread 罚)/ **E6 DDSR-lite**(机会式 payback 门控重定位)/ **E7 Joint**(CP-SAT move 罚)。全部容量审计合规(ceil(n/L) 硬约束)。

### 3.3 评估与验证层
- **L0 route cost**(订单级 greedy TSP)+ **L1 SimPy replay**(flow time)
- **sequential.py**:滚动 benchmark + myopic 标签 + **beam-search dynamic oracle**(myopic trajectory 保底注入 → beam ≤ myopic 严格成立,报告 gap 为保守下界)
- Execution Gateway stub(8/8 路由/拒绝测试,§15.4 审计行)
- **确定性 CP-SAT**(单 worker + deterministic time)—— 消除 beam replay 不一致

### 3.4 实验记录(R01–R11 + 5 份三轮自审)
关键数字演变(全部NormalizedCost vs 当期锚,诚实协议:时间/user 切分 + 容量审计):

| 实验 | 结论 |
|------|------|
| R05(诚实评估) | B4 CP-SAT 0.8089 > B3 0.8442(撤回 R02–R04 的全知+违约排名) |
| R07/R08(Instacart) | B4 真实数据稳定获胜(0.9252±0.018);B3≈B1 无显著差异;真实浓度 0.23 vs 合成假设 0.70 |
| R10(T0) | **GO**:promo→E3/E4 家族,stable→E1,mc_shock→E7 |
| R11(T1) | seed 17:dynamic 故意在 affinity_shift 期选当期差 1.6% 的 E1,换得 mc_shock 期 5 moves(vs myopic 55)→ 全局省 5.34%;但 5 seeds 中仅 1 个达 2% |

## 4. 已固化的方法学发现(论文素材)

1. **世界必须有结构**(Zipf+basket),否则基线无区分度 —— 均匀采样曾被 gate 抓获
2. **排序结论前必须做约束公平性审计**(B3 曾靠容量违约"获胜")
3. **合成参数系统性扭曲排名**(浓度 0.70 vs 实测 0.23;B2 符号翻转)
4. **recency 加权历史已含促销信号** → forecast 类 expert 的价值在 move/风险意识,不在信息优势(W1)
5. **"knowing when not to move" 是最清晰的切换信号**(mc_shock 全由 E7 获胜)
6. **T1 的核心机制已观测到**:myopic 的失败模式 = 不为未来重配置成本做预期;dynamic 通过当期小牺牲换后期低成本(seed 17 为标准案例)
7. 单期协议(信息+求解最强)与序列协议(move-aware joint 最强)的**分水岭** —— 这正是 v1.2 novelty 的实证支撑

## 5. 三轮自审已抓出的重大缺陷(工程信用记录)

| Review | 缺陷 | 影响 |
|--------|------|------|
| v0.2 F1/F2 | 全知槽位评估;B3 容量违约 14 处 | R02–R04 排名全部撤回重做 |
| v0.4 H5 | 空表 world 通过 validate | 事实表非空强制 |
| v1.2-T0 W2 | move_cost_scale 未接线 | mc_shock 相位结果全部重跑 |
| v1.2-T1 | CP-SAT 非确定性导致 beam replay 不一致 | 全部求解器改 deterministic 模式 |

## 6. 下一步计划(优先级序)

### 6.1 立即:T1 BORDERLINE 的裁决(本周)
R11 的 5-seeds 结果落在预声明的 BORDERLINE 带(1/5 达 2%)。裁决路径:
1. **诊断 seed 间异质性**:gap 与"affinity_shift→mc_shock 相邻 + myopic 在前期的布局失误"强相关吗?量化"陷阱窗口"出现频率
2. **加 seeds 至 10–15**(每 seed ~90s,可行):报告 gap 分布而非单值
3. **判据重审(如需)**:若 gap 呈重尾分布(少数大、多数零),则正确指标是"期望 regret + 出现频率",不是"全 seeds ≥2%"—— 任何判据修改须预声明并写明理由
4. **产出**:T1 终审报告(GO / NO-GO / 修正判据下的裁决),三道关结果写回 SPEC

### 6.2 T2 Switch-cost Sensitivity
- 扫 λm ∈ {0.5×, 1×, 20×} × λs ∈ {0, 1×}:观察最优 trajectory 的 moves/switches 单调性
- Go 条件:move 成本上升 → 最优路径 move 数下降且专家组合变化合理
- 依赖:T1 的 beam machinery 直接复用(λs 已是参数)

### 6.3 三关通过后(按 v1.2 §12)
1. **WEPA/SLAPStack 接入**(phase-1 主数据):连续 regime perturbation 落到真实几何
2. **Selector Benchmark(Step 7)**:Rule / XGBoost / MLP / LLM zero/few-shot / LLM+Solver-Feedback,指标 = OracleGap + Dynamic Regret
3. 指标补全:Over-Reslotting / Policy Stability 已在 R11 报告;State Impact 随 E7 replenish 分量完整化

### 6.4 积压技术债(非阻塞,记录在案)
- cost_weights.yaml 接线(λ 权重目前硬编码于各实验脚本)
- action schema 统一(附录 C 契约 vs DecisionPlan.actions 双格式)
- Instacart adapter 每 seed 全量重解析(~10s,可缓存)
- R09(v1.1)遗留报告归档标注 "superseded by v1.2"

## 7. 风险与边界(诚实声明)

- **平台仍是合成**(几何真实、需求构造);T1 的 5.34% 单例是构造性 regime 下的证据,WEPA 复核前不外推到真实仓
- **成本口径**:C_pick + λm·C_move;λr·C_replenish / λc·C_congestion 未入目标(声明,不隐藏)
- beam oracle 是**近似**,报告 gap 为保守下界;null 结果是 beam-limited 而非严格否定
- λs(C_switch)T1 中为 0,T2 才启用 —— 若 switch 成本主导,T1 gap 可能被低估

## 8. 文件索引

```
SPEC_UPDATE_v1.2.md            # 当前权威研究规范
README.md                      # 项目概览 + 工作规则(三轮自审)
world_state/                   # schema, validate, sampler, regimes, adapters
features/                      # affinity (recency), forecast (heterogeneous σ)
or_experts/                    # policies.py (v3.1) + E1–E7 内核
simulation/                    # sequential.py (benchmark + beam), replay.py (L1)
execution/gateway.py           # Execution Gateway stub
scripts/run_r{01..11}_*.py     # 逐实验入口(5 阶段 pipeline 风格)
outputs/experiments/           # R01–R11 报告 + REVIEW_v0.2..v1.2-T0
```
