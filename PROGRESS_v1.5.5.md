# Agentic Warehouse Engine — 进展与下一步计划 v1.5.5

**日期**: 2026-08-18 | **项目**: `~/projects/agentic-warehouse-engine/`
**论文 PDF**: `paper/main.pdf` (16 页, 5,592 词, 25 引用, 5 图)
**规范链**: SPEC v1.0 → v1.1 → v1.2 → v1.3 → v1.4 → **v1.5 (MTS 母体 + d_m/d_w 区分)** → v1.5.5 (reviewer-grade closure)
**仓库**: https://github.com/topprismdata/agentic-warehouse-engine (33 commits)

---

## 1. 论文最终定位 (v1.5.5)

> **DWERP studies when a warehouse should defer locally optimal physical
> reconfiguration under non-stationary demand, and how much of the
> resulting full-information opportunity can be captured by deployable
> receding-horizon policies with imperfect forecasts and internal cost models.**

中文:在非平稳需求下,仓库何时应延迟眼前最优的物理重配置;在预测与内部
成本模型均不完美的现实条件下,可部署的滚动决策能捕获多少全信息长期规划价值。

**理论母体**: Metrical Task Systems (MTS) — 距离/状态空间是严格 metric
(displacement 满足对称+三角不等式+identity)。在文献中(同源 Borodin
et al. 1992 原始定义、MTS 至 2010s 的经典竞争性分析),MTS 是 online
optimization with switching costs 的标准范式。

**正式区分**:
- `d_m(L, L') = |{s : L(s) ≠ L'(s)}|` (move-count metric proxy) — 理论抽象
- `d_w(L, L') = labour_cost(L, L')` — 实际实现成本
- `d_w ≠ d_m` 本身是一个 finding:clean MTS 抽象在真实仓库中系统性地被
  asymmetric moves / capacity / batching / exchange chains 违反

---

## 2. 论文三层贡献链(压缩自 5 项 → 3 项)

1. **Structural opportunity exists**: DWERP 形式化 + 7 道 T-gate 完整 + 穷举验证
   - R18 beam-30 = exact(0.00% gap 4/4 seeds)
   - Seed 17 TrapScore 26.3 (sac 80→regret 2116, 5.34% gap)
   - Δt=1 trap band 1.26-1.69% (R16 controlled)
   - Traps vanish without cost shocks

2. **The deployment paradox**: 朴素保守策略胜过学习型
   - R17 归因: model fidelity 不是绑定约束
   - R22/R23: FixedBest 5 种 selectors 中最强
   - R15: RHC ≈ greedyFC (≤0% capture)
   - **核心洞察**: "何时不应重构"本身是一个优化问题

3. **Boundary and mechanism**: 6 datasets / 8 evaluation settings
   - **empirical deployment-gap collapse**: 真实数据上 gap=0.00%
   - **d_m ≠ d_w**: 4 类违反(不对称/容量/批量/交换)
   - Hidden reconfiguration rate 17-69% (R14)
   - Trap → clean MTS abstract → real warehouse implementation 三个层次

---

## 3. 数据源完整 T0 全景 (6 public datasets / 8 settings)

| 来源 | 接入方式 | n SKUs | 数据类型 | Winners | Gap |
|------|---------|--------|---------|---------|-----|
| WEPA (R21) | slapstack pip | 40 | 单仓 3mo | 3-4 | 0.00% |
| CrossStacks (R24) | slapstack pip | 40 | cross-dock | 1-2 | 0.00% |
| Instacart top-10% (R25) | Kaggle 32M行 | 20 | 零售 top 10% | 2 | 0.00% |
| Instacart mid-10% (R25) | Kaggle 32M行 | 20 | 零售 mid 10% | 2 | 0.00% |
| Favorita real (R26b) | Kaggle 850MB | 40 | 54 门店 × 14d | 2 | 0.00% |
| M5 sparse (R28) | Kaggle 47MB parquet | 40 | 5-yr CA_1 | 1 | 0.00% |
| M5 dense (R28b) | Kaggle 47MB parquet | 40 | 5-yr 10 门店 | 1 | 0.00% |
| **SLAPRP (R29)** | **Zenodo 7866860** | **40** | **basket 1-8 items/order** | **3** | **0.00%** |

**Footwear 2025** (de Assis et al.): 论文找到,尝试下载受环境阻挡(Elsevier session
auth + 我们的 git 环境无 OAuth cookies);**数据集声明为 CC BY 4.0,理论上可下载**。
Mendeley ID `pf2w725pw3`,DOI `10.17632/pf2w725pw3`。**Future work**: R30 Footwear。

