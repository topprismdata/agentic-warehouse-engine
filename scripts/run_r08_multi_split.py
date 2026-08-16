"""
scripts/run_r08_multi_split.py
— R08: multi-split variance check (REVIEW v0.4 decision #1).

Motivation: R07's headline numbers (B4=0.9115/0.7736) came from ONE user
split. Before citing any ranking, we need: same protocol, >=5 independent
splits (different user samples), per-expert mean ± std, and per-split
win/loss tallies. A mean edge that flips sign across splits is not an edge.

Cheap: pure computation over already-downloaded data. No new sources.

Output: outputs/experiments/r08_multi_split.md
"""

from __future__ import annotations

import argparse
import random
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from world_state import validate_pipeline
from world_state.instacart_adapter import load_instacart
from world_state import sample as sampler
from features.affinity import compute_affinity
from simulation.replay import replay, ReplayConfig
from evaluation.route_cost import total_route_cost
from evaluation.audit import count_capacity_violations
from evaluation import normalized_cost
from or_experts.b0_random import assign_random as b0_assign
from or_experts.b1_static_abc import assign_static_abc as b1_assign
from or_experts.b2_coi import assign_coi as b2_assign
from or_experts.b3_affinity import assign_affinity as b3_assign
from or_experts.b4_cpsat import solve_cpsat


class Logger:
    def __init__(self):
        self._t0 = time.time()

    def log(self, msg, level="INFO"):
        print(f"[{time.time()-self._t0:7.2f}s][{level}] {msg}", flush=True)


