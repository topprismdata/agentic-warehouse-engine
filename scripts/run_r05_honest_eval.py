"""
scripts/run_r05_honest_eval.py
— R05: honest evaluation after the v0.2 three-round review.

Fixes applied by this run (see outputs/experiments/REVIEW_v0.2.md):
  F1  Time-split protocol (spec §4.3/§16.1): experts slot on days 1-7 ONLY,
      evaluation replays days 8-14. No clairvoyant slotting.
  F2  Capacity-fair fight (spec §10.4): every expert's plan is audited with
      count_capacity_violations; any violation is a hard gate failure.
  F6  Non-vacuous validate: assignments + DecisionPlans are persisted into
      the world state BEFORE validate_pipeline (R02-R04 validated an empty
      world — gate theater).

Hypothesis: under the honest protocol the ranking persists but the gaps
COMPRESS (affinity estimated on 7 days is noisier; capacity-bound B3 loses
its illegal co-location edge). Whatever the outcome, these numbers supersede
R02-R04 for ranking claims.

Output: outputs/experiments/r05_honest_eval.md
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
from world_state import validate_pipeline
from features.affinity import compute_affinity
from simulation.replay import replay, ReplayConfig
from evaluation.route_cost import total_route_cost
from evaluation.audit import count_capacity_violations
from evaluation import normalized_cost
from or_experts.b0_random import assign_random as b0_assign, build_decision_plan as b0_plan
from or_experts.b1_static_abc import assign_static_abc as b1_assign, build_decision_plan as b1_plan
from or_experts.b2_coi import assign_coi as b2_assign, build_decision_plan as b2_plan
from or_experts.b3_affinity import assign_affinity as b3_assign, build_decision_plan as b3_plan
from or_experts.b4_cpsat import solve_cpsat, build_decision_plan as b4_plan


class Logger:
    def __init__(self):
        self._t0 = time.time()

    def log(self, msg, level="INFO"):
        print(f"[{time.time()-self._t0:7.2f}s][{level}] {msg}", flush=True)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--smoke", action="store_true")
    p.add_argument("--split-day", type=int, default=7)
    p.add_argument("--n-pickers", type=int, default=3)
    args = p.parse_args()

    log = Logger()
    log.log("=== run_r05_honest_eval.py ===")

    cfg = yaml.safe_load(open(ROOT / "config" / "main_config.yaml"))
    gates = yaml.safe_load(open(ROOT / "config" / "verify_gate.yaml"))["gates"]
    seed = args.seed if args.seed is not None else cfg["runtime"]["seed"]
    n_days = cfg["world_state"]["n_days"]
    split_day = min(args.split_day, n_days - 1)
    if args.smoke:
        cfg["world_state"].update(n_skus=20, n_locations=10, n_days=4)
        split_day = 2
        log.log("  --smoke: shrunk world (split at day 2)")
    cfg["world_state"]["category_concentration"] = 0.7

    world = build_world(cfg, seed, use_basket=True)
    xyz, pickable, as_of = world["xyz_lookup"], world["locations"], world["day_anchor"]
    orders, lines = world["orders"], world["order_lines"]

    # ---- F1: time split (slot on history, replay on future) ----------------
    t0 = as_of
    hist_orders = [o for o in orders if (o.order_time - t0).days < split_day]
    fut_orders = [o for o in orders if (o.order_time - t0).days >= split_day]
    hist_ids = {o.order_id for o in hist_orders}
    hist_lines = [ln for ln in lines if ln.order_id in hist_ids]
    fut_lines = [ln for ln in lines if ln.order_id not in hist_ids]
    log.log(f"Stage 1: split@day{split_day} — history {len(hist_orders)} orders/"
            f"{len(hist_lines)} lines | future {len(fut_orders)} orders/{len(fut_lines)} lines")

    # ---- experts slot on HISTORY ONLY --------------------------------------
    log.log("Stage 3: experts slot on history; evaluation on future")
    n_seeds = gates["metric_gate"]["config"]["threshold_seed_count"]
    sim_cfg = ReplayConfig(n_pickers=args.n_pickers)

    def audit(m):
        return count_capacity_violations(m, len(pickable))

    a1, m1 = b1_assign(world["sku_ids"], hist_lines, pickable, xyz, "DP-B1", as_of)
    a2, m2 = b2_assign(world["sku_master"], hist_lines, pickable, xyz, "DP-B2", as_of)
    aff_h = compute_affinity(hist_lines)
    a3, m3 = b3_assign(world["sku_ids"], hist_lines, aff_h, pickable, xyz, "DP-B3", as_of)
    a4, m4, rep4 = solve_cpsat(world["sku_ids"], hist_lines, aff_h, pickable, xyz,
                               lambda_affinity=0.0, time_budget_s=10.0)
    if rep4.status != "feasible":
        log.log("  CP-SAT infeasible — abort", "ERROR")
        sys.exit(2)
    b0_maps, b0_assigns = [], []
    for s in range(n_seeds):
        a0, m0 = b0_assign(world["sku_ids"], pickable, xyz, f"DP-B0-{s}", as_of,
                           random.Random(seed * 1000 + s))
        b0_maps.append(m0)
        b0_assigns.append(a0)

    experts = [("B1_StaticABC", m1, a1), ("B2_COI", m2, a2),
               ("B3_Affinity", m3, a3), ("B4_CPSAT(l=0)", m4, a4)]

    # ---- F2: capacity audit (hard gate) ------------------------------------
    viol = {name: audit(m) for name, m, _ in experts}
    viol_b0 = [audit(m) for m in b0_maps]
    any_viol = any(viol.values()) or any(viol_b0)
    log.log(f"  capacity audit: violations = "
            f"{ {k: len(v) for k, v in viol.items()} } | B0 = {[len(v) for v in viol_b0]}")

    # ---- L0 + L1 on FUTURE --------------------------------------------------
    l0 = {name: total_route_cost(fut_lines, m, xyz) for name, m, _ in experts}
    b0_l0 = [total_route_cost(fut_lines, m, xyz) for m in b0_maps]
    base_l0 = l0["B1_StaticABC"]

    def flow(r):
        return r.total_wait_s + r.total_travel_s + r.total_pick_s

    l1 = {name: flow(replay(fut_orders, fut_lines, m, xyz, sim_cfg)) for name, m, _ in experts}
    b0_flow = [flow(replay(fut_orders, fut_lines, m, xyz, sim_cfg)) for m in b0_maps]
    base_l1 = l1["B1_StaticABC"]

    log.log("  L0 (future):  " + "  ".join(
        f"{n}={normalized_cost(c, base_l0):.4f}" for n, c in l0.items())
        + f"  B0={normalized_cost(sum(b0_l0)/len(b0_l0), base_l0):.4f}")
    log.log("  L1 (future):  " + "  ".join(
        f"{n}={normalized_cost(c, base_l1):.4f}" for n, c in l1.items())
        + f"  B0={normalized_cost(sum(b0_flow)/len(b0_flow), base_l1):.4f}")

    # ---- F6: non-vacuous validate -------------------------------------------
    world["slot_assignment"] = a1 + a2 + a3 + a4 + b0_assigns[-1]
    world["decision_plan"] = [
        b1_plan(a1, expected_cost=l0["B1_StaticABC"], baseline_cost=base_l0),
        b2_plan(a2, expected_cost=l0["B2_COI"], baseline_cost=base_l0),
        b3_plan(a3, expected_cost=l0["B3_Affinity"], baseline_cost=base_l0),
        b4_plan(a4, expected_cost=l0["B4_CPSAT(l=0)"], baseline_cost=base_l0, report=rep4),
        b0_plan(b0_assigns[-1], expected_cost=b0_l0[-1], baseline_cost=base_l0),
    ]
    report = validate_pipeline(world)
    log.log(f"  validate_pipeline (non-vacuous): {report.summary()}")

    # ---- gates ---------------------------------------------------------------
    order_l0 = sorted(l0, key=l0.get)
    order_l1 = sorted(l1, key=l1.get)
    ranking_consistent = order_l0 == order_l1
    b0_worst = all(c > base_l0 for c in b0_l0) and all(c > base_l1 for c in b0_flow)
    gate_pass = (not any_viol) and b0_worst and report.is_clean()
    log.log(f"  gates: zero_capacity_violations={not any_viol} B0_worst(L0&L1)={b0_worst} "
            f"validate_clean={report.is_clean()} ranking_L0==L1={ranking_consistent} "
            f"-> {'PASS' if gate_pass else 'FAIL'}")

    # in-sample vs honest delta for B3 (the headline correction)
    aff_full = compute_affinity(lines)
    _, m3_ins = b3_assign(world["sku_ids"], lines, aff_full, pickable, xyz, "X", as_of)
    b3_ins = normalized_cost(total_route_cost(lines, m3_ins, xyz),
                             total_route_cost(lines, m1, xyz))
    b3_honest = normalized_cost(l0["B3_Affinity"], base_l0)
    log.log(f"  B3 inflation: in-sample {b3_ins:.4f} -> honest {b3_honest:.4f} "
            f"(delta = {b3_ins - b3_honest:+.4f})")

    rows = "\n".join(
        f"| {name} | {normalized_cost(l0[name], base_l0):.4f} | "
        f"{normalized_cost(l1[name], base_l1):.4f} | {len(viol[name])} |"
        for name, _, _ in experts
    )
    out = ROOT / "outputs" / "experiments" / "r05_honest_eval.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(f"""# R05 — honest evaluation: time-split + capacity-fair (supersedes R02-R04 rankings)

