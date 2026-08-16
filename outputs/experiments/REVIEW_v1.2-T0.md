# REVIEW v1.2-T0 — 三轮自审(SPEC v1.2 落地 + R10 T0 完成后)

**日期**: 2026-08-16 | **审阅对象**: v1.2 增量更新落地 + R10(T0 Expert Diversity)
**规则**: 每次更新对完成结果自审 3 次,再决定下一步。

---

## 第零轮:v1.2 文档精读裁决(先于代码)

6 个实质变化全部固化进 `SPEC_UPDATE_v1.2.md`;**R09(v1.1 单道 Go/No-Go)终止**,
其修复的 4 个实现 bug(E1 round-robin 错位 / promo 流-forecast 物理不一致 /
E6·E7 归一漂移 / forecast zip bug)全部继承。v1.1 e6(FcAff)移出 v3.1 名单。

## 第一轮:事实核查(取证)

| # | 发现 | 证据 | 处置 |
|---|------|------|------|
| W1 | promo_peak winner 是 E3 而非 E4(smoke 与 full 不同) | margin 取证:E3=5429 vs E7=5466 vs E1=5497(<1.3%) | **不是 bug,是结构结论**:recency-weighted 历史已含 promo 信号,E4 的 informed forecast 信息集与之重叠;E4 全量重排反付 move 罚。E4/E5 的真实价值在"move/不确定性意识",不在信息优势 —— 记入 findings,进论文叙事 |
| W2 | **move_cost_scale 未接线**:mc_shock(×20)相位的 move 罚没有放大,E1 以 108 moves 险胜 E7 | moves 取证:mc_shock 下 E1=108 vs E7=72 | **已修**:`mc_unit *= dp.move_cost_scale`;修复后 mc_shock 全 seed 由 E7 获胜(物理一致:"knowing when not to move" 是最清晰切换信号) |
| W3 | E6_DDSR 从未获胜且 moves 最多(170) | r10 报告 | 简化版局限(无 retrieval 融合、swap-only、无未来订单窗口),记 finding,不掩盖;v3.1 名单保留(它的对手集会随 T1/T2 变化) |
| W4 | E1 每期 100+ moves,"稳定布局"偏好未体现 | W2 取证 | **结构澄清而非缺陷**:E1 的慢变来自信息集(全历史),promo 之后历史分布漂移使重排合理;真正"低搬库"的表述者是 E7(move 罚内置)。v3.1 表格的"行为偏好"描述与实现的对齐依赖此解释,已写入报告 |
| W5 | validate 非 vacuous 通过;容量违规全 0 | r10 报告 | ✓ |

## 第二轮:架构推导

- **T0 GO 成立**:E7 统治 67% 但未达 80%;promo_ramp/peak → E3/E4/E5 家族,
  stable → E1,mc_shock → E7;切换与相位对齐、可解释。
- **序列协议 vs 单期协议的分水岭已经显形**:单期世界(R05/R08)里 B4/E4 类
  "信息+求解"最强;序列世界(move cost + 状态依赖)里 **move-aware joint(E7)
  才是王者,E1 在稳态回归**。这恰是 v1.2 novelty audit 预言的
  "selection × reconfiguration × switching cost" 价值来源。
- W2 说明 T0 是 T1/T2 的必要前置:连 move-cost 机制都没接线时跑 T2 会得出
  荒谬结论。gate 顺序被验证有效。

## 第三轮:方法论

- **阈值主观性声明**:v1.2 只说"绝大多数",本实现量化为 <80% Go / ≥95% No-Go
  / 之间 BORDERLINE(先跑 T1 再定)。已写入脚本与报告。
- warm-up 泄漏(phase 0 只作历史、不参与评估)在实现时即时抓住 —— 序列协议
  的 R05 纪律等价物。
- **数据工程占比继续上升**(regime sequence / policy 接口 / sequential core),
  再证 spec "schema/环境先行,OR 是薄层" 的路线正确。

## R10 最终数字(3 seeds × 7 期,120 SKU / 60 loc,λs=0)

| 相位 | modal winner |
|------|--------------|
| promo_ramp | E1_StaticABC(ramp 收益 < 重排罚) |
| promo_peak | E3_Affinity(margin<1.3%,E3/E7/E1 接近) |
| promo_decay / stable2 / reversal / affinity_shift / mc_shock | E7_Joint |

share = E7 67%(<80)· distinct = 4 · 违规 = 0 · **T0 VERDICT: GO**

## 下一步(三轮后决定)

1. **R11 = T1 Myopic vs Dynamic Oracle**:beam search trajectory rollout
   (T0 已产出 per-period cost matrix + myopic 标签,直接复用);判据 =
   Dynamic 总成本显著低于 Myopic(建议 ≥2% 且 3 seeds 一致才 Go)
2. **R12 = T2 Switch-cost Sensitivity**:扫 λm(0.5×/1×/20×)与 λs(0/正),
   观察最优 trajectory 的 moves/switches 单调变化
3. T1/T2 通过后:WEPA/SLAPStack 接入(v1.2 §12),再 Selector(Step 7)
