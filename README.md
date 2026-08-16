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
| 7 | Affinity 计算器 | ⬜ | Stage 2 |
| 8 | Warehouse graph + travel-time | ⬜(用欧氏距离 proxy) | Stage 2 |
| 9 | B0 Random + B1 Static ABC | ✅ | Stage 3 |
| 10 | CP-SAT Dynamic Slotting | ⬜ | Stage 3 |
| 11 | SimPy L1 replay | ⬜ | Stage 4 |
| 12 | Execution Gateway stub | ⬜ | Stage 4 |

**v0.1 最小闭环已建(8 件),剩 4 件留到下个 milestone。**

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
