"""
simulation/replay.py — Spec §14.3 L1 fidelity: SimPy discrete-event replay.

Model (deliberately minimal — calibration protocol comes with real data):
  - Orders are released at their `order_time` (known_at_time == order_time
    in v0.1, so release == visibility — no lookahead advantage).
  - A fixed pool of pickers (resource) each executes orders FIFO by wave
    then priority (v0.1: FIFO by release time; wave/priority is v0.3).
  - One order = one tour: travel at `speed` m/s over the greedy route
    (L0 geometry reused), plus `pick_time_per_stop` s at each DISTINCT stop
    (quantity per line folds into stop time via `pick_time_per_unit`).
  - Output: per-order completion time, picker utilization, queue waits.

Calibration hooks (spec §14.2 "simulation must be calibrated by replay"):
  `sim_gate` in verify_gate.yaml holds max_relative_mae — until real task
  durations exist, R04 reports utilization/wait sanity rather than claiming
  calibrated accuracy.
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

import simpy

from world_state.schemas import Order, OrderLine
from evaluation.route_cost import greedy_route_distance

ENTRANCE = (0.0, 0.0, 0.0)


@dataclass
class ReplayConfig:
    n_pickers: int = 3
    speed_m_s: float = 1.2          # walking speed (m/s)
    pick_time_per_stop_s: float = 20.0
    pick_time_per_unit_s: float = 2.0
    sim_horizon_s: float = 14 * 24 * 3600.0  # 14 days


@dataclass
class ReplayResult:
    n_orders: int = 0
    makespan_s: float = 0.0
    total_completion_s: float = 0.0
    total_wait_s: float = 0.0
    total_travel_s: float = 0.0
    total_pick_s: float = 0.0
    utilization: float = 0.0
    per_order: List[Dict] = field(default_factory=list)

    def summary(self) -> str:
        return (f"orders={self.n_orders} makespan={self.makespan_s/3600:.1f}h "
                f"busy/picker={self.utilization:.2%} "
                f"wait={self.total_wait_s/3600:.1f}h "
                f"travel={self.total_travel_s/3600:.1f}h "
                f"pick={self.total_pick_s/3600:.1f}h")


def replay(
    orders: List[Order],
    order_lines: List[OrderLine],
    sku_to_loc: Dict[str, str],
    xyz_lookup: Dict[str, Tuple[float, float, float]],
    cfg: ReplayConfig = None,
) -> ReplayResult:
    cfg = cfg or ReplayConfig()
    result = ReplayResult()

    # Pre-compute per order: distinct stop points, total units
    lines_by_order: Dict[str, List[OrderLine]] = defaultdict(list)
    for ln in order_lines:
        lines_by_order[ln.order_id].append(ln)
    order_meta: Dict[str, Dict] = {}
    t0 = min(o.order_time for o in orders)
    for o in orders:
        lns = lines_by_order.get(o.order_id, [])
        sku_set = {ln.sku_id for ln in lns}
        locs = {sku_to_loc[s] for s in sku_set if s in sku_to_loc}
        pts = [xyz_lookup[l] for l in locs if l in xyz_lookup]
        units = sum(ln.quantity for ln in lns)
        release_s = (o.order_time - t0).total_seconds()
        order_meta[o.order_id] = {
            "release_s": release_s,
            "route_m": greedy_route_distance(pts),
            "n_stops": len(pts),
            "units": units,
        }

    env = simpy.Environment()
    pickers = simpy.Resource(env, capacity=cfg.n_pickers)

    def order_proc(order_id: str):
        meta = order_meta[order_id]
        yield env.timeout(meta["release_s"])            # release at order_time
        with pickers.request() as req:
            req_time = env.now
            yield req
            wait = env.now - req_time
            travel = meta["route_m"] / cfg.speed_m_s
            pick = (meta["n_stops"] * cfg.pick_time_per_stop_s
                    + meta["units"] * cfg.pick_time_per_unit_s)
            yield env.timeout(travel + pick)
            result.per_order.append({
                "order_id": order_id,
                "release_s": meta["release_s"],
                "wait_s": wait,
                "travel_s": travel,
                "pick_s": pick,
                "completion_s": env.now,
            })
            result.total_wait_s += wait
            result.total_travel_s += travel
            result.total_pick_s += pick

    for oid in order_meta:
        env.process(order_proc(oid))
    env.run(until=cfg.sim_horizon_s)

    result.n_orders = len(result.per_order)
    if result.per_order:
        result.makespan_s = max(r["completion_s"] for r in result.per_order)
        result.total_completion_s = sum(r["completion_s"] for r in result.per_order)
        busy = result.total_travel_s + result.total_pick_s
        result.utilization = busy / (cfg.n_pickers * max(result.makespan_s, 1e-9))
    return result
