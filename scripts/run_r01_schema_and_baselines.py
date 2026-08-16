"""
scripts/run_r01_schema_and_baselines.py
— v0.1 minimum viable run.

Mirrors the 5-stage `cultivating-ml-agent` pipeline structure:

  Stage 0: Configuration  (load YAML, set seed, get logger)
  Stage 1: Data Loading   (synthetic World State, validate_pipeline)
  Stage 2: Feature Eng    (skipped — Todo #7/#8 live here in v0.2)
  Stage 3: Model Training (B0 Random + B1 Static ABC)
  Stage 4: Predict+Submit (NormalizedCost + evaluation_gate + write experiment log)

Output: outputs/experiments/r01_schema_and_baselines.md
"""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any

import numpy as np
import yaml

# Make src-layout resolve when called from repo root
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from world_state import (
    SkuMaster, Order, OrderLine, ForecastDaily,
    Location, InventorySnapshot, SlotAssignment, Constraint,
    DecisionPlan,
    SourceType, StorageClass, ZoneType,
    validate_pipeline, ValidationError,
)
from world_state import sample as sampler

from or_experts.b0_random import (
    assign_random as b0_assign,
    replay_total_pick_distance as b0_replay,
    build_decision_plan as b0_plan,
)
from or_experts.b1_static_abc import (
    assign_static_abc as b1_assign,
    total_pick_distance as b1_replay,
    build_decision_plan as b1_plan,
)
from or_experts.b2_coi import (
    assign_coi as b2_assign,
    build_decision_plan as b2_plan,
)
from evaluation import compute_components, apply_weights, normalized_cost


# -------------------------------------------------------------------------
# Tiny logger (stdout-only; MLflow is overkill for v0.1)
# -------------------------------------------------------------------------

class Logger:
    def __init__(self, level: str = "INFO"):
        self.level = level
        self._t0 = time.time()

    def log(self, msg: str, level: str = "INFO"):
        ts = time.time() - self._t0
        print(f"[{ts:7.2f}s][{level}] {msg}", flush=True)


# -------------------------------------------------------------------------
# Stage 0 — Configuration
# -------------------------------------------------------------------------

def stage0_config(args, log: Logger):
    log.log("Stage 0: Configuration")
    with open(ROOT / "config" / "main_config.yaml") as f:
        cfg = yaml.safe_load(f)
    with open(ROOT / "config" / "cost_weights.yaml") as f:
        weights = yaml.safe_load(f)["weights"]
    with open(ROOT / "config" / "verify_gate.yaml") as f:
        gates = yaml.safe_load(f)["gates"]

    # CLI overrides
    seed = args.seed if args.seed is not None else cfg["runtime"]["seed"]
    log.log(f"  seed={seed} cfg.project={cfg['project']['name']} v{cfg['project']['version']}")
    return {
        "cfg": cfg, "weights": weights, "gates": gates,
        "seed": seed,
    }


# -------------------------------------------------------------------------
# Stage 1 — Data Loading
# -------------------------------------------------------------------------

def stage1_world_state(cfg: Dict, seed: int, log: Logger):
    log.log("Stage 1: Data Loading (synthetic)")
    rng = random.Random(seed)
    np_rng = np.random.default_rng(seed)

    n_skus = cfg["world_state"]["n_skus"]
    n_locations = cfg["world_state"]["n_locations"]
    n_days = cfg["world_state"]["n_days"]
    o_mean = cfg["world_state"]["orders_per_day_mean"]
    o_std = cfg["world_state"]["orders_per_day_std"]

    sku_master = sampler.make_sku_master(n_skus, rng)
    log.log(f"  sku_master rows = {len(sku_master)}")
    locations, xyz_lookup = sampler.make_locations(n_locations, rng)
    log.log(f"  locations rows = {len(locations)} (xyz_lookup has {len(xyz_lookup)})")
    sku_ids = [s.sku_id for s in sku_master]

    day_anchor = datetime(2025, 1, 1, tzinfo=timezone.utc)
    orders, order_lines = sampler.make_orders(
        sku_ids=sku_ids,
        location_xyz=xyz_lookup,
        n_days=n_days,
        orders_per_day_mean=o_mean,
        orders_per_day_std=o_std,
        day_anchor=day_anchor,
        rng=rng,
    )
    log.log(f"  orders={len(orders)} order_lines={len(order_lines)}")

    forecast = sampler.make_forecast_daily(sku_ids, orders, order_lines, n_days, day_anchor)
    log.log(f"  forecast_daily rows = {len(forecast)}")

    inv = sampler.make_inventory_snapshot(sku_ids, locations, day_anchor, rng)
    log.log(f"  inventory_snapshot rows = {len(inv)}")

    constraints = sampler.make_constraints(locations)
    log.log(f"  constraints rows = {len(constraints)}")

    # slot_assignment + decision_plan start empty
    return {
        "sku_master": sku_master,
        "orders": orders,
        "order_lines": order_lines,
        "forecast_daily": forecast,
        "locations": locations,
        "inventory_snapshot": inv,
        "slot_assignment": [],
        "constraints": constraints,
        "decision_plan": [],
        "xyz_lookup": xyz_lookup,
        "sku_ids": sku_ids,
        "day_anchor": day_anchor,
        "_rng": rng,
        "_np_rng": np_rng,
    }


