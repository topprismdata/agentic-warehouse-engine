# SPEC UPDATE v1.4 — 信息边界与过渡成本(强制,导师 2026-08-16 晚反馈)

**效力**: > v1.3 > v1.2 > v1.1 > v1.0。冲突处以本文件为准。

---

## 1. 信息边界(最高优先级,新实验 T3)

**问题**:seed 17 的机制(dynamic 在 affinity_shift 忍住)依赖对未来 mc_shock 的
预知 —— beam 看到完整未来轨迹 = clairvoyance。已证明 Intertemporal Opportunity
Exists,**未证明 Deployable Policy Can Exploit It**。

**信息体制拆分(冻结)**:

| 体制 | 可见信息 | 角色 |
|------|---------|------|
| Ex-post Dynamic Oracle | S_{t:T}(完整未来) | 理论上界 |
| **Anticipatory Policy** | Information_t(当前状态/已知促销/已确认订单/需求趋势/forecast/已排期 labor·tariff/未知 shock 的概率) | **可部署算法** |
| Myopic(两种) | 逐期 realized(事后贪心 oracle)或 逐期 forecast(可部署贪心) | 基线 |

**新指标**: CaptureRate = (C_Myopic − C_Deployable)/(C_Myopic − C_Oracle)。
危险情形 = trap 存在但只有 clairvoyant 能避开 → DWERP 仍有理论意义但
Agent 价值弱;此情形必须如实报告。

**Anticipatory 实现口径**: receding-horizon —— 每期用 **forecast 内部成本模型**
(Σ p50×dist 线性代理,非 realized route)在 H 步前瞻上 beam,取首动作,
滚动;每步重预测(per-period forecast 视图,忠实于滚动重预测语义)。
**Shock 知情性两档**: schedule-aware( tariff/labor 已排期,合法预知)vs
schedule-blind(假设当前 move cost 持续,surprise shock)。

## 2. DWERP 公式化简化(冻结)

正文定义改为 **π(S_t) → E_t → A_t,S_{t+1} = f(S_t, A_t, ξ_{t+1})**(S_t 已含
layout/inventory/resources;E_{t-1} 仅当策略切换本身有成本时入状态)。
**C_transition = d(L_t, L_{t+1})**(物理布局距离),非 1[E_t≠E_{t-1}]。
长期形式(论文):C_transition = α·N_moves + β·D_move + γ·T_labor + δ·N_pickface。

## 3. T1.5 = Methodology Result(指标冻结)

- **False Switch Penalty**: E_t≠E_{t-1} 且 d(A_t,A_{t-1})≈0(换名不换仓,被罚 = false positive)
- **Hidden Physical Reconfiguration**: E_t=E_{t-1} 且 d(A_t,A_{t-1})≫0(同名大搬,漏罚 = false negative)
- 若两率显著 → 论文结论:**"algorithm-switch count is an inadequate surrogate
  for warehouse reconfiguration cost"**(d 代理 = n_moves,v1.4 声明)
- 三条件: move-only / switch-only(λm=0,λs>0)/ both

## 4. Trap 归一化与前置变量(冻结)

- **NormalizedTrapGain_t(H) = (C^M_{t:t+H} − C^D_{t:t+H}) / C^M_{t:t+H}**
- MaterialTrap_t = 1[NTG > τ],τ=1%(跨 seed/仓库可比,无规模依赖)
- 新变量 **LeadTimeToShock**(错误局部重配 → 后续高成本 regime 的间隔)
- 目标: P(Trap | LeadTime, ShockMagnitude, DemandShift, MoveCost)

## 5. Controlled Trap Phase Diagram(新实验 T4,论文最强图候选)

系统网格而非随机 seed 等稀有事件:
**Δt ∈ {0,1,2,4}(transition→shock 间隔)× M_s ∈ {2,5,10,20}(shock 倍数)**
× λm,序列 = warmup→transition(affinity remap)→gap(Δt)→mc-shock(M_s)→tail。
产出: NTG 热力图 + trap 区域边界 —— 回答"什么条件组合产生 inter-temporal trap"
这一科学问题。

## 6. R13 结果的规范表述(冻结)

禁止说"dynamic 高成本下搬得更多";正确表述:
> Although total reconfiguration declines with increasing move cost, the
> dynamic policy may execute more moves than myopic at the same cost level
> because it **selectively retains high-payback moves**.

**Not fewer moves. Better moves.** / When NOT to reconfigure ≠ never reconfigure
= **Only reconfigure when future value exceeds the option value of waiting**
(real options 味道,论文 Discussion 素材)。
新增指标: **VPM** = (FuturePickingSaving − MoveCost)/N_moves;
**Marginal Move Quality** = (Moves_D − Moves_M) 部分的净收益。

## 7. Selector 纪律(冻结,Step 7 前)

- **禁止把 phase 当 feature**(phase 可能是人赋的未来标签);Selector 输入只能
  是 online-observable 状态变量(MoveCost_t/DemandTrend_t/VelocityShift_t/
  AffinityDensity_t/ForecastUncertainty_t...)—— known_at_time 反泄漏原则的延续
- **不做纯分类**:预测 Ĉ(E_i|S_t) 取 argmin(cost-sensitive expert routing /
  learning-to-rank);评价 = DynamicRegret 而非 accuracy;trap 是 rare-but-costly
  → cost-sensitive 合理

## 8. WEPA 两层验证(冻结)

- **WEPA-Natural**:纯真实 order stream → external validity(自然数据有无
  diversity/natural trap)
- **WEPA-Stress**:真实几何/库存/订单组成 + 人为 promo·move-shock·reversal →
  mechanism validation。论文表述 = "natural validation + controlled
  counterfactual stress test",不混为一个结论

## 9. 论文题目(候选,冻结)

**When Not to Reconfigure: Sequential Expert Routing for Dynamic Warehouse
Slotting under Non-Stationary Demand**(with Physical Reconfiguration Costs
作副标)。中文:何时不应重配置:非平稳需求下考虑物理重配置成本的仓储动态专家路由。

## 10. 执行顺序(修订)

T1.5 → **信息边界实验(T3)** → **Controlled Trap Phase Diagram(T4)** →
多 seed 加固(cache 增量)→ WEPA Natural/Stress → Selector(最后)。

## 11. 三个必须保护的机制(项目核心资产)

1. 不同状态 → 不同 Expert 最优
2. 当前最优 → 不一定长期最优
3. **重配置成本越重要 → "是否行动"本身成为决策变量**(最值得挖)
