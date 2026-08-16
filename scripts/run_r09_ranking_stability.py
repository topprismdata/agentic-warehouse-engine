"""
scripts/run_r09_ranking_stability.py
— R09: Go/No-Go experiment (spec update §10, dev-order Step 4).

THE question: does the best slotting expert CHANGE with the warehouse state?
  - Run ALL of E1..E7 on every state (regime × seed)
  - If one expert wins >= 95% of states -> NO-GO (selector research invalid)
  - If winners switch by regime in the predicted pattern -> GO

Protocol discipline (inherited from R05): experts see HISTORY window only;
evaluation on FUTURE window; capacity audit; non-vacuous validate; every
number mean over seeds. E4/E5/E6 use INFORMED forecast (promotions known —
spec §13.1); R5 injects noise into their input, not the stream.

Output: outputs/experiments/r09_ranking_stability.md
"""

from __future__ import annotations

import argparse
import random
import statistics
import sys
import time
from collections import Counter, defaultdict
import math
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from world_state import sample as sampler
from world_state import validate_pipeline, ValidationError
from world_state.regimes import REGIMES, RegimeSpec, regime_specs, make_regime_orders
from world_state.schemas import SourceType
from features.affinity import compute_affinity
from features.forecast import forecast_demand
from simulation.replay import replay, ReplayConfig
from evaluation.route_cost import total_route_cost
from evaluation.audit import count_capacity_violations
from evaluation import normalized_cost
from or_experts.b1_static_abc import assign_static_abc as e1
from or_experts.b2_coi import assign_coi as e2
from or_experts.b3_affinity import assign_affinity as e3
from or_experts.e4_e7 import (
    assign_e4_forecast_abc as e4,
    assign_e5_robust as e5,
    assign_e6_forecast_affinity as e6,
    assign_e7_rolling_lite as e7,
)

EXPERTS = ["E1_StaticABC", "E2_COI", "E3_Affinity",
           "E4_ForecastABC", "E5_Robust", "E6_FcAff", "E7_RollingLite"]


class Logger:
    def __init__(self):
        self._t0 = time.time()

    def log(self, msg, level="INFO"):
        print(f"[{time.time()-self._t0:7.2f}s][{level}] {msg}", flush=True)


def build_state(cfg, regime: RegimeSpec, seed: int, log: Logger):
    """One state: world + regime order stream, split hist/future."""
    ws = cfg["world_state"]
    rng = random.Random(seed)
    n_skus, n_loc = ws["n_skus"], ws["n_locations"]
    sku_master = sampler.make_sku_master(n_skus, rng)
    sku_ids = [s.sku_id for s in sku_master]
    sku_cat = {s.sku_id: s.category_id for s in sku_master}
    locations, xyz = sampler.make_locations(n_loc, rng)

    # R7: capacity shock — keep only a fraction of locations
    if regime.location_keep_frac < 1.0:
        keep = max(4, int(round(n_loc * regime.location_keep_frac)))
        rng.shuffle(locations)
        locations = sorted(locations[:keep], key=lambda l: (l.aisle, l.bay, l.level))
        log.log(f"    R7: {keep}/{n_loc} locations kept")

    anchor = datetime(2025, 1, 1, tzinfo=timezone.utc)
    n_hist = ws["n_days"] // 2
    n_fut = ws["n_days"] - n_hist
    orders, lines, promo = make_regime_orders(
        sku_ids, sku_cat, n_hist, n_fut, regime, rng, anchor,
        orders_per_day_mean=ws["orders_per_day_mean"],
        orders_per_day_std=ws["orders_per_day_std"])

    hist_ids = {o.order_id for o in orders if (o.order_time - anchor).days < n_hist}
    hist_orders = [o for o in orders if o.order_id in hist_ids]
    hist_lines = [l for l in lines if l.order_id in hist_ids]
    fut_orders = [o for o in orders if o.order_id not in hist_ids]
    fut_lines = [l for l in lines if l.order_id not in hist_ids]

    # forecasts (informed: promotions known; R5 per-SKU heterogeneous noise)
    line_day = {o.order_id: float((o.order_time - anchor).days) for o in hist_orders}
    fc = forecast_demand(sku_ids, hist_lines, future_days=n_fut, history_days=n_hist,
                         history_time_span_days=float(n_hist), line_day=line_day,
                         promotion=promo, noise_sigma=regime.forecast_noise,
                         seed=seed)
    return dict(sku_master=sku_master, sku_ids=sku_ids, sku_cat=sku_cat,
                locations=locations, xyz=xyz, anchor=anchor,
                hist_orders=hist_orders, hist_lines=hist_lines,
                fut_orders=fut_orders, fut_lines=fut_lines,
                fc=fc, promo=promo, regime=regime, n_hist=n_hist, n_fut=n_fut)