# -------------------------------------------------------------------------
# Stage 2 — Feature Engineering (skipped, see Todo #7/#8)
# -------------------------------------------------------------------------

def stage2_features(log: Logger):
    log.log("Stage 2: Feature Engineering (skipped — Todo #7/#8 in v0.2)")


# -------------------------------------------------------------------------
# Stage 3 — OR Experts (B0 Random + B1 Static ABC)
# -------------------------------------------------------------------------

def stage3_experts(world: Dict, weights: Dict, gates: Dict, log: Logger):
    log.log("Stage 3: OR Experts (B0, B1, B2)")
    pickable = [loc for loc in world["locations"] if loc.pickable]
    rng = world["_rng"]
    as_of = world["day_anchor"]

    # ---- B1 (run first, deterministic) -----------------------------------
    b1_assignments, sku_to_loc_b1 = b1_assign(
        sku_ids=world["sku_ids"],
        order_lines=world["order_lines"],
        pickable_locations=pickable,
        xyz_lookup=world["xyz_lookup"],
        decision_id="DP-B1-RUN",
        as_of=as_of,
    )
    cost_b1_components = compute_components(
        world["order_lines"], sku_to_loc_b1, world["xyz_lookup"]
    )
    cost_b1 = apply_weights(cost_b1_components, weights)
    plan_b1 = b1_plan(b1_assignments, expected_cost=cost_b1, baseline_cost=cost_b1)
    log.log(f"  B1 total pick cost = {cost_b1:.3f}")

    # Reproducibility gate: 5 seeds rerun
    rep_scores = []
    for s in range(gates["reproducibility_gate"]["config"]["threshold_seed_count"]):
        # B1 is deterministic, but verify:
        _, sku2 = b1_assign(
            sku_ids=world["sku_ids"],
            order_lines=world["order_lines"],
            pickable_locations=pickable,
            xyz_lookup=world["xyz_lookup"],
            decision_id=f"DP-B1-RUN-{s}",
            as_of=as_of,
        )
        c = apply_weights(
            compute_components(world["order_lines"], sku2, world["xyz_lookup"]),
            weights,
        )
        rep_scores.append(c)
    rep_max_rel = max(abs(x - cost_b1) / cost_b1 for x in rep_scores)
    log.log(f"  B1 reproducibility: max_rel_dev = {rep_max_rel:.6f}")

    # ---- B0 (random; 5 seeds for variance) -------------------------------
    b0_seed_count = gates["metric_gate"]["config"]["threshold_seed_count"]
    b0_costs = []
    b0_plans = []
    b0_assignments_list = []
    for s in range(b0_seed_count):
        rng_s = random.Random(world["_rng"].random() + s)  # propagate but advance
        # NOTE: reassign each SKU takes randomness state; rng is consumed in-place
        #       but we reinit it each loop for fair per-seed resets.
        asgns, sku_to_loc = b0_assign(
            sku_ids=world["sku_ids"],
            pickable_locations=pickable,
            xyz_lookup=world["xyz_lookup"],
            decision_id=f"DP-B0-RUN-{s}",
            as_of=as_of,
            rng=rng_s,
        )
        cost = apply_weights(
            compute_components(world["order_lines"], sku_to_loc, world["xyz_lookup"]),
            weights,
        )
        b0_costs.append(cost)
        b0_assignments_list.append(asgns)
        b0_plans.append(b0_plan(asgns, expected_cost=cost, baseline_cost=cost_b1))

    b0_mean = sum(b0_costs) / len(b0_costs)
    b0_std = (sum((x - b0_mean) ** 2 for x in b0_costs) / len(b0_costs)) ** 0.5
    b0_norm = normalized_cost(b0_mean, cost_b1)
    log.log(f"  B0 mean cost = {b0_mean:.3f} ± {b0_std:.3f}")
    log.log(f"  B0 NormalizedCost (vs B1) = {b0_norm:.4f}")

    # Metric gate check
    # v0.1 uses win-rate logic: B0 (random) must lose to B1 (structural) on EVERY
    # seed — std/mean is the wrong statistic for a uniformly-random policy whose
    # seed-to-seed variance is intrinsic, not an estimation artifact.
    metric_cfg = gates["metric_gate"]["config"]
    win_rate = sum(1 for c in b0_costs if c > cost_b1) / len(b0_costs)
    gate_pass = (
        abs(b0_norm - 1.0) > metric_cfg["threshold_relative_improvement"]
        and win_rate >= metric_cfg.get("threshold_win_rate", 1.0)
    )
    log.log(f"  metric_gate: |B0_norm - 1| = {abs(b0_norm - 1.0):.4f} "
            f"> {metric_cfg['threshold_relative_improvement']}, "
            f"win_rate(B0 worse than B1) = {win_rate:.2f} "
            f">= {metric_cfg.get('threshold_win_rate', 1.0)} -> "
            f"{'PASS' if gate_pass else 'FAIL'}")

    # ---- B2 (COI, deterministic) -----------------------------------------
    b2_assignments, sku_to_loc_b2 = b2_assign(
        sku_master=world["sku_master"],
        order_lines=world["order_lines"],
        pickable_locations=pickable,
        xyz_lookup=world["xyz_lookup"],
        decision_id="DP-B2-RUN",
        as_of=as_of,
    )
    cost_b2 = apply_weights(
        compute_components(world["order_lines"], sku_to_loc_b2, world["xyz_lookup"]),
        weights,
    )
    plan_b2 = b2_plan(b2_assignments, expected_cost=cost_b2, baseline_cost=cost_b1)
    b2_norm = normalized_cost(cost_b2, cost_b1)
    log.log(f"  B2 COI total pick cost = {cost_b2:.3f} (NormalizedCost = {b2_norm:.4f})")

    # Persist plans back into the world state (flatten list-of-lists)
    all_assignments = list(b1_assignments) + list(b2_assignments)
    for batch in b0_assignments_list:
        all_assignments.extend(batch)
    world["slot_assignment"] = all_assignments
    world["decision_plan"] = [plan_b1, plan_b2] + b0_plans

    return {
        "b1_cost": cost_b1,
        "b1_components": cost_b1_components.to_dict(),
        "b2_cost": cost_b2,
        "b2_norm": b2_norm,
        "b0_costs": b0_costs,
        "b0_mean": b0_mean,
        "b0_std": b0_std,
        "b0_norm": b0_norm,
        "b1_norm": 1.0,
        "rep_max_rel": rep_max_rel,
        "gate_pass": gate_pass,
        "win_rate": win_rate,
        "b1_plan": plan_b1,
    }


