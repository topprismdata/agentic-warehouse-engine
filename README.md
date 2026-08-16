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

| Run | 内容 | 结果(NormalizedCost vs B1) |
|-----|------|------------------------------|
| R01 | schema + B0/B1/B2(legacy 度量:每行距离) | B1=1.00 B2=1.11 B0=1.71 |
| R02 | Affinity + L0 route 度量 + B3 | **B3=0.4527** B2=1.13 B0=1.79 |
| R03 | B4 CP-SAT(λ sweep) | **B4(λ=0)=0.6654 OPT**(未胜 B3,公式化留 v0.3) |
| R04 | SimPy L1 replay(Σ flow time) | B3=0.6987 B4=0.8489 B2=1.0554 B0=1.3212,L0/L1 排序一致 |

### 已固化的实验发现
1. **世界必须有结构**(Zipf 频率 + basket 共现),否则基线无区分度(gate 抓到)
2. **仓库几何必须真实**(v0.1 的 5m 小仓在时间度量下抹平一切差异 → 放大到 120m)
3. **L0(距离)→ L1(时间)必须过 ranking-preservation 检查**:小世界中 B3/B4 排序翻转是 travel 被压缩的伪影
4. **CP-SAT 的 affinity rank-distance 线性化与 route metric 错位**:λ↑ 反而变差;容量约束(2/位置)下不敌 B3 共停启发式;正确公式化需 stop-count 项(v0.3)
5. **度量选择两次被 gate 纠正**:makespan 不敏感(低利用率)→ Σ completion 被 release 主导 → Σ flow time 正确

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