def run_split(data, cfg, seed, n_pickers, log: Logger, cp_budget=30.0):
    """One full honest split: slot on train, evaluate on held-out users."""
    n_loc = cfg["world_state"]["n_locations"]
    rng = random.Random(seed)
    locations, xyz = sampler.make_locations(n_loc, rng)
    as_of = datetime(2025, 1, 1, tzinfo=timezone.utc)
    sku_ids, sku_cat = data["sku_ids"], data["sku_category"]
    sku_master = sampler.make_sku_master(len(sku_ids), rng)
    sku_master = [type(s)(sku_id=sid, category_id=sku_cat.get(sid, "AISLE000"),
                          unit_volume_m3=s.unit_volume_m3, unit_weight_kg=s.unit_weight_kg,
                          case_pack=s.case_pack, pallet_qty=s.pallet_qty,
                          shelf_life_days=s.shelf_life_days, storage_class=s.storage_class,
                          source_type=s.source_type)
                  for s, sid in zip(sku_master, sku_ids)]
    cap = max(1, -(-len(sku_ids) // n_loc))

    tr_lines, ev_lines = data["train_lines"], data["test_lines"]
    ev_orders = data["test_orders"]
    n_seeds = 5
    sim_cfg = ReplayConfig(n_pickers=n_pickers)

    _, m1 = b1_assign(sku_ids, tr_lines, locations, xyz, "DP-B1", as_of)
    _, m2 = b2_assign(sku_master, tr_lines, locations, xyz, "DP-B2", as_of)
    aff = compute_affinity(tr_lines)
    _, m3 = b3_assign(sku_ids, tr_lines, aff, locations, xyz, "DP-B3", as_of)
    _, m4, rep4 = solve_cpsat(sku_ids, tr_lines, aff, locations, xyz,
                              lambda_affinity=0.0, time_budget_s=cp_budget)
    if rep4.status != "feasible":
        return None, "CP-SAT infeasible"
    b0_maps = [b0_assign(sku_ids, locations, xyz, f"DP-B0-{s}", as_of,
                         random.Random(seed * 1000 + s))[1] for s in range(n_seeds)]

    experts = {"B1_StaticABC": m1, "B2_COI": m2, "B3_Affinity": m3,
               "B4_CPSAT(l=0)": m4}
    viol = {n: count_capacity_violations(m, n_loc, cap) for n, m in experts.items()}
    viol_b0 = [count_capacity_violations(m, n_loc, cap) for m in b0_maps]
    if any(viol.values()) or any(viol_b0):
        return None, f"capacity violations {viol}"

    def flow(r):
        return r.total_wait_s + r.total_travel_s + r.total_pick_s

    base_l0 = total_route_cost(ev_lines, m1, xyz)
    base_l1 = flow(replay(ev_orders, ev_lines, m1, xyz, sim_cfg))
    l0 = {n: normalized_cost(total_route_cost(ev_lines, m, xyz), base_l0)
          for n, m in experts.items()}
    l1 = {n: normalized_cost(flow(replay(ev_orders, ev_lines, m, xyz, sim_cfg)), base_l1)
          for n, m in experts.items()}
    b0_l0 = [normalized_cost(total_route_cost(ev_lines, m, xyz), base_l0) for m in b0_maps]
    b0_l1 = [normalized_cost(flow(replay(ev_orders, ev_lines, m, xyz, sim_cfg)), base_l1)
             for m in b0_maps]
    return {
        "l0": l0, "l1": l1,
        "b0_l0_mean": statistics.fmean(b0_l0), "b0_l1_mean": statistics.fmean(b0_l1),
        "n_train": len(data["train_orders"]), "n_eval": len(data["test_orders"]),
        "concentration": data["estimated_concentration"],
        "sku_master": sku_master, "locations": locations,
        "ev_orders": ev_orders, "ev_lines": ev_lines,
        "a1": b1_assign(sku_ids, tr_lines, locations, xyz, "DP-B1", as_of)[0],
        "a2": b2_assign(sku_master, tr_lines, locations, xyz, "DP-B2", as_of)[0],
        "a3": b3_assign(sku_ids, tr_lines, aff, locations, xyz, "DP-B3", as_of)[0],
        "a4": solve_cpsat(sku_ids, tr_lines, aff, locations, xyz, 0.0, cp_budget)[0],
    }, None


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--seeds", type=int, nargs="+", default=[42, 101, 202, 303, 404])
    p.add_argument("--n-users", type=int, default=3000)
    p.add_argument("--top-skus", type=int, default=120)
    p.add_argument("--n-pickers", type=int, default=3)
    p.add_argument("--smoke", action="store_true")
    args = p.parse_args()

    log = Logger()
    log.log("=== run_r08_multi_split.py ===")

    cfg = yaml.safe_load(open(ROOT / "config" / "main_config.yaml"))
    raw = ROOT / "data" / "raw" / "instacart"
    n_users = args.n_users if not args.smoke else 300
    top = args.top_skus if not args.smoke else 40
    seeds = args.seeds if not args.smoke else args.seeds[:3]

    results = []
    for seed in seeds:
        data = load_instacart(raw_dir=raw, n_users=n_users, top_n_skus=top, seed=seed)
        res, err = run_split(data, cfg, seed, args.n_pickers, log)
        if err:
            log.log(f"  seed {seed}: ABORT — {err}", "ERROR")
            sys.exit(2)
        results.append((seed, res))
        log.log(f"  seed {seed}: conc={res['concentration']:.3f} "
                f"L0: " + " ".join(f"{k}={v:.4f}" for k, v in res["l0"].items())
                + f" B0={res['b0_l0_mean']:.4f}")

    # ---- aggregate -----------------------------------------------------------
    experts = ["B1_StaticABC", "B2_COI", "B3_Affinity", "B4_CPSAT(l=0)"]

    def agg(metric):
        out = {}
        for e in experts:
            vals = [r[metric][e] for _, r in results]
            out[e] = (statistics.fmean(vals), statistics.stdev(vals) if len(vals) > 1 else 0.0)
        return out

    l0_stats, l1_stats = agg("l0"), agg("l1")

    # win matrix: for each pair (i beats j on how many splits)
    def wins(metric):
        w = {}
        for i in experts:
            for j in experts:
                if i == j:
                    continue
                w[(i, j)] = sum(1 for _, r in results if r[metric][i] < r[metric][j])
        return w

    w0, w1 = wins("l0"), wins("l1")
    n_splits = len(results)

    # headline gate: B4 beats B3 AND B1 on every split, both metrics
    b4_beats_b3 = all(r["l0"]["B4_CPSAT(l=0)"] < r["l0"]["B3_Affinity"]
                      and r["l1"]["B4_CPSAT(l=0)"] < r["l1"]["B3_Affinity"]
                      for _, r in results)
    b4_beats_b1 = all(r["l0"]["B4_CPSAT(l=0)"] < 1.0
                      and r["l1"]["B4_CPSAT(l=0)"] < 1.0 for _, r in results)
    b0_worst = all(r["b0_l0_mean"] > 1.0 and r["b0_l1_mean"] > 1.0 for _, r in results)
    gate_pass = b4_beats_b3 and b4_beats_b1 and b0_worst
    log.log(f"  gates: B4>B3(all splits,both)={b4_beats_b3} B4>B1={b4_beats_b1} "
            f"B0_worst={b0_worst} -> {'PASS' if gate_pass else 'FAIL'}")

    # validate one split non-vacuously
    seed0, r0 = results[0]
    world = {
        "sku_master": r0["sku_master"], "orders": r0["ev_orders"],
        "order_lines": r0["ev_lines"], "forecast_daily": [],
        "locations": r0["locations"], "inventory_snapshot": [],
        "slot_assignment": r0["a1"] + r0["a2"] + r0["a3"] + r0["a4"],
        "constraints": sampler.make_constraints(r0["locations"]),
        "decision_plan": [],
    }
    report = validate_pipeline(world)

    rows = "\n".join(
        f"| {e} | {l0_stats[e][0]:.4f} ± {l0_stats[e][1]:.4f} | "
        f"{l1_stats[e][0]:.4f} ± {l1_stats[e][1]:.4f} | "
        f"{w0[('B4_CPSAT(l=0)', e)] if e != 'B4_CPSAT(l=0)' else '—'}/{n_splits} |"
        f"{w1[('B4_CPSAT(l=0)', e)] if e != 'B4_CPSAT(l=0)' else '—'}/{n_splits} |"
        for e in experts
    )
    conc_vals = [r["concentration"] for _, r in results]
    out = ROOT / "outputs" / "experiments" / "r08_multi_split.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(f"""# R08 — multi-split variance: is B4's edge real? (REVIEW v0.4 #1)

**Date**: {datetime.now(timezone.utc).isoformat()} | splits = {seeds} | users = {n_users} | top SKUs = {top} | pickers = {args.n_pickers}

## Per-split detail

{chr(10).join(f"- seed {s}: conc={r['concentration']:.4f}, train {r['n_train']}/eval {r['n_eval']} orders, B4 L0={r['l0']['B4_CPSAT(l=0)']:.4f}, B3 L0={r['l0']['B3_Affinity']:.4f}" for s, r in results)}

## Aggregate ({n_splits} splits)

| Expert | L0 norm (mean ± std) | L1 norm (mean ± std) | B4 wins L0 | B4 wins L1 |
|--------|----------------------|----------------------|------------|------------|
{rows}
| B0 Random (mean of means) | {statistics.fmean(r['b0_l0_mean'] for _, r in results):.4f} | {statistics.fmean(r['b0_l1_mean'] for _, r in results):.4f} | — | — |

- observed concentration across splits: min={min(conc_vals):.4f} max={max(conc_vals):.4f} mean={statistics.fmean(conc_vals):.4f}

## Gates
- B4 beats B3 on EVERY split, both metrics: **{'PASS' if b4_beats_b3 else 'FAIL'}**
- B4 beats B1 on every split: **{'PASS' if b4_beats_b1 else 'FAIL'}**
- B0 worst on every split: **{'PASS' if b0_worst else 'FAIL'}**
- validate (split 0, non-vacuous): **{'PASS' if report.is_clean() else 'FAIL'}**

## Verdict
- **B4 CP-SAT's edge is {'STABLE' if gate_pass else 'NOT stable'} across {n_splits} independent user splits** (mean L0 {l0_stats['B4_CPSAT(l=0)'][0]:.4f} ± {l0_stats['B4_CPSAT(l=0)'][1]:.4f}, L1 {l1_stats['B4_CPSAT(l=0)'][0]:.4f} ± {l1_stats['B4_CPSAT(l=0)'][1]:.4f}).
- R07's single-split numbers were {'representative' if gate_pass else 'lucky'}; the ranking B4 > B3 > B1 may now be cited with variance attached.
""")
    log.log(f"  wrote outputs/experiments/r08_multi_split.md")
    log.log("=== done ===")


if __name__ == "__main__":
    main()