# -------------------------------------------------------------------------
# Stage 4 — Predict + Submit (validate + metric gate + write report)
# -------------------------------------------------------------------------

def stage4_predict_submit(world: Dict, gates: Dict, expert_results: Dict, log: Logger):
    log.log("Stage 4: Predict + Submit")
    # Validate the full pipeline (now includes decision_plan)
    try:
        report = validate_pipeline(world)
        log.log(f"  validate_pipeline: {report.summary()}")
        log.log(f"  hard-fails={len(report.hard_failures)} warnings={len(report.soft_warnings)}")
    except ValidationError as e:
        log.log(f"  VALIDATION HARD-FAIL: {e}", "ERROR")
        raise

    # evaluation_gate: classic metric_gate + reproducibility_gate already evaluated
    rep_thr = gates["reproducibility_gate"]["config"].get("b1_within_pct", 0.01)
    if expert_results["rep_max_rel"] > rep_thr:
        log.log(f"  reproducibility_gate FAIL: rel_dev {expert_results['rep_max_rel']:.6f} > {rep_thr}", "ERROR")
        sys.exit(2)

    if not expert_results["gate_pass"]:
        log.log("  metric_gate FAIL — but for v0.1 we LOG only, not abort")
        # spec §16.4 stress test inherits this; in v0.2 we'd `evaluation_gate()` block

    return report


# -------------------------------------------------------------------------
# Report writer
# -------------------------------------------------------------------------

