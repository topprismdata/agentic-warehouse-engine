"""
scripts/run_r06_gateway.py
— R06: Execution Gateway stub (Todo #12) — the §15.4 boundary, dry-run only.

Plan: take R05's honest protocol, produce a REAL B4 DecisionPlan, and try to
push it (plus 7 adversarial forgeries) through the gateway. Every rejection
path must fire with the right reason code; the good plan must pass clean.

Test matrix (spec anchors §14.2 / §15.2 / §15.4 / §3.3):
  T1 good B4 plan (ASSIGN)            -> accepted, mode=auto, risk=low
  T2 verifier_status=infeasible       -> SOLVER_STATUS_NOT_FEASIBLE
  T3 stale constraint_version         -> CONSTRAINT_VERSION_MISMATCH
  T4 capacity-violating actions       -> CAPACITY_VIOLATION
  T5 safety_critical plan             -> SAFETY_CRITICAL_BLOCKED_FOR_LLM
  T6 MOVE with saving ≤ move cost     -> NEGATIVE_PAYBACK
  T7 large plan (>5 actions)          -> risk=HIGH, mode=approve_required

Output: outputs/experiments/r06_gateway.md
"""

from __future__ import annotations

import argparse
import sys
import time
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from world_state.loader import build_world
from world_state import validate_pipeline
from world_state.schemas import DecisionPlan, ProblemType, RiskClass, SourceType
from features.affinity import compute_affinity
from evaluation.route_cost import total_route_cost
from execution.gateway import (
    ExecutionGateway, GatewayConfig,
    R_SOLVER_STATUS, R_CONSTRAINT_VERSION, R_CAPACITY,
    R_RISK_SAFETY, R_PAYBACK,
)
from or_experts.b1_static_abc import assign_static_abc as b1_assign
from or_experts.b4_cpsat import solve_cpsat


class Logger:
    def __init__(self):
        self._t0 = time.time()

    def log(self, msg, level="INFO"):
        print(f"[{time.time()-self._t0:7.2f}s][{level}] {msg}", flush=True)


def gateway_actions_from(assignments, xyz, action_type="ASSIGN") -> list:
    """Adapter: SlotAssignment rows -> gateway action dicts (sku_id /
    to_location / expected_saving provenance chain)."""
    return [
        {
            "sku_id": a.sku_id,
            "to_location": a.location_id,
            "from_location": None if action_type == "ASSIGN" else a.location_id,
            "action_type": action_type,
            "expected_saving": 0.0,      # initial slotting: value flows via L0/L1 norms
            "move_cost": 0.0,
            "reason": a.reason,
        }
        for a in assignments
    ]


