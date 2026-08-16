"""
scripts/run_r19_metric_properties.py
— R19: SPEC v1.5 §3.3 — d(L_t, L_{t+1}) metric properties + MTS connection.

Checks on ACTUAL expert-produced layout pairs (from the sequential benchmark):
  1. Symmetry: d(L1,L2) = d(L2,L1) — trivially true for n_moves/total-distance
  2. Triangle inequality: d(L1,L3) ≤ d(L1,L2) + d(L2,L3) — verify on sampled
     layout triples from actual trajectories
  3. Where warehouse structure VIOLATES the clean MTS formulation:
     - asymmetric costs (open vs close pick-face)
     - capacity-constrained transitions (infeasible ≠ costly)
     - batch effects (multiple moves in same period)
     - sequence-dependence (swap chains require intermediate states)
  4. Empirical distribution of d across expert transitions

Output: outputs/experiments/r19_metric_properties.md
"""

from __future__ import annotations

import argparse
import itertools
import random
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from world_state import sample as sampler
from world_state.regime_sequence import build_sequence, generate_stream
from simulation.sequential import SequentialBenchmark
from or_experts.policies import EXPERT_IDS, run_policy


def n_moves(l1, l2):
    return sum(1 for s in l1 if l1[s] != l2.get(s))


def total_move_dist(l1, l2, xyz):
    import math
    d = 0.0
    for s in l1:
        if l1[s] != l2.get(s) and l2.get(s) in xyz and l1[s] in xyz:
            d += math.dist(xyz[l1[s]], xyz[l2[s]])
    return d