def run_experts(state, seed, log: Logger):
    sku_ids = state["sku_ids"]
    locs, xyz, as_of = state["locations"], state["xyz"], state["anchor"]
    hist, fc = state["hist_lines"], state["fc"]
    regime = state["regime"]

    # recency day index for forecast + dynamic affinity (order day from anchor)
    line_day = {o.order_id: float((o.order_time - state["anchor"]).days)
                for o in state["hist_orders"]}

    r1, m1 = e1(sku_ids, hist, locs, xyz, "DP-E1", as_of)
    r2, m2 = e2(state["sku_master"], hist, locs, xyz, "DP-E2", as_of)
    aff = compute_affinity(hist, line_day=line_day,
                           history_time_span_days=state["n_hist"])  # dynamic affinity (13.2)
    r3, m3 = e3(sku_ids, hist, aff, locs, xyz, "DP-E3", as_of)
    r4, m4 = e4(sku_ids, fc, locs, "DP-E4", as_of)
    r5, m5 = e5(sku_ids, fc, locs, "DP-E5", as_of)
    # stable normalization reference: hist-frequency max (no promo/noise drift)
    hist_freq = defaultdict(float)
    for ln in hist:
        hist_freq[ln.sku_id] += ln.quantity
    fmax_ref = (max(hist_freq.values(), default=1.0) or 1.0) * (state["n_fut"] / max(state["n_hist"], 1))
    mean_dist = sum(math.dist((l.x, l.y, l.z), (0, 0, 0)) for l in locs) / max(len(locs), 1)
    r6, m6 = e6(sku_ids, fc, aff, locs, xyz, "DP-E6", as_of, time_budget_s=15.0,
                fmax_ref=fmax_ref)
    # E7 calibrated move cost: 0.15 x typical-SKU-full-aisle saving (R09 review)
    mc = 0.15 * fmax_ref * mean_dist * regime.move_cost_scale
    r7, m7 = e7(sku_ids, fc, locs, xyz, m1, "DP-E7", as_of,
                move_cost=mc, time_budget_s=15.0)

    maps = {"E1_StaticABC": m1, "E2_COI": m2, "E3_Affinity": m3,
            "E4_ForecastABC": m4, "E5_Robust": m5, "E6_FcAff": m6, "E7_RollingLite": m7}
    assign = [r1, r2, r3, r4, r5, r6, r7]

    n_eff = len(locs)
    viol = {k: count_capacity_violations(m, n_eff) for k, m in maps.items()}
    if any(viol.values()):
        return None, f"capacity violations: { {k: len(v) for k, v in viol.items() if v} }"

    sim_cfg = ReplayConfig(n_pickers=3)
    fut_orders, fut_lines = state["fut_orders"], state["fut_lines"]

    def flow(m):
        r = replay(fut_orders, fut_lines, m, xyz, sim_cfg)
        return r.total_wait_s + r.total_travel_s + r.total_pick_s

    base_l0 = total_route_cost(fut_lines, m1, xyz)
    base_l1 = flow(m1)

    # relocation cost component (spec §11 first real slice: C = C_pick + λ_m·C_move).
    # unit move cost ≈ 0.05% of baseline pick cost (calibration: full re-slot of
    # ~n SKUs must cost less than a promotion-shock pick advantage (~15-25%) but
    # more than a stable-demand pick edge (~0-3%) — so R1/R6 favor keeping the
    # layout while R2 rewards re-slotting). R6 scales it ×20.
    mc_unit = 0.0005 * base_l0 * regime.move_cost_scale
    moves = {k: sum(1 for s in sku_ids if m.get(s) != m1.get(s))
             for k, m in maps.items()}

    l0 = {}
    for k, m in maps.items():
        pick = total_route_cost(fut_lines, m, xyz)
        l0[k] = (pick + moves[k] * mc_unit) / (base_l0 + 0.0)  # E1: 0 moves → pure pick
    l1 = {k: normalized_cost(flow(m), base_l1) for k, m in maps.items()}
    return (l0, l1, assign, maps, moves), None


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--seeds", type=int, nargs="+", default=[7, 17, 27])
    p.add_argument("--smoke", action="store_true")
    args = p.parse_args()

    log = Logger()
    log.log("=== run_r09_ranking_stability.py (Go/No-Go) ===")
    cfg = yaml.safe_load(open(ROOT / "config" / "main_config.yaml"))
    if args.smoke:
        cfg["world_state"].update(n_skus=40, n_locations=20, n_days=8)
        args.seeds = args.seeds[:2]
        log.log("  --smoke: shrunk world")

    specs = regime_specs(seed=0)
    matrix = defaultdict(list)   # (regime, metric, expert) -> [norm costs]
    winners_l0, winners_l1 = defaultdict(list), defaultdict(list)
    failures = []

    for rname in REGIMES:
        regime = specs[rname]
        for seed in args.seeds:
            state = build_state(cfg, regime, seed, log)
            res, err = run_experts(state, seed, log)
            if err:
                log.log(f"  {rname} seed{seed}: {err}", "ERROR")
                failures.append((rname, seed, err))
                continue
            l0, l1, assign, maps, moves = res
            for e in EXPERTS:
                matrix[(rname, "L0", e)].append(l0[e])
                matrix[(rname, "L1", e)].append(l1[e])
            winners_l0[rname].append(min(l0, key=l0.get))
            winners_l1[rname].append(min(l1, key=l1.get))
            log.log(f"  {rname:22s} seed{seed}: L0 winner={winners_l0[rname][-1]:16s} "
                    f"E1={l0['E1_StaticABC']:.3f} E3={l0['E3_Affinity']:.3f} "
                    f"E4={l0['E4_ForecastABC']:.3f} E5={l0['E5_Robust']:.3f} "
                    f"E6={l0['E6_FcAff']:.3f} E7={l0['E7_RollingLite']:.3f}")

        # non-vacuous validate on the last state of this regime
        world = {
            "sku_master": state["sku_master"], "orders": state["fut_orders"],
            "order_lines": state["fut_lines"], "forecast_daily": [],
            "locations": state["locations"], "inventory_snapshot": [],
            "slot_assignment": [a for batch in assign for a in batch],
            "constraints": sampler.make_constraints(state["locations"]),
            "decision_plan": [],
        }
        try:
            validate_pipeline(world)
        except ValidationError as e:
            failures.append((rname, "validate", str(e)[:80]))

    n_states = sum(len(v) for v in winners_l0.values())
    # global winner distribution
    all_winners_l0 = [w for v in winners_l0.values() for w in v]
    dist = Counter(all_winners_l0)
    top_expert, top_count = dist.most_common(1)[0]
    dominance = top_count / n_states
    n_distinct_winners = len(dist)

    # per-regime winner (modal over seeds)
    regime_winner = {r: Counter(v).most_common(1)[0][0] for r, v in winners_l0.items()}

    # predicted patterns (spec update §9 table)
    predicted = {"R1_stable": "E1_StaticABC", "R2_promotion": "E4_ForecastABC",
                 "R3_velocity_reversal": "E4_ForecastABC", "R4_affinity_shift": "E3_Affinity",
                 "R5_forecast_error": "E5_Robust", "R6_move_cost": "E1_StaticABC",
                 "R7_capacity": None}
    matched = sum(1 for r, w in regime_winner.items()
                  if predicted.get(r) and w == predicted[r])

    go = (dominance < 0.95) and n_distinct_winners >= 3
    log.log(f"  dominance: {top_expert} wins {top_count}/{n_states} = {dominance:.0%} "
            f"| distinct winners = {n_distinct_winners}")
    log.log(f"  regime winners (L0): {regime_winner}")
    log.log(f"  predicted-pattern matches: {matched}/{sum(1 for v in predicted.values() if v)}")
    log.log(f"  VERDICT: {'GO — expert selection has research value' if go else 'NO-GO — one expert dominates; selector research invalid'}")

    # report
    agg_rows = []
    for r in REGIMES:
        cells = []
        for e in EXPERTS:
            v = matrix[(r, "L0", e)]
            cells.append(f"{statistics.fmean(v):.3f}" if v else "—")
        agg_rows.append(f"| {r} | " + " | ".join(cells) + f" | {regime_winner[r]} |")
    out = ROOT / "outputs" / "experiments" / "r09_ranking_stability.md"
    out.write_text(f"""# R09 — Expert Ranking Stability: the Go/No-Go experiment (spec update §10, Step 4)

**Date**: {datetime.now(timezone.utc).isoformat()} | states = {len(REGIMES)} regimes × {len(args.seeds)} seeds = {n_states} | world = {cfg['world_state']['n_skus']} SKU / {cfg['world_state']['n_locations']} loc / {cfg['world_state']['n_days']} d

## Cost matrix — mean NormalizedCost vs E1 (L0 route, FUTURE window, honest split)

| Regime | {' | '.join(EXPERTS)} | winner |
|--------|{'------|'*len(EXPERTS)}--------|
{chr(10).join(agg_rows)}

## Winner switching
- distinct winners across {n_states} states: **{n_distinct_winners}** ({', '.join(f'{k}×{v}' for k, v in dist.most_common())})
- dominance of best single expert: **{top_expert} {top_count}/{n_states} = {dominance:.0%}**
- regime → modal winner: {regime_winner}
- predicted pattern matches (§9 table): **{matched}**/6

## Verdict
{'**GO** — expert ranking switches with warehouse state in interpretable patterns; instance-wise selection (and the Selector research program) is justified.' if go else '**NO-GO** — a single expert dominates; fixed-best is near-optimal and the Selector research question does not hold as posed.'}

## Caveats (honest scope)
- Synthetic platform (Zipf + basket structure + controlled regimes); WEPA/SLAPStack
  replication is the next step if GO (spec update §1: WEPA is the phase-1 priority).
- Cost = L0 route + L1 flow only; λ_r/λ_m/λ_c components enter with the full
  replenishment/relocation model (E7 full rolling, Step 10).
- E7 is the single-window reduction (move-penalized re-slot), declared in module
  docstring; multi-period rolling may change R6's shape but not the Go/No-Go logic.
- R5 noise hits E4/E5/E6's forecast INPUT only (the stream itself is R1-stable),
  per spec §9 definition of forecast uncertainty.
{('- Failures: ' + str(failures)) if failures else ''}
""")
    log.log(f"  wrote outputs/experiments/r09_ranking_stability.md")
    log.log("=== done ===")
    sys.exit(0 if go else 3)


if __name__ == "__main__":
    main()