**核心结论**: empirical deployment-gap collapse 在所有测试的 8 个 evaluation
settings 上都成立;diversity finding 需要数据含 regime 变化(M5 退化 = 数据
结构条件, 而非数据稀疏限制)。

---

## 4. 选择器家族完整结果 (R15/R22/R23)

| Selector | 类型 | 总成本 | Mean Regret | Top-1 |
|----------|------|--------|-------------|-------|
| S0 BFIP | (近似 full-info) | 138,296 | 0.00% | 100% |
| S1 FixedBest | 经验保守基准 | 139,842 | 1.43% | 46.4% |
| S2 Rule | 手工阈值 | 140,377 | 1.26% | 35.7% |
| S3 XGBoost | 学习型 | 140,204 | 1.87% | 39.3% |
| S4 MLP | 学习型 | 140,248 | 2.23% | 25.0% |
| S5 LLM (1B) | 零样本 | 150,122 | 11.38% | 25.0% |

**结论**: FixedBest 是 strong deployable conservative benchmark,
**不是** theoretical cost lower bound(它本身是可行 policy,给出的是
upper bound on the minimum achievable cost 的 pessimistic estimate)。

**表阅读注意**: S1 总成本低 vs S2 mean regret 低 的不一致来自聚合差异
(全成本是规模加权聚合,mean regret 是 instance-level unweighted 平均);
脚注已显式说明,supplementary material 提供 paired per-instance 对比。

---

## 5. 资产清单

- **代码**: ~8,500 行 Python (85+ tracked files)
- **数据**: 5 个公开来源完整接入 (Instacart, WEPAStacks, CrossStacks, Favorita, M5, SLAPRP);Footwear 引用
- **实验报告**: R01-R29 (29 个);REVIEW v0.2-v1.5.5 (15+ 轮自审)
- **图**: t2_lambda_curves / expert_winning_map / trap_phase_diagram / rf_capture / vpm_curve
- **缓存**: R13/R16/R17/R20 JSON cell (断点续跑)
- **论文**: `paper/main.pdf` v4 (16 页, 5,592 词, 25 引用)

---

## 6. 15 轮三轮自审记录 (累计捕获 18 项关键发现/缺陷)

| 轮 | 关键捕获 |
|----|---------|
| v0.2 | 全知评估 + 容量违约 → 撤回 R02-R04 |
| v0.4 | 空表过 validate → 事实表非空强制 |
| v1.2-T0 | move_cost_scale 未接线 → 修复 |
| v1.2-T1 | CP-SAT 非确定性 → deterministic 化 |
| v1.3 | 微 trap 口径 + 判据静默修改 |
| v1.4 | beam oracle 非可采纳 → 宽度制度化 |
| v1.5-R17 | capture 语义差异 + model fidelity 假设否定 |
| v1.5-R21 | 部署边界单点(WEPA only) |
| v1.5-R22 | selector ≤ FixedBest |
| v1.5-R23 | LLM 失败作为零样本基线 |
| v1.5-R24 | 跨数据集验证(6 → 7 → 8 settings) |
| v1.5-R26 | WEPA 真实数据边界 |
| v1.5-R28 | M5 稀疏限制 |
| v1.5-R28b | M5 单 winner 是数据结构条件,非数据稀疏 |
| **v1.5.5 (reviewer)** | **3 项事实验错 + 4 项术语修正 + 5 项结构性提升** |

