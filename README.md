# agentic-warehouse-engine

> Agentic Warehouse Decision Engine — v0.1 partial implementation
> 见 `/Users/guohongbin/Downloads/FMCG_Agentic_Warehouse_Decision_Engine_研究与设计_v1.0 (1).pdf` 总设计文档

## 当前进度(spec 12 件 TODO)

| # | 任务 | 状态 | 锚点 |
|---|------|------|------|
| 1 | `cost_weights.toml` | ✅ | Stage 0 |
| 2 | `verify_gate.yaml` | ✅ | Stage 0 |
| 3 | 主指标 `NormalizedCost` 口径 | ✅ partial | Stage 0 / 4 |
| 4 | Canonical schema DDL | ✅ | Stage 1 |
| 5 | Instacart/Favorita 接入 | ⬜(留 v0.2) | Stage 1 |
| 6 | SLAPStack layout 接入 | ⬜(留 v0.2) | Stage 1 |
| 7 | Affinity 计算器 | ✅ R02 | Stage 2 |
| 8 | Warehouse graph + travel-time | ◐ 欧氏 proxy + L1 时间;真实标定待 #6 | Stage 2 |
| 9 | B0 Random + B1 Static ABC + B2 COI | ✅ | Stage 3 |
| 10 | CP-SAT Dynamic Slotting | ✅ R03(stop-count 目标留 v0.3) | Stage 3 |
| 11 | SimPy L1 replay | ✅ R04(未标定) | Stage 4 |
| 12 | Execution Gateway stub | ⬜ | Stage 4 |

**v0.2 完成:11/12 件落地(剩 #5/#6 真实数据、#12 gateway stub、#8 标定)。**

## 实验结果(seed=42, 120 SKU / 60 位置 / 14 天)

> **R05 为排名权威**(时间切分 + 容量公平);R02–R04 的排名声明已被三轮自审撤回(见 `outputs/experiments/REVIEW_v0.2.md`)。

| Run | 内容 | 结果(NormalizedCost vs B1) |
|-----|------|------------------------------|
| R01 | schema + B0/B1/B2(legacy 度量:每行距离) | legacy 基线,仅存档 |
| R02–R04 | affinity / CP-SAT / SimPy(全知协议) | 排名已撤回(违约+泄漏) |
| **R05** | **诚实评估**:slot 1–7 天 / replay 8–14 天,容量审计 | **B4=0.8089** B3=0.8442 B2=0.9707 B0=1.6686(L0);L1: B4=0.9056 B3=0.9189 B0=1.2893;gates 全 PASS |

### 已固化的实验发现(经三轮自审修订)
1. **世界必须有结构**(Zipf 频率 + basket 共现),否则基线无区分度(gate 抓到)
2. **仓库几何必须真实**(5m 小仓在时间度量下抹平差异 → 120m 真实几何)
3. **排序结论前必须做约束公平性审计**(R05):R03 把"B3 违约"误诊为"B4 公式化缺陷";公平条件下 B4 胜 B3
4. **诚实协议压缩一切**:B3 0.4527(违约+全知)→ 0.7136(容量修正)→ 0.8442(时间切分)
5. **度量选择两次被 gate 纠正**:makespan 不敏感 → Σ completion 被 release 主导 → Σ flow time
6. **未被消费的代码也会腐蚀 schema**(forecast zip bug)

## 工作规则(用户规定,长期有效)

**每次更新对完成的结果自审 3 次,再决定下一步**:
1. 第一轮·事实核查 —— 取证(跑代码验证),不靠记忆
2. 第二轮·架构推导 —— 结论是否被证据支撑;撤回/降级不成立的
3. 第三轮·方法论 —— 过程与规则的改进
产出 `outputs/experiments/REVIEW_*.md` 后才进入下一里程碑。

## 设计原则(沿用 spec §8.4 自审后 8 条)

1. **State-centric**: World State 是唯一事实中心
2. **Bounded autonomy**: 任何自动动作必须有边界 + 审批
3. **Solver-verified**: (等 #10 落地)
4. **Counterfactual before execute**: (等 #11 落地)
5. **Progressive disclosure**: schema 自带 `known_at_time` / `lineage` / `constraint_version`
6. **Multi-timescale**: (Ch.15 设计层面,v0.1 不入环)
7. **Economic explainability**: 每个 `decision_plan` 含 `expected_cost + baseline_cost + confidence`
8. **Data lineage**: `source_type` ∈ {observed, derived, synthetic} 强制字段

## 5 阶段 pipeline(模仿 `cultivating-ml-agent`)

- Stage 0: `config/`
- Stage 1: `world_state/sample.py` + `world_state/validate.py`
- Stage 2: (留 v0.2)
- Stage 3: `or_experts/b{0,1}_*.py`
- Stage 4: `evaluation/compute_normalized_cost.py`

## 运行

```bash
export PATH=/opt/homebrew/Caskroom/miniconda/base/bin:$PATH
python scripts/run_r01_schema_and_baselines.py
```

输出 → `outputs/experiments/r01_schema_and_baselines.md`
