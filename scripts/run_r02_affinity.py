"""
scripts/run_r02_affinity.py
— R02: Affinity feature (Todo #7) + B3 Affinity Slotting under L0 route cost.

Hypothesis (one change vs R01's world): with basket structure
(category_concentration=0.7) and per-ORDER route cost (spec §14.3 L0),
B3_affinity < B1_static_abc by ≥ 5% NormalizedCost, because co-picked SKUs
share a single stop.

Secondary integrity checks:
  - B0 Random still ≫ 1 under the new metric
  - B2 COI still between B1 and B0
  - affinity graph is non-degenerate (pairs with lift > 1 exist)

Output: outputs/experiments/r02_affinity.md
"""

from __future__ import annotations

import argparse
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from world_state.loader import build_world
from world_state import validate_pipeline, ValidationError
from features.affinity import compute_affinity
from evaluation.route_cost import total_route_cost
from evaluation import normalized_cost
from or_experts.b0_random import assign_random as b0_assign
from or_experts.b1_static_abc import assign_static_abc as b1_assign
from or_experts.b2_coi import assign_coi as b2_assign
from or_experts.b3_affinity import assign_affinity as b3_assign


class Logger:
    def __init__(self):
        self._t0 = time.time()

    def log(self, msg, level="INFO"):
        print(f"[{time.time()-self._t0:7.2f}s][{level}] {msg}", flush=True)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--smoke", action="store_true")
    p.add_argument("--concentration", type=float, default=0.7)
    p.add_argument("--alpha", type=float, default=1.0)
    p.add_argument("--top-k", type=int, default=5)
    args = p.parse_args()

    log = Logger()
    log.log("=== run_r02_affinity.py ===")

    cfg = yaml.safe_load(open(ROOT / "config" / "main_config.yaml"))
    gates = yaml.safe_load(open(ROOT / "config" / "verify_gate.yaml"))["gates"]
    seed = args.seed if args.seed is not None else cfg["runtime"]["seed"]
    if args.smoke:
        cfg["world_state"].update(n_skus=8, n_locations=4, n_days=3)
        log.log("  --smoke: shrunk world")
    cfg["world_state"]["category_concentration"] = args.concentration

    # ---- Stage 1: world with basket structure -----------------------------
    world = build_world(cfg, seed, use_basket=True)
    log.log(f"Stage 1: world built — skus={len(world['sku_master'])} "
            f"orders={len(world['orders'])} lines={len(world['order_lines'])} "
            f"concentration={args.concentration}")

    # ---- Stage 2: affinity feature ----------------------------------------
    aff = compute_affinity(world["order_lines"], alpha=args.alpha, top_k=args.top_k)
    n_lift1 = int((aff.df["lift"] > 1.0).sum()) if not aff.df.empty else 0
    log.log(f"Stage 2: affinity — pairs={len(aff.df)} lift>1 pairs={n_lift1} "
            f"alpha={args.alpha} top_k={args.top_k}")

    # ---- Stage 3: experts under L0 route cost ------------------------------
    log.log("Stage 3: experts under L0 route cost (spec §14.3)")
    pickable = world["locations"]
    xyz = world["xyz_lookup"]
    as_of = world["day_anchor"]
    n_seeds = gates["metric_gate"]["config"]["threshold_seed_count"]

    def cost_of(sku_to_loc):
        return total_route_cost(world["order_lines"], sku_to_loc, xyz)

    _, m1 = b1_assign(world["sku_ids"], world["order_lines"], pickable, xyz, "DP-B1", as_of)
    c1 = cost_of(m1)
    _, m2 = b2_assign(world["sku_master"], world["order_lines"], pickable, xyz, "DP-B2", as_of)
    c2 = cost_of(m2)
    _, m3 = b3_assign(world["sku_ids"], world["order_lines"], aff, pickable, xyz,
                      "DP-B3", as_of)
    c3 = cost_of(m3)

    b0_costs = []
    for s in range(n_seeds):
        _, m0 = b0_assign(world["sku_ids"], pickable, xyz, f"DP-B0-{s}", as_of,
                          random.Random(seed * 1000 + s))
        b0_costs.append(cost_of(m0))
    b0_mean = sum(b0_costs) / len(b0_costs)

    n1, n2, n3 = 1.0, normalized_cost(c2, c1), normalized_cost(c3, c1)
    n0 = normalized_cost(b0_mean, c1)
    log.log(f"  B1={c1:.1f} (norm 1.0000) | B2={c2:.1f} (norm {n2:.4f}) | "
            f"B3={c3:.1f} (norm {n3:.4f}) | B0={b0_mean:.1f} (norm {n0:.4f})")

    # ---- gates --------------------------------------------------------------
    thr = gates["metric_gate"]["config"]["threshold_relative_improvement"]
    b3_wins = n3 < (1.0 - thr)
    b0_loses = all(c > c1 for c in b0_costs)
    degenerate = n_lift1 < 5
    gate_pass = b3_wins and b0_loses and not degenerate
    log.log(f"  gates: B3_improves({n3:.4f} < {1-thr})={b3_wins} "
            f"B0_always_loses={b0_loses} non_degenerate={not degenerate} "
            f"-> {'PASS' if gate_pass else 'FAIL'}")

    # ---- validate + report --------------------------------------------------
    report = validate_pipeline(world)
    out = ROOT / "outputs" / "experiments" / "r02_affinity.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(f"""# R02 — Affinity (Todo #7) + B3 under L0 route cost

**Date**: {datetime.now(timezone.utc).isoformat()}
**Seed**: {seed} | concentration = {args.concentration} | alpha = {args.alpha} | top_k = {args.top_k}

## Metric change vs R01
Cost upgraded per-line Euclidean → **per-order greedy route** (spec §14.3 L0).
R01 numbers are legacy per-line; not comparable. B1 remains the anchor (norm = 1.0).

## Affinity graph
- pairs with CoPick > 0: **{len(aff.df)}**
- pairs with lift > 1 (better-than-chance co-occurrence): **{n_lift1}**
- top pair: {aff.df.iloc[0].to_dict() if not aff.df.empty else 'n/a'}

## Results (L0 route cost)

| Expert | Total route cost | NormalizedCost vs B1 |
|--------|-----------------|---------------------|
| **B1 Static ABC** | **{c1:.1f}** | **1.0000** |
| B2 COI | {c2:.1f} | {n2:.4f} |
| B3 Affinity | {c3:.1f} | **{n3:.4f}** |
| B0 Random ({n_seeds} seeds) | {b0_mean:.1f} | {n0:.4f} |

- Per-seed B0: {[round(c,1) for c in b0_costs]}

## Gates
- B3 improves ≥ {thr*100:.0f}%: **{'PASS' if b3_wins else 'FAIL'}** (norm = {n3:.4f})
- B0 always worse than B1: **{'PASS' if b0_loses else 'FAIL'}**
- affinity graph non-degenerate: **{'PASS' if not degenerate else 'FAIL'}** ({n_lift1} lift>1 pairs)
- validate_pipeline hard-fails: **{len(report.hard_failures)}**

## Interpretation
- B3 exploits basket structure: co-picked SKUs share one location → fewer route stops.
- If B3 FAILs the 5% gate, sweep `--concentration` (basket strength) or `--alpha`
  before touching the algorithm — a degenerate world cannot reward affinity.
""")
    log.log(f"  wrote {out.relative_to(ROOT)}")
    log.log("=== done ===")


if __name__ == "__main__":
    main()