def main():
    cfg = yaml.safe_load(open(ROOT / "config" / "main_config.yaml"))
    ws = cfg["world_state"]

    # build one world and collect actual layouts from expert trajectories
    seed = 17
    rng = random.Random(seed)
    sm = sampler.make_sku_master(ws["n_skus"], rng)
    ids = [s.sku_id for s in sm]
    cat = {s.sku_id: s.category_id for s in sm}
    locs, xyz = sampler.make_locations(ws["n_locations"], rng)
    anchor = datetime(2025, 1, 1, tzinfo=timezone.utc)
    seq = build_sequence(ids)
    o, l = generate_stream(ids, cat, seq, rng, anchor)
    bench = SequentialBenchmark(sm, locs, xyz, o, l, seq, anchor)

    # collect all layouts produced at period 1 (each expert from cold start)
    current, plans = bench._prepare_periods(seed)
    layouts = {}
    for e in EXPERT_IDS:
        layouts[e] = run_policy(e, plans[0].view, current, plans[0].mc_unit).layout

    # also collect across-period layouts on the myopic path
    m = bench.run(seed_for_view=seed)
    path_layouts = [current] + [pr.layout_after for pr in m.periods]

    # --- 1. Symmetry (trivial for both measures) ---
    sym_ok = True
    for (ea, la), (eb, lb) in itertools.combinations(layouts.items(), 2):
        if n_moves(la, lb) != n_moves(lb, la):
            sym_ok = False
    print(f"[1] Symmetry (n_moves): {'HOLDS' if sym_ok else 'VIOLATED'} (trivially — Hamming)")

    # --- 2. Triangle inequality on actual layout triples ---
    layout_list = list(layouts.values()) + path_layouts
    tri_checked = tri_violated = 0
    for triple in itertools.combinations(layout_list[:15], 3):
        L1, L2, L3 = triple
        d12, d23, d13 = n_moves(L1, L2), n_moves(L2, L3), n_moves(L1, L3)
        tri_checked += 1
        if d13 > d12 + d23:
            tri_violated += 1
    # also for total_move_dist
    tri_dist_violated = 0
    for triple in itertools.combinations(layout_list[:15], 3):
        L1, L2, L3 = triple
        d12 = total_move_dist(L1, L2, xyz)
        d23 = total_move_dist(L2, L3, xyz)
        d13 = total_move_dist(L1, L3, xyz)
        if d13 > d12 + d23 + 1e-9:
            tri_dist_violated += 1
    print(f"[2] Triangle inequality (n_moves): {tri_checked - tri_violated}/{tri_checked} hold "
          f"({tri_violated} violations)")
    print(f"    Triangle inequality (total-dist): {tri_checked - tri_dist_violated}/{tri_checked} hold "
          f"({tri_dist_violated} violations)")

    # --- 3. Empirical d distribution across expert transitions ---
    print("\n[3] Pairwise n_moves between experts (period-1 layouts):")
    header = "       " + " ".join(f"{e.split('_')[0]:>4s}" for e in EXPERT_IDS)
    print(header)
    for ea in EXPERT_IDS:
        row = f"  {ea.split('_')[0]:>4s} "
        for eb in EXPERT_IDS:
            row += f"{n_moves(layouts[ea], layouts[eb]):4d} "
        print(row)

    # --- 4. MTS structure vs warehouse-specific violations ---
    print("\n[4] Warehouse-specific violations of clean MTS:")
    print("  a. ASYMMETRY: opening vs closing a pick-face has different setup/teardown")
    print("     costs — d(L1,L2) != d(L2,L1) under these cost components")
    print("     (not captured by n_moves or Euclidean distance)")
    print("  b. CAPACITY: transitions violating ceil(n/L) are INFEASIBLE (hard")
    print("     constraint), not merely costly — MTS assumes all states reachable")
    print("  c. BATCHING: k moves in one period cost != k * (1 move) — shared")
    print("     forklift mobilization, aisle congestion, labor windows")
    print("  d. SEQUENCE: swap A<->B requires temp location C (or double-handling);")
    print("     the METRIC sees d=2 but the PHYSICAL execution may cost 3+ moves")
    print("     -> d(L,L') underestimates true reconfiguration labor for swaps")

    # quantify swap prevalence (how many transitions involve swaps vs pure moves)
    swap_count = pure_move = 0
    for (ea, la), (eb, lb) in itertools.combinations(layouts.items(), 2):
        moved_a = {s for s in la if la[s] != lb.get(s)}
        moved_b = {s for s in lb if lb[s] != la.get(s)}
        # swap: two SKUs exchanged locations
        locs_a = {la[s]: s for s in moved_a if s in lb}
        locs_b = {lb[s]: s for s in moved_b if s in la}
        for loc in set(locs_a) & set(locs_b):
            if locs_a[loc] != locs_b[loc]:
                swap_count += 1
    print(f"\n  Swap pairs detected across expert layout pairs: {swap_count}")
    print(f"  (each swap's true cost >= 2 moves but may need 3 with temp storage)")

    # --- 5. Write report ---
    expert_tbl = "\n".join(
        f"| {ea.split('_')[0]} | " + " | ".join(
            str(n_moves(layouts[ea], layouts[eb])) for eb in EXPERT_IDS) + " |"
        for ea in EXPERT_IDS)

    out = ROOT / "outputs" / "experiments" / "r19_metric_properties.md"
    out.write_text(f"""# R19 — d(L,L) 度量性质与 MTS 连接(SPEC v1.5 §3.3)

**Date**: {datetime.now(timezone.utc).isoformat()} | world = {ws['n_skus']} SKU / {ws['n_locations']} loc | seed = {seed}

## 1. 对称性
n_moves(Hamming)与 total_move_dist(Euclidean 和)**天然对称** ✓

## 2. 三角不等式(实际布局三元组,{tri_checked} 组)
- n_moves: **{tri_checked - tri_violated}/{tri_checked} 成立**(Hamming 距离满足三角不等式,理论保证)
- total_move_dist: **{tri_checked - tri_dist_violated}/{tri_checked} 成立**(逐 SKU Euclidean 三角不等式的直接推论)

**结论:两种 d 均构成合法度量 → MTS 框架的度量空间假设满足**

## 3. 专家间 n_moves 矩阵(实际 period-1 布局)

| | {' | '.join(e.split('_')[0] for e in EXPERT_IDS)} |
|{'---|' * (len(EXPERT_IDS) + 1)}
{expert_tbl}

## 4. 仓储特异性:何处违反干净 MTS 假设

| # | 违反 | 描述 | 影响 |
|---|------|------|------|
| a | **成本不对称** | 开设 vs 撤销 pick-face 的 setup/teardown 成本不同 | d(L1,L2) ≠ d(L2,L1) 在真实成本下 |
| b | **硬约束不可达** | 违反容量约束的状态转移不可行(不是"贵"而是"不可能") | MTS 假设状态空间连通 |
| c | **批量效应** | k 次搬库 ≠ k × 单次成本(共享叉车调度、通道拥堵) | d 的线性可加性被破坏 |
| d | **交换链** | A↔B 互换需要中间位 C(n_moves=2 但物理 3+ 步) | d 系统性低估真实重配置劳动 |

检出 swap 对:{swap_count}(每个 swap 的真实成本 ≥ n_moves 计数)

## 5. 判读

- **n_moves 和 total_move_dist 都是合法度量**(对称 + 三角不等式)→ 理论上
  DWERP 可以嵌入标准 MTS 框架
- 但 **4 类仓储特异性**使真实 C_trans 偏离干净度量 → 论文表述:
  "warehouse-specific generalized switching cost"(广义切换成本)
- T1.5 的 Hidden Reconfig(17–69%)是**指示罚 vs 物理距离**失真的实证;
  本节给出的是**物理距离 vs 真实劳动成本**的进一步失真来源
- 论文 Related Work:MTS 的 work-function 算法与 "lazy" 策略在我们的
  R17 发现(保守 = 保护)中有直接对应
""")
    print(f"\nwrote outputs/experiments/r19_metric_properties.md")


if __name__ == "__main__":
    main()
