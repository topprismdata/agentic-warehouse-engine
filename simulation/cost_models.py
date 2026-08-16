"""
simulation/cost_models.py — SPEC v1.5 §5: graded internal cost models.

The attribution experiment (R17) holds the warehouse trajectory fixed and
swaps ONLY the internal cost model a receding-horizon policy plans with:
  L1_linear      sum_s p50_s * dist(loc_s)            (v1, crude)
  L2_stopaware   per-order stop-count surrogate: for each HISTORICAL basket
                 pattern, expected stops ~ distinct locations of its SKUs;
                 cost ~ n_stops * stop_price + travel * dist
  L3_route       L0 greedy-route surrogate on forecast-expected orders
  L4_oracle      realized route cost (cheating upper reference: the model
                 the ex-post benchmark uses)
Each model exposes: pick_cost(view, layout) — what the agent believes.
"""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Dict, List, Tuple

from or_experts.policies import StateView

STOP_PRICE = 20.0    # seconds-equivalent per distinct stop (calibrated to replay pick_time_per_stop)
TRAVEL_SPEED = 1.2   # m/s


def dist_of(xyz, loc):
    x, y, z = xyz[loc]
    return math.sqrt(x * x + y * y + z * z)


def l1_linear(view: StateView, layout: Dict[str, str]) -> float:
    total = 0.0
    for s, f in view.fc.items():
        loc = layout.get(s)
        if loc:
            total += f.p50 * dist_of(view.xyz, loc)
    return total


def _basket_table(view: StateView, max_orders: int = 300):
    """Distinct-SKU sets of recent orders (recency-weighted sample of the
    basket structure the stop-aware model knows)."""
    by_order = defaultdict(set)
    for ln in view.hist_lines:
        by_order[ln.order_id].add(ln.sku_id)
    orders = list(by_order.items())
    if len(orders) > max_orders:
        stride = len(orders) // max_orders
        orders = orders[::stride]
    return orders


def l2_stopaware(view: StateView, layout: Dict[str, str]) -> float:
    """Expected stop+travel over recent basket patterns, demand-weighted:
    each sampled order is 'expected to arrive' with weight proportional to
    its SKUs' forecast p50 relative to their history."""
    total = 0.0
    for _, skus in _basket_table(view):
        locs = {layout.get(s) for s in skus if layout.get(s)}
        if not locs:
            continue
        ds = [dist_of(view.xyz, l) for l in locs]
        total += len(locs) * STOP_PRICE + sum(ds) / TRAVEL_SPEED * 2.0
    n = max(1, len(_basket_table(view, max_orders=300)))
    return total / n * 14.0   # scale: expected orders per period (~14/day)


def _expected_orders(view: StateView, max_orders: int = 60):
    """Forecast-weighted synthetic orders: sample SKUs ~ p50 as inclusion
    probability; basket composition from recent co-pick structure."""
    by_order = defaultdict(set)
    for ln in view.hist_lines:
        by_order[ln.order_id].add(ln.sku_id)
    pats = list(by_order.values())
    p50 = {s: f.p50 for s, f in view.fc.items()}
    tot = sum(p50.values()) or 1.0
    exp_lines = tot / max(1, sum(len(p) for p in pats) / max(1, len(pats)))
    n_orders = max(1, int(round(exp_lines / 3.0)))   # ~3 lines/order
    import random
    rng = random.Random(0)
    orders = []
    for _ in range(n_orders):
        pat = pats[rng.randrange(len(pats))] if pats else set()
        orders.append(set(rng.sample(sorted(pat), k=min(len(pat), 2))) if pat else set())
    return orders


def l3_route(view: StateView, layout: Dict[str, str]) -> float:
    """Greedy-route surrogate over forecast-expected orders (entrance tour)."""
    from evaluation.route_cost import greedy_route_distance
    total = 0.0
    for skus in _expected_orders(view):
        pts = [view.xyz[layout[s]] for s in skus if layout.get(s) in view.xyz]
        total += greedy_route_distance(pts)
    return total


def l4_oracle_cost(view: StateView, layout: Dict[str, str],
                   period_lines, xyz) -> float:
    """Realized L0 route cost on the actual future lines (cheating model —
    only as the fidelity ceiling reference)."""
    from evaluation.route_cost import total_route_cost
    return total_route_cost(period_lines, layout, xyz)


MODEL_REGISTRY = {
    "L1_linear": l1_linear,
    "L2_stopaware": l2_stopaware,
    "L3_route": l3_route,
}
