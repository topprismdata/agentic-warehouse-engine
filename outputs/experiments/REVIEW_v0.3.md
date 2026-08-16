# REVIEW v0.3 — 三轮自审(R06 Execution Gateway 完成后)

**日期**: 2026-08-16 | **审阅对象**: Execution Gateway stub(#12)+ R06 测试矩阵
**规则**: 每次更新对完成结果自审 3 次,再决定下一步。

---

## 第一轮:事实核查(取证确认)

| # | 发现 | 证据 | 处置 |
|---|------|------|------|
| G1 | **死代码**: `R_RISK_HIGH_NO_APPROVAL` 定义后从未触发 —— high risk 的正确行为是 `approve_required`(接受待批),不是 reject,该 code 语义混乱 | grep: 仅定义处 1 次出现 | 已删除 |
| G2 | **medium 档零测试覆盖**: spec §15.2 四档风险路由,测试矩阵只盖了 low/high/safety 三档 | grep MEDIUM: 0 hit | 补 T8(现 8/8 PASS) |
| G3 | audit row 完整性 | 报告 sample 含 §15.4 全部六要素 | ✓ 通过 |
| G4 | **两套 action 格式并存**: b1–b4 的 `DecisionPlan.actions = {action, reason, ...}` vs gateway 契约 `{sku_id, to_location, expected_saving, ...}`,靠 R06 的 adapter 桥接 | grep 两种格式 | 记 finding:v0.4 统一到 gateway 契约(附录 C 语义) |

## 第二轮:架构推导

- **检查链顺序耦合**: T6 smoke 失败暴露 capacity 检查先于 payback —— 动作子集若位置碰撞会在 payback 之前被拒,测试意图被吞。教训:**每个 gate 场景必须只触发目标检查**(测试隔离),构造数据时显式排除前置检查的干扰
- **容量是世界属性,不是 plan 属性**(T1 抓到的核心缺陷): `count_capacity_violations` 原从 plan 内 SKU 数反推 capacity,5 动作子集自推 cap=1 误判合法共存为违约。已改为 gateway 构造时显式传入 `ceil(n_sku_total/n_loc)`。这条原则等价于 spec §10.4:约束定义在世界,所有计划在同一约束集下受审
- **dry_run 不执行是特性**: stub 的职责是契约 + 拒绝码 + 审计行;执行管道(审批流转、WMS 适配)是 v0.4,不在此milestone 膨胀

## 第三轮:方法论

- 测试矩阵驱动有效:8 个场景中 T1(容量反推 bug)与 T6(检查顺序耦合)都是测试**自己**抓出来的真缺陷 —— 不是被实现顺便带出的
- 路由类组件的测试完备性判据:**枚举全部档位**(low/medium/high/safety),逐档验证,缺档即 gap —— 这次是 medium,靠"数档位"发现的
- R06 的 8/8 全 PASS 才 commit;此前 7 轮迭代中 2 次 FAIL 都是测试断言与 spec 语义打架,值得保留在 git log 里

## R06 最终结果

| 场景 | 结果 | 拒绝码 |
|------|------|--------|
| T1 合法小 plan(≤5 动作) | 5 accepted, auto, LOW | — |
| T2 verifier_status=timeout | 拒绝 | SOLVER_STATUS_NOT_FEASIBLE |
| T3 过期 constraint_version | 拒绝 | CONSTRAINT_VERSION_MISMATCH |
| T4 容量违约 | 拒绝 | CAPACITY_VIOLATION |
| T5 safety_critical | 拒绝 | SAFETY_CRITICAL_BLOCKED_FOR_LLM |
| T6 MOVE 不回本 | 拒绝×3 | NEGATIVE_PAYBACK |
| T7 120 动作大规模 | 120 accepted, HIGH, approve_required | — |
| T8 MEDIUM 显式标记 | 5 accepted, MEDIUM, approve_required | — |

**#12 完成。spec 附录 C 三方契约(Supervisor/Solver/Verification)中的执行边界已闭环。**

## 下一步(三轮后决定)

剩余 TODO:#5/#6 真实数据接入(Instacart basket → affinity 重估;Favorita 需求 → B4 forecast)、#8 真实任务时长标定 L1、F4/G4 action schema 统一(v0.4)、cost weights 接线。

优先级判断:**#5 Instacart 接入最优先** —— 当前所有结论建立在合成世界(Zipf+人为 basket 浓度 0.7)上,合成参数决定了 B3/B4 的相对优劣;真实 basket 分布是让排名可信的第一杠杆。且 Instacart 数据本地可下、无需 Kaggle 认证的部分先做。