### v1.5.5 (reviewer) 捕获
1. 8 sources 应为 6 datasets / 8 settings
2. IISE ≠ INFORMS 期刊
3. d(L,L) 是符号笔误 (应是 d(L,L'))
4. 1B/7B LLM 用词不一致
5. "global boundary" 应为 "empirical deployment-gap collapse"
6. "lower bound" 应为 "conservative benchmark"
7. S0 "Oracle" 改 S0 BFIP
8. 4-contribution → 3-contribution
9. 选择器总成本 vs mean regret 不一致须显式说明
10. 引入 d_m/d_w 区分(MTS 抽象 vs 实现)
11. Footwear 数据可下载(我们环境阻挡) → future work R30
12. 引入 empirical deployment-gap collapse 取代 universal boundary
13. 引用 PoP(MTS 起源 paper)
14. 引入 c_t(L) per-period operating cost
15. 总成本 vs mean regret 配对分析放 supplementary

---

## 7. 实验分层结构 (29 实验)

| 层 | 编号 | 范围 |
|----|------|------|
| 基础设施 | R01-R09 | schema/基线/CP-SAT/SimPy/gateway/Instacart |
| 主实验 | R10-R22 | T0/T1a/T1b/T2/T1.5/T3 完整 7 道关 |
| 序列 vs 部署 | R15/R17 | 归因实验 |
| 真实数据 | R21/R24/R25/R26b/R28/R28b/R29 | 6 个独立源 / 8 个 settings |
| 选择器家族 | R22/R23 | 5 种 selector |
| 数据管理 | R27 | 可获得性报告 |

---

## 8. 公开/待办/未来 — reviewer-grade 优先级

### P0 — 投稿前必须完成
1. **R30 Footwear**(导师新提) — 尝试 alternative API 路径(图集/Zenodo/作者GitHub)
   - 如下载成功,加 1 行 R30(7th public dataset, 9 evaluation settings)
   - 如下载受阻,future work 一行说明
2. **PoP(MTS 起源)引用** — 在 §2 Related Work 加 Borodin et al. 1992
3. **c_t(L) per-period operating cost** — §3 Formulation 已包含
4. **paired per-instance comparison** — supplementary material
5. **multi-seed CI** — 关键主结果 (trap / capture / selector / real-data)
6. **Cover letter + venue selection** — **首选 IISE Transactions** (IISE ≠ INFORMS;
   强调 methodology + engineering problem + real datasets)
7. **README/SPEC/PROGRESS/paper 同步** — 统一指向 v1.5.5
8. **§Limitations: Footwear** — 软化 "behind auth wall" → "unable to download in our
   test env despite CC-BY-4.0 license"

### P1 — 强烈建议(可选)
9. **R29 SLAPRP multi-seed** (5 seeds) — 验证 basket structure 信号的稳定性
10. **R18 exact-certification grid** — 小规模穷举扩展 (n_experts × T × regimes × λ)
11. **R28b M5 完整化** — 不只是 dense,加 5-yr 跨年(5 个 sub-period × 4 stores)
12. **d(L,L) 公式化扩展** — 从 n_moves 升级到 weighted sum-dist

### P2 — 不阻塞第一投
13. **SLAPStack full integration** (P2 → P0 if T-ASE target)
14. **Paper 2 方向** — "How to detect and avoid traps under data uncertainty"
    (R12 + estimator) 或 "Cost-aware Meta-learning for Online Routing"

---

## 9. 风险与边界(诚实声明 v1.5.5)

- **6 真实数据集 / 8 evaluation settings** ≠ 全部真实仓库;**Footwear 2025** 是最大的未补齐(我们能找到论文但无法在测试环境下载)
- **empirical deployment-gap collapse** 不等于 universality 证明 — 真实数据 gap=0 是观察结论,不是普适定理
- **M5 single-winner 退化** 明确归因到 5-yr 层次稳态数据结构, 不是数据问题
- **FI-Beam-30** 仍是 approximate (穷举 R18 只在 7 expert × 4 period 小实例验证)
- **D_m ≠ d_w** 承认: MTS 抽象 + warehouse physics 之间结构性 gap 是 finding 不是 bug

---

## 10. 论文提交清单(更新 v1.5.5)

- [x] 16 页 5,592 词 — 完整手稿
- [x] 5 张图 — t2_lambda / winning_map / trap_phase / rf_capture / vpm_curve
- [x] 8 张附录表 — R10/R11/R12/R13/R16/R17/R20/R22+R23
- [x] 25 引用 — MTS theory + 仓储 + 算法选择
- [x] §Limitations — 3 类限制全列
- [x] 3 个 §1 contributions(从 5 项压缩)
- [x] §3 formal d_m/d_w 区分
- [x] §9 selector table + total-vs-mean regret footnote
- [x] §11 empirical deployment-gap collapse 措辞
- [x] BFIP 命名 + "conservative benchmark" 替代 "lower bound"
- [ ] Cover letter
- [ ] **首选 IISE Transactions**(其次 M&SOM, 暂不 T-ASE)
- [ ] Code/data availability statement
- [ ] 多 seed CI
- [ ] Supplementary paired per-instance comparison
- [ ] R30 Footwear(尝试 alternative 下载路径)

**当前论文状态: v1.5.5 — 学术封板收尾中,理论结构 + 术语 + 实验 + 限制
均已审查。最大风险是 PoP 引用 + R30 Footwear 关闭。如能完成 R30,即可
进入 cover letter 与 venue 提交阶段。**

---

## 11. 文件索引(本版新增/修改)

```
SPEC_UPDATE_v1.5.md                      # MTS 母体 + 术语规范化
PROGRESS_v1.5.md                         # 上一版(已加 R28b)
PROGRESS_v1.5.5.md                       # 本文件
paper/main.tex v4 (16 pages)            # 论文草稿 v4: 3-contribution + d_m/d_w
world_state/m5_adapter.py                # M5 parquets
world_state/favorita_adapter.py          # Favorita 真实数据
world_state/slaprp_adapter.py            # SLAPRP 真实数据
scripts/run_r26b_favorita.py             # R26b
scripts/run_r28_m5.py                    # R28
scripts/run_r28b_m5_dense.py             # R28b
scripts/run_r29_slaprp.py                # R29
outputs/experiments/r21-r29_*.md         # 9 个真实数据实验
outputs/experiments/REVIEW_v1.5-*.md    # 7 轮自审 (本周)
```

---

## 12. 关键决策日志 (持续更新)

| 决策 | 时机 | 替代方案 | 取舍 |
|------|------|---------|------|
| 不用 sorted L2_stopaware 等复杂模型, 坚持 Zipf 简单合成 | R10 v0.2 | 学习型分布拟合 | 简单 vs 真实性: 走 6 真实数据验证 |
| T1.5: false-switch/move-cost 分别实验 | R14 v1.4 | 单一合并测试 | 分开可归因更清晰 |
| R17: 归因实验 vs 直接 top-1 命中率 | R17 v1.5 | 单一统计 | 3 模型 × 2 schedule 拆出真正归因 |
| Cap E7 to 0.1s for small experiments | R24 v1.4 | 15s everywhere | 速度优先牺牲精度, 大实验仍用 15s |
| M5 单 winner 解释为 "数据结构" 而非 "数据稀疏" | R28b v1.5 | "数据太稀疏" | R28b 9× 数据后仍未变 → 真实结论 |
| 选择 Fixed-Best 而非 OLS 回归对照 | R22 v1.4 | 全部 scikit 默认 | 防止 baseline 比 selector 还好 |
| 找 deployment boundary 的 0% 而非 best classifier | R27 v1.5 | 找 max accuracy | 找负结果而非确认假设 |
| **MTS 挂靠而非 MTS/SOCO 并列** | **v1.5** | **MTS/SOCO** | **MTS 适合离散+combinatorial;SOCO 偏连续+convex, 我们不完全 fit** |
| **d_m vs d_w 区分而非单一 d** | **v1.5** | **单一 d(L,L)** | **d_m 是 metric proxy, d_w 真实劳动成本; gap 本身是 finding** |
| **3 contributions 而非 4** | **v1.5.5** | **5 contributions** | **强 concentration paradox + structural gap 是最强 finding** |
| **"empirical deployment-gap collapse" 而非 "global boundary"** | **v1.5.5** | **"deployment boundary universal"** | **保守:** gap=0 是观察结论,不是普适定理 |
| **"strong conservative benchmark" 而非 "safety lower bound"** | **v1.5.5** | **"lower bound"** | **FixedBest 是可行 policy,不是 cost LB; lower bound 接近 oracle** |
| **S0_Oracle → S0 BFIP** | **v1.5.5** | **"Oracle"** | **BFIP 才是准确命名; Oracle 会让 reviewer 误以为 exact optimum** |
| **首选 IISE Transactions** | **v1.5.5** | **INFORMS** | **IISE ≠ INFORMS; IISE 强调 methodology + engineering** |
| **6 public datasets / 8 settings 而非 "8 independent"** | **v1.5.5** | **"8 sources"** | **M5 sparse/dense 同源;Instacart top/mid 同源** |
| **Footwear: 环境阻挡,而非 "behind wall"** | **v1.5.5** | **"behind auth wall"** | **数据集 CC-BY-4.0;我们环境无 cookies** |
| **暂停 R30 SLAPStack,先封学术** | **v1.5.5** | **continues R30** | **R30 真实仓库几何重要,但 priority 应在 cover letter** |

---

**v1.5.5 状态: 学术封板已 80%,最大未关闭项是 R30 Footwear 数据下载尝试 + multi-seed CI + cover letter。建议明天先 close R30 + PoP citation,再写 cover letter。**

