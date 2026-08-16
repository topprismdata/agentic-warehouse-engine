# REVIEW v0.2 — 三轮自审(R01–R04 完成后)

**日期**: 2026-08-16 | **审阅对象**: commits 787df56..eb7d72d(R01–R04 全部成果)
**方法**: 按用户工作规则 —— 每次更新对完成结果自审 3 次,再决定下一步。本轮规则自此固化。

---

## 第一轮:事实核查(取证后确认,非记忆)

| # | 发现 | 证据 | 状态 |
|---|------|------|------|
| F1 | **全知槽位**: 所有 expert 在全部 14 天订单上槽位,又在同一批订单上评估 | R02–R04 协议代码: `assign_*(... order_lines ...)` 全量输入,`total_route_cost(order_lines ...)` 同一全量 | 违反 spec §4.3/§16.1 replay 纪律 → R05 时间切分修复 |
| F2 | **B3 容量违约**: 14 处位置超载(max 4 vs cap 2),而 B4 被同一约束硬约束 | 取证: `violating_locations=14 max_load=4` | spec §10.4 硬约束须对全体 expert 一致 → B3 改为 split-not-overflow |
| F3 | **forecast_daily 时间戳错配**: `zip(order_lines, orders)` 位置配对,line 与 order 非一一对应 | 取证: 5/12 行 known_qty 错 | 改 order_id 映射;教训:**未被消费的代码也会腐蚀 canonical schema** |
| F4 | **R03 报告 λ"单调变差"声明为假**: λ=1.0(0.7401) < λ=0.5(0.9369) | r03_cpsat.md 实际数字 | 报告文本改为"非单调,λ>0 皆 timeout 未证明,仅 λ=0 OPT 可下结论" |
| F5 | **R01 报告与配置漂移**: 报告 50 SKU/12 位置,config 已改 120/60 | 文件对比 | 重跑 R01(标记 legacy 度量) |
| F6 | **R02–R04 的 validate gate 空转**: 校验的是空 world(slot_assignment=[]) | 代码检查: `validate_pipeline(world)` 时 world 来自 build_world,决策从未写入 | R05 把 assignments+plans 写入后再 validate |
| F7 | **cost_weights.yaml 装饰性**: R02–R04 直接用原始 route/flow,权重未接线 | 脚本代码 | 记录在案;接线和真实业务权重同属 v0.3 |

## 第二轮:架构推导(结论层)

| 原结论 | 判定 | R05 验证后 |
|--------|------|-----------|
| "B3=0.4527 最佳" | 撤回(沾 F1+F2) | **B3 诚实值 0.8442/0.9189** |
| "B4 需要 stop-count 项(v0.3 修复方向)" | **诊断错误** | 公平条件下 **B4(0.8089/0.9056)胜 B3** —— solver 胜过启发式的架构假设成立,无需改公式化 |
| "L0/L1 排序一致" | 仅在全知协议下成立 | 诚实协议下**仍一致**(B4<B3<B2<B1<B0) |

**核心教训**: R03 的负结果诊断把"对手违约"误判为"公式化缺陷"。排序结论必须先做约束公平性审计 —— 这正是 spec §14.2 三重验证存在的原因。

## 第三轮:方法论(过程层)

- M1 验证层有效,但只有**非空转**的 gate 才算验证(F6)
- M2 DecisionPlan 审计产物 R02–R04 缺失;R05 起每个 expert 必须产出(b4 补了 build_decision_plan)
- M3 世界生成器的两次翻车(均匀采样→无 ABC;5m 玩具仓→时间度量无区分度)教训:**先证明世界有结构,再相信实验结论**
- M4 三轮自审固化为本仓工作规则(见 README)

## R05 执行结果(本轮审阅的直接产出)

诚实协议(slot days 1–7 / replay days 8–14,全 expert 容量审计=0,非空 validate):

| Expert | L0 norm | L1 norm |
|--------|---------|---------|
| B1 Static ABC(锚) | 1.0000 | 1.0000 |
| B2 COI | 0.9707 | 0.9852 |
| B3 Affinity | 0.8442 | 0.9189 |
| **B4 CP-SAT(λ=0)** | **0.8089** | **0.9056** |
| B0 Random(5 seeds) | 1.6686 | 1.2893 |

Gates 全 PASS;B3 三数演进:0.4527(违约+全知)→ 0.7136(容量修正,仍全知)→ 0.8442(诚实)。

## 下一步(三轮后决定)

1. **#12 Execution Gateway stub** —— DecisionPlan 现已真实产出,gateway 有东西可校验;补完 spec 附录 C 闭环
2. 之后:#5/#6 真实数据(Instacart basket 重估 affinity;Favorita 需求接 B4)
3. v0.3:cost weights 接线 + Multi-seed world(≥5 世界取均值,单世界结论不稳)