**Date**: {datetime.now(timezone.utc).isoformat()} | seed = {seed} | split@day{split_day} | pickers = {args.n_pickers}

## Protocol fixes (v0.2 three-round review)
- **F1 leakage**: experts slot on days 1-{split_day} ONLY; evaluation replays days {split_day + 1}-{n_days}. No clairvoyant slotting (spec §4.3, §16.1).
- **F2 fairness**: capacity = ceil(n/L) audited per expert — the same hard constraint CP-SAT obeys (spec §10.4). B3 now splits clusters instead of overflowing.
- **F6 gates**: validate_pipeline runs on a world WITH assignments + decision plans (R02-R04 validated an empty world).

## Results (both metrics on FUTURE orders only; B1 slotted-on-history anchor = 1.0)

| Expert | L0 norm (honest) | L1 norm (honest) | capacity violations |
|--------|------------------|------------------|---------------------|
{rows}
| B0 Random ({n_seeds} seeds) | {normalized_cost(sum(b0_l0)/len(b0_l0), base_l0):.4f} | {normalized_cost(sum(b0_flow)/len(b0_flow), base_l1):.4f} | 0 |

## The headline correction (B3's three numbers)
- R02 reported: **0.4527** (capacity-violating + clairvoyant — invalid)
- capacity-fixed, still clairvoyant (full 14 d used for both): **{b3_ins:.4f}**
- honest (slot on 1-{split_day}, replay {split_day + 1}-{n_days}): **{b3_honest:.4f}**
- leakage correction: **{b3_ins - b3_honest:+.4f}**

## Gates
- zero capacity violations (all experts incl. B0): **{'PASS' if not any_viol else 'FAIL'}**
- B0 worst on both L0 and L1 (all seeds): **{'PASS' if b0_worst else 'FAIL'}**
- validate_pipeline clean (non-vacuous, {len(world['slot_assignment'])} assignments + {len(world['decision_plan'])} plans): **{'PASS' if report.is_clean() else 'FAIL'}**
- L0/L1 ranking consistency: **{'PRESERVED' if ranking_consistent else 'FLIPPED'}** (L0: {order_l0} / L1: {order_l1})

## Interpretation
- These numbers **supersede R02-R04** for any ranking claim.
- Gap compression vs in-sample is expected: affinity from {split_day} days is noisier, and B3 lost its illegal >capacity co-locations.
- Whatever the honest ranking is, it is the first number in this repo that would survive the spec's own §4.3 replay discipline.
""")
    log.log(f"  wrote {out.relative_to(ROOT)}")
    log.log("=== done ===")


if __name__ == "__main__":
    main()