def write_report(cfg, gates, report, expert_results, log: Logger):
    out_dir = ROOT / "outputs" / "experiments"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "r01_schema_and_baselines.md"

    metric_cfg = gates["metric_gate"]["config"]
    rep_cfg = gates["reproducibility_gate"]["config"]

    md = f"""# R01 — schema + baselines (B0 Random, B1 Static ABC)

**Date**: {datetime.now(timezone.utc).isoformat()}
**Seed**: {cfg["runtime"]["seed"]}
**Spec**: {cfg["project"]["spec_ref"]}

## Stage 0 — Configuration
- `main_config.yaml`: project `{cfg["project"]["name"]}` v{cfg["project"]["version"]}
- World State size: SKUs = {cfg["world_state"]["n_skus"]}, locations = {cfg["world_state"]["n_locations"]}, days = {cfg["world_state"]["n_days"]}
- Cost weights: α=1.0, β..ζ=0.0 (v0.1 pick-only)

## Stage 1 — Data Loading (synthetic)
- 9 canonical tables present: {sorted(report.tables_seen)}
- Records: {report.record_counts}
- hard-fails = {len(report.hard_failures)}, soft warnings = {len(report.soft_warnings)}

## Stage 2 — Feature Engineering
- Skipped. **Todo #7 (Affinity)** and **#8 (Travel-time Calibration)** live here in v0.2.

## Stage 3 — OR Experts (B0, B1, B2)

| Expert | Total cost (± std over {metric_cfg['threshold_seed_count']} seeds) | NormalizedCost vs B1 |
|--------|---------------|-------------------|
| **B1 Static ABC** | **{expert_results["b1_cost"]:.3f}** | **1.0000** |
| B2 COI            | {expert_results["b2_cost"]:.3f} | {expert_results['b2_norm']:.4f} |
| B0 Random         | {expert_results["b0_mean"]:.3f} ± {expert_results['b0_std']:.3f} | {expert_results['b0_norm']:.4f} |

- Per-seed B0 costs: {[round(x,3) for x in expert_results['b0_costs']]}
- B1 is the deterministic anchor.
- B0 should be **worse** than B1; metric_gate asserts `|B0_norm - 1| > {metric_cfg['threshold_relative_improvement']}` and win_rate `>= {metric_cfg.get('threshold_win_rate', 1.0)}`.
- win_rate(B0 worse than B1) = **{expert_results['win_rate']:.2f}** across {metric_cfg['threshold_seed_count']} seeds (per-seed comparison; std/mean is not used — see gate docstring).

### Reproducibility gate (B1 across {rep_cfg['threshold_seed_count']} reruns)
- max relative deviation = **{expert_results['rep_max_rel']:.6f}** (B1 is fully deterministic ⇒ expected ≈ 0)

## Stage 4 — Predict + Submit
- `validate_pipeline`: hard-fails = **{len(report.hard_failures)}**
- metric_gate verdict: **{'PASS' if expert_results['gate_pass'] else 'FAIL'}**
- `evaluation_gate()` would block on FAIL; v0.1 logs the verdict.

## Open TODOs (next milestones)
- Todo #5/#6 (real data)
- Todo #7 (Affinity Score)
- Todo #8 (Warehouse graph + travel-time calibration)
- Todo #10 (CP-SAT Dynamic Slotting)
- Todo #11 (SimPy L1 replay → enables `pick_distance_total` replacement)
- Todo #12 (Execution Gateway stub)

"""
    path.write_text(md)
    log.log(f"  wrote {path.relative_to(ROOT)}")


# -------------------------------------------------------------------------
# Entry
# -------------------------------------------------------------------------

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--smoke", action="store_true",
                   help="override config with small sizes for a sub-second smoke test")
    args = p.parse_args()

    log = Logger()
    log.log("=== run_r01_schema_and_baselines.py ===")

    cfg_bundle = stage0_config(args, log)
    cfg = cfg_bundle["cfg"]
    if args.smoke:
        cfg["world_state"]["n_skus"] = 8
        cfg["world_state"]["n_locations"] = 4
        cfg["world_state"]["n_days"] = 3
        log.log("  --smoke: shrunk world state (8 SKUs, 4 locs, 3 days)")

    world = stage1_world_state(cfg, cfg_bundle["seed"], log)
    stage2_features(log)
    expert_results = stage3_experts(world, cfg_bundle["weights"], cfg_bundle["gates"], log)
    report = stage4_predict_submit(world, cfg_bundle["gates"], expert_results, log)
    write_report(cfg, cfg_bundle["gates"], report, expert_results, log)
    log.log("=== done ===")


if __name__ == "__main__":
    main()