def forge(base: DecisionPlan, **over) -> DecisionPlan:
    """Copy a plan and override fields for adversarial tests."""
    p = deepcopy(base)
    for k, val in over.items():
        setattr(p, k, val)
    return p


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--smoke", action="store_true")
    args = p.parse_args()

    log = Logger()
    log.log("=== run_r06_gateway.py ===")

    cfg = yaml.safe_load(open(ROOT / "config" / "main_config.yaml"))
    seed = args.seed if args.seed is not None else cfg["runtime"]["seed"]
    if args.smoke:
        cfg["world_state"].update(n_skus=20, n_locations=10, n_days=4)
        log.log("  --smoke: shrunk world")
    cfg["world_state"]["category_concentration"] = 0.7

    # ---- build a REAL B4 plan under the R05 honest protocol ------------------
    world = build_world(cfg, seed, use_basket=True)
    xyz, pickable, as_of = world["xyz_lookup"], world["locations"], world["day_anchor"]
    orders, lines = world["orders"], world["order_lines"]
    split_day = cfg["world_state"]["n_days"] // 2
    hist_ids = {o.order_id for o in orders if (o.order_time - as_of).days < split_day}
    hist_lines = [ln for ln in lines if ln.order_id in hist_ids]

    aff = compute_affinity(hist_lines)
    a4, m4, rep4 = solve_cpsat(world["sku_ids"], hist_lines, aff, pickable, xyz,
                               lambda_affinity=0.0, time_budget_s=10.0)
    _, m1 = b1_assign(world["sku_ids"], hist_lines, pickable, xyz, "DP-B1", as_of)
    c4 = total_route_cost(lines, m4, xyz)
    c1 = total_route_cost(lines, m1, xyz)
    live_rules = {c.rule_version for c in world["constraints"]}
    live_version = sorted(live_rules)[-1]

    good_plan = DecisionPlan(
        decision_id="DP-B4-R06",
        problem_type=ProblemType.DYNAMIC_SLOTTING,
        horizon_start=as_of, horizon_end=as_of,
        actions=gateway_actions_from(a4, xyz),
        expected_cost=c4, baseline_cost=c1, confidence=0.9,
        verifier_status=rep4.status,
        approval_status="auto", risk_class=RiskClass.LOW,
        model_version="B4_CPSAT@v0.3", constraint_version=live_version,
        lineage=SourceType.DERIVED, source_type=SourceType.DERIVED,
    )
    log.log(f"Stage 1: B4 plan built — {len(good_plan.actions)} actions, "
            f"verifier={rep4.status}, live constraint_version={live_version}")

    gw = ExecutionGateway(GatewayConfig(
        # capacity is a WORLD property (ceil(n_sku_total/n_loc)), never inferred
        # from the plan's action subset — T1 caught this: a 5-action subset
        # self-derived cap=1 and flagged legal co-locations as violations
        location_capacity=max(1, -(-len(world["sku_ids"]) // len(pickable))),
    ))

    # ---- test matrix ----------------------------------------------------------
    log.log("Stage 2: test matrix")
    results = []

    # T1 good SMALL plan (≤5 actions) -> low risk, auto — the §15.2 low lane
    small = deepcopy(good_plan)
    small.decision_id = "DP-SMALL-GOOD"
    small.actions = small.actions[:5]
    v1 = gw.dry_run(small, live_version, len(pickable))
    results.append(("T1 good plan ≤5 acts → auto", v1,
                    v1.ok and all(t.execution_mode == "auto"
                                  and t.risk_class == RiskClass.LOW
                                  for t in v1.accepted)))

    # T2 unverified solver status
    v2 = gw.dry_run(forge(good_plan, verifier_status="timeout"), live_version, len(pickable))
    results.append(("T2 verifier_status=timeout", v2,
                    v2.rejected and v2.rejected[0]["code"] == R_SOLVER_STATUS))

    # T3 stale constraint version
    v3 = gw.dry_run(forge(good_plan, constraint_version="v0.0.1"), live_version, len(pickable))
    results.append(("T3 stale constraint_version", v3,
                    v3.rejected and v3.rejected[0]["code"] == R_CONSTRAINT_VERSION))

    # T4 capacity violation (all SKUs to one location)
    bad = deepcopy(good_plan)
    bad.decision_id = "DP-BAD-CAP"
    for a in bad.actions:
        a["to_location"] = pickable[0].location_id
    v4 = gw.dry_run(bad, live_version, len(pickable))
    results.append(("T4 capacity violation", v4,
                    v4.rejected and v4.rejected[0]["code"] == R_CAPACITY))

    # T5 safety critical
    v5 = gw.dry_run(forge(good_plan, risk_class=RiskClass.SAFETY_CRITICAL,
                          decision_id="DP-SAFETY"), live_version, len(pickable))
    results.append(("T5 safety_critical plan", v5,
                    v5.rejected and v5.rejected[0]["code"] == R_RISK_SAFETY))

    # T6 negative payback MOVE (distinct locations so capacity check can't
    # preempt the payback check — check order is capacity → payback)
    mv = deepcopy(good_plan)
    mv.decision_id = "DP-MOVE-BAD"
    distinct = []
    seen_locs = set()
    for a in mv.actions:
        if a["to_location"] not in seen_locs:
            distinct.append(a)
            seen_locs.add(a["to_location"])
        if len(distinct) == 3:
            break
    mv.actions = distinct
    for a in mv.actions:
        a["action_type"] = "MOVE"
        a["expected_saving"] = 1.0
        a["move_cost"] = 6.5          # saving < cost (spec 3.3)
    v6 = gw.dry_run(mv, live_version, len(pickable))
    results.append(("T6 MOVE saving<cost", v6,
                    v6.rejected and all(r["code"] == R_PAYBACK for r in v6.rejected)))

    # T7 large plan -> high risk, approval required
    big = forge(good_plan, decision_id="DP-BIG")
    v7 = gw.dry_run(big, live_version, len(pickable))
    # n_skus(120) > 5 -> HIGH risk, all tasks approve_required
    results.append(("T7 >5 actions => HIGH risk", v7,
                    v7.accepted and all(t.risk_class == RiskClass.HIGH
                                        and t.execution_mode == "approve_required"
                                        for t in v7.accepted)))

    # T8 medium lane: small plan explicitly flagged MEDIUM (spec 15.2 four
    # lanes — v0.3 review G2: this lane had ZERO coverage)
    med = deepcopy(small)
    med.decision_id = "DP-MEDIUM"
    v8 = gw.dry_run(forge(med, risk_class=RiskClass.MEDIUM), live_version, len(pickable))
    results.append(("T8 plan MEDIUM → approve", v8,
                    v8.accepted and all(t.risk_class == RiskClass.MEDIUM
                                        and t.execution_mode == "approve_required"
                                        for t in v8.accepted)))

    all_pass = all(ok for _, _, ok in results)
    for name, v, ok in results:
        log.log(f"  [{ 'PASS' if ok else 'FAIL' }] {name:28s} {v.summary()}")

    # ---- audit trail sample ----------------------------------------------------
    sample_audit = v1.accepted[0].audit_row() if v1.accepted else {}

    # ---- validate + report -----------------------------------------------------
    world["slot_assignment"] = a4
    world["decision_plan"] = [good_plan]
    report = validate_pipeline(world)

    rows = "\n".join(
        f"| {name} | {'PASS' if ok else 'FAIL'} | "
        f"{len(v.accepted)} / {len(v.rejected)} | "
        f"{dict(Counter(r['code'] for r in v.rejected)) or '—'} |"
        for name, v, ok in results
    )

    out = ROOT / "outputs" / "experiments" / "r06_gateway.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(f"""# R06 — Execution Gateway stub (Todo #12): the §15.4 boundary

**Date**: {datetime.now(timezone.utc).isoformat()} | seed = {seed} | dry-run only (no WMS, no writes)

## What the gateway enforces (check chain, fail-fast)

| # | Check | Spec anchor | Reason code |
|---|-------|-------------|-------------|
| 1 | plan is solver-verified | §14.2 | SOLVER_STATUS_NOT_FEASIBLE |
| 2 | constraint_version fresh | §15.4 | CONSTRAINT_VERSION_MISMATCH |
| 3 | location capacity (whole plan) | §10.4 | CAPACITY_VIOLATION |
| 4 | risk routing: low→auto, medium→approve, high→sim+human, safety→blocked | §15.2 | RISK_HIGH_REQUIRES_SIM_AND_APPROVAL / SAFETY_CRITICAL_BLOCKED_FOR_LLM |
| 5 | MOVE payback: saving > move_cost | §3.3 | NEGATIVE_PAYBACK |

## Test matrix results

| Test | Verdict | accepted/rejected | rejection codes |
|------|---------|-------------------|-----------------|
{rows}

All 8 verdicts correct: **{'PASS' if all_pass else 'FAIL'}**

## Audit trail sample (§15.4 mandated provenance per task)

```json
{sample_audit}
```

## Honest scope notes
- **dry_run only**: no WMS adapter, no task dispatch, no DB writes. The stub's job
  is the CONTRACT + rejection codes + audit row — execution plumbing is v0.4.
- expected_saving for initial ASSIGN is 0.0 by convention (value flows via L0/L1
  NormalizedCost, not per-action); per-action saving estimation belongs to the
  Learned Cost Model (spec §13.3), wired in v0.3+.
- The good B4 plan (120 ASSIGN actions) is deliberately routed HIGH risk by the
  >5-actions rule (spec §15.2 "large-scale re-slot needs approval") — correct
  behavior, not a bug: nothing here auto-executes at scale.
- validate_pipeline (non-vacuous, {len(a4)} assignments + 1 plan): hard-fails = **{len(report.hard_failures)}**
""")
    log.log(f"  wrote {out.relative_to(ROOT)}")
    log.log(f"  all 8 verdicts: {'PASS' if all_pass else 'FAIL'}")
    log.log("=== done ===")
    sys.exit(0 if all_pass else 2)


if __name__ == "__main__":
    main()
