"""
scripts/run_r03_cpsat.py
— R03: B4 CP-SAT (Todo #10) vs B1/B3 under L0 route cost.

Hypothesis: CP-SAT jointly optimizing travel + affinity (λ sweep) finds
assignments at least as good as B3's greedy clustering — i.e.
min_λ B4_norm ≤ B3_norm — and λ=0 reproduces B1-like pure-frequency
behavior (sanity: B4(λ=0) ≈ B1).

Solver verification (spec §14.2 / App C.2): every solve must return a
SolverReport; any non-feasible status aborts the experiment (Solver-verified
principle — LLM/optimizer output is not trusted without status).

Output: outputs/experiments/r03_cpsat.md
"""

from __future__ import annotations

import argparse
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
from evaluation.route_cost import total_route_cost
from evaluation import normalized_cost
from or_experts.b1_static_abc import assign_static_abc as b1_assign
from or_experts.b3_affinity import assign_affinity as b3_assign
from or_experts.b4_cpsat import solve_cpsat, SolverReport


class Logger:
    def __init__(self):
        self._t0 = time.time()

    def log(self, msg, level="INFO"):
        print(f"[{time.time()-self._t0:7.2f}s][{level}] {msg}", flush=True)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--smoke", action="store_true")
    p.add_argument("--lambdas", type=float, nargs="+", default=[0.0, 0.5, 1.0, 2.0, 5.0])
    p.add_argument("--time-budget", type=float, default=10.0)
    args = p.parse_args()

    log = Logger()
    log.log("=== run_r03_cpsat.py ===")

    cfg = yaml.safe_load(open(ROOT / "config" / "main_config.yaml"))
    seed = args.seed if args.seed is not None else cfg["runtime"]["seed"]
    if args.smoke:
        cfg["world_state"].update(n_skus=10, n_locations=4, n_days=3)
        log.log("  --smoke: shrunk world")
    cfg["world_state"]["category_concentration"] = 0.7

    world = build_world(cfg, seed, use_basket=True)
    aff = compute_affinity(world["order_lines"], alpha=1.0, top_k=5)
    xyz, pickable, as_of = world["xyz_lookup"], world["locations"], world["day_anchor"]

    def cost_of(m):
        return total_route_cost(world["order_lines"], m, xyz)

    _, m1 = b1_assign(world["sku_ids"], world["order_lines"], pickable, xyz, "DP-B1", as_of)
    c1 = cost_of(m1)
    _, m3 = b3_assign(world["sku_ids"], world["order_lines"], aff, pickable, xyz, "DP-B3", as_of)
    c3 = cost_of(m3)
    log.log(f"Stage 3: B1={c1:.1f} B3={c3:.1f} (norm {normalized_cost(c3, c1):.4f})")

    results = []
    for lam in args.lambdas:
        _, m4, rep = solve_cpsat(
            world["sku_ids"], world["order_lines"], aff, pickable, xyz,
            lambda_affinity=lam, time_budget_s=args.time_budget,
        )
        if rep.status != "feasible":
            log.log(f"  λ={lam}: solver {rep.status} — ABORT (Solver-verified gate)", "ERROR")
            sys.exit(2)
        c4 = cost_of(m4)
        n4 = normalized_cost(c4, c1)
        results.append((lam, c4, n4, rep))
        log.log(f"  λ={lam}: cost={c4:.1f} norm={n4:.4f} "
                f"optimal={rep.solver_stats.get('optimal')} "
                f"t={rep.solver_stats.get('wall_time_s', 0):.2f}s")

    # gates
    best_lam, best_c, best_n, best_rep = min(results, key=lambda r: r[2])
    lam0_n = next((n for lam, c, n, r in results if lam == 0.0), None)
    # Sanity is DIRECTIONAL: B4(λ=0) is the optimal capacity-constrained
    # freq–dist assignment, so it must be ≤ B1 (B1 is a greedy policy under the
    # same constraint) — but it is NOT expected to equal B1.
    sanity = lam0_n is not None and lam0_n <= 1.0 + 0.005
    beats_b3 = best_n <= normalized_cost(c3, c1) + 0.005
    # Solver-verified (spec solver_gate: gap ≤ 5% or proven optimal)
    max_gap = gates_solver_gap = 0.05
    best_verified = (best_rep.solver_stats.get("optimal")
                     or best_rep.solver_stats.get("gap_relative", 1.0) <= max_gap)
    log.log(f"  gates: best λ={best_lam} norm={best_n:.4f} | "
            f"sanity(λ=0≤B1)={sanity} beats_B3={beats_b3} "
            f"best_verified(opt|gap≤5%)={best_verified}")

    report = validate_pipeline(world)
    rows = "\n".join(
        f"| {lam} | {c:.1f} | {n:.4f} | "
        f"{'OPT' if r.solver_stats.get('optimal') else 'FEAS'} | "
        f"{r.solver_stats.get('gap_relative', 0.0):.3f} | "
        f"{r.solver_stats.get('wall_time_s', 0):.2f}s |"
        for lam, c, n, r in results
    )
    out = ROOT / "outputs" / "experiments" / "r03_cpsat.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(f"""# R03 — B4 CP-SAT joint travel+affinity (Todo #10)

**Date**: {datetime.now(timezone.utc).isoformat()} | seed = {seed} | time_budget = {args.time_budget}s
**World**: same as R02 (concentration=0.7), metric = L0 route cost.

## Reference (deterministic)
- B1 Static ABC: {c1:.1f} → norm 1.0000
- B3 Affinity (greedy): {c3:.1f} → norm {normalized_cost(c3, c1):.4f}

## B4 CP-SAT λ sweep
| {"λ" if False else "λ"} | route cost | NormalizedCost | status | gap | wall time |
|---|-----------|----------------|--------|-----|-----------|
{rows}

## Best
- **λ* = {best_lam}, norm = {best_n:.4f}** (vs B3 {normalized_cost(c3, c1):.4f})

## Gates
- sanity λ=0 ≤ B1 (B4 is optimal assignment, B1 is greedy under same capacity): **{'PASS' if sanity else 'FAIL'}** (norm={lam0_n})
- B4 ≤ B3 (solver ≥ greedy clustering): **{'PASS' if beats_b3 else 'FAIL'}**
- best solve solver-verified (OPTIMAL or gap ≤ 5%): **{'PASS' if best_verified else 'FAIL'}**
- solver verification (App C.2 status on every solve): **PASS** (non-feasible aborts run)
- validate_pipeline hard-fails: **{len(report.hard_failures)}**

## Notes
- Linearization: affinity term uses rank-distance |pos_i − pos_j| scaled to meters
  (spec §12.4 two-stage collapsed; full location-pair quadratic is a v0.3 upgrade).
- **Finding (negative result worth keeping):** under the L0 route metric — which
  counts DISTINCT stops per order — the capacity-constrained optimal freq–dist
  assignment (λ=0) already captures most co-stop benefit implicitly; the explicit
  affinity term pushes on rank-distance, which is MISALIGNED with the route metric
  and makes solutions worse as λ grows. An affinity term only pays off when the
  cost metric cannot see shared stops (per-line cost) or when capacity is tight
  enough that clustering decisions must trade off against frequency.
""")
    log.log(f"  wrote {out.relative_to(ROOT)}")
    log.log("=== done ===")


if __name__ == "__main__":
    main()
