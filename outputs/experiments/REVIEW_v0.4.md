# REVIEW v0.4 — 三轮自审(R07 Instacart 真实 basket 完成后)

**日期**: 2026-08-16 | **审阅对象**: #5 Instacart 接入 + R07 真实数据重排名
**规则**: 每次更新对完成结果自审 3 次,再决定下一步。

---

## 第一轮:事实核查(取证确认)

| # | 发现 | 证据 | 处置 |
|---|------|------|------|
| H1 | user 切分无泄漏:top-N SKU 选择仅用 train 侧 | adapter L89-90: freq 来自 op_train | ✓ 通过 |
| H2 | r07 死代码 `for s in sku_master: pass` 残留 | grep 命中 | 已清 |
| H3 | 原始数据不入 git | .gitignore data/raw/ | ✓ 通过 |
| H4 | **B2 的 volume 是合成 uniform**(Instacart 无体积数据),COI 真实表现含此伪影 | sku_master 构造 | 报告已声明:B2 真实数据结论不可引用 |
| H5 | **空 world 通过 validate**(F6 空转的变体):9 表齐全但全空 = vacuous PASS | 取证:empty world is_clean=True | **validate 增强**:orders/order_lines/sku_master/locations/slot_assignment 非空强制;forecast/inventory 允许空(Track B 不适用);回归测试:空 world 现在被拒,R07 world 仍过 |
| H6 | R07 代码数据工程占 ~80%,OR 只重放 | 行数统计 | 记录(见第三轮) |

## 第二轮:架构推导 —— 合成世界的三重误导被真实数据纠正

| 量 | 合成世界(R05) | 真实 Instacart(R07) | 教训 |
|----|---------------|---------------------|------|
| basket 浓度 | 0.70(人为设定) | **0.2302(实测)** | 合成参数夸大 3 倍 |
| B3 affinity 优势 | 0.8442(−16%) | **0.9803(−2%)** | 信号弱 3 倍,优势几乎消失 |
| B2 COI 方向 | 0.9707(优于 B1) | **1.0588/1.1818(劣于 B1)** | 正负号翻转(部分是 H4 伪影) |
| **B4 CP-SAT** | 0.8089/0.9056 | **0.9115/0.7736** | **唯一在两个世界都稳定获胜者**;L1 优势反而扩大 |

核心结论:
- **B4 > B3 > B1 排序经受住真实数据检验**(L0/L1 一致),solver-胜-启发式的架构假设不再是合成世界的产品
- **任何合成结论必须带真实数据对照运行** —— 本次对照推翻了"B3 是强基线"的印象
- B4 L1(0.7736)< L0(0.9115)的解释:quantity=1 → stop 主导(均 3.25 行/单),freq-dist 指派省的是每停 travel —— 已写入报告,不是异常

## 第三轮:方法论

- **lineage 语义落地**:observed 内容 + synthetic 时间 = DERIVED(adapter docstring 声明),spec §4.1 semi-synthetic 纪律的实际演练
- **R07 的价值密度来自对照,不是绝对数**:Track B(真实 basket + 合成几何)的结论作用域已显式声明(报告 Honest notes)
- 数据工程占 80% 的工作量印证 spec 路线:canonical schema + lineage 先行,OR 组件是薄层
- validate 的"可空表白名单"设计:事实表不可空、上下文表可空 —— 空转防护与 Track 灵活性兼得

## R07 最终数字(3000 users / top-120 SKU / 60 合成位,容量审计全 0)

| Expert | L0 (held-out) | L1 (held-out) |
|--------|--------------|---------------|
| B1 StaticABC(锚) | 1.0000 | 1.0000 |
| B2 COI(含 H4 伪影,不引用) | 1.0588 | 1.1818 |
| B3 Affinity | 0.9803 | 0.9251 |
| **B4 CP-SAT(λ=0)** | **0.9115** | **0.7736** |
| B0 Random(5 seeds) | 1.1886 | 1.5951 |

Gates 全 PASS;validate 非空强化版通过。

## 下一步(三轮后决定)

1. **#6 真实几何接入(SLAPStack/WEPA 或 Footwear Picking 2025)** —— 消除 Track B 的合成几何,让 B4 的 L1 优势在真实 layout 上复核;Favorita(#5 另一半)接 forecast → B4 从"历史 freq"升级到"forecast 驱动"(spec §2.5 第五代)
2. 多世界(multi-seed users)方差报告 —— 单次 split 的结论需 ≥5 采样确认(B4 优势 0.91/0.77 是否稳定)
3. cost weights 接线 + action schema 统一(v0.4 已记)

优先级:**先 2 后 1** —— 便宜(纯计算,无新数据)且决定结论可信度;#6 需要新数据源调研。
