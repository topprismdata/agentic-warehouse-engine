"""
evaluation/route_cost.py — Spec §14.3 L0 fidelity: static route cost.

Upgrades the v0.1 per-line Euclidean proxy to per-ORDER route distance:
each order is one picker tour from the entrance, visiting the DISTINCT
locations of its SKUs, and returning. Greedy nearest-neighbor TSP (fine
for ≤6 stops/order at L0; L1 SimPy replaces this in Todo #11).

Why this matters: affinity-based slotting only pays off when co-picked SKUs
share a stop — a per-line proxy cannot see that, an order route can.
"""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Dict, List, Tuple

from world_state.schemas import OrderLine

ENTRANCE = (0.0, 0.0, 0.0)


def _d(a: Tuple[float, float, float], b: Tuple[float, float, float]) -> float:
    return math.dist(a, b)


def greedy_route_distance(points: List[Tuple[float, float, float]]) -> float:
    """Greedy NN tour ENTRANCE → all points → ENTRANCE. Points may repeat."""
    remaining = list(points)
    cur = ENTRANCE
    total = 0.0
    while remaining:
        nxt_i = min(range(len(remaining)), key=lambda k: _d(cur, remaining[k]))
        nxt = remaining.pop(nxt_i)
        total += _d(cur, nxt)
        cur = nxt
    total += _d(cur, ENTRANCE)
    return total


def order_route_distance(
    sku_set, sku_to_loc: Dict[str, str], xyz_lookup: Dict[str, Tuple[float, float, float]]
) -> float:
    """One tour per order over the DISTINCT locations of its SKUs."""
    locs = {sku_to_loc[s] for s in sku_set if s in sku_to_loc}
    pts = [xyz_lookup[l] for l in locs if l in xyz_lookup]
    return greedy_route_distance(pts)


def total_route_cost(
    order_lines: List[OrderLine],
    sku_to_loc: Dict[str, str],
    xyz_lookup: Dict[str, Tuple[float, float, float]],
) -> float:
    """Sum of per-order route distances across all orders."""
    order_skus: Dict[str, set] = defaultdict(set)
    for line in order_lines:
        order_skus[line.order_id].add(line.sku_id)
    return float(sum(
        order_route_distance(skus, sku_to_loc, xyz_lookup)
        for skus in order_skus.values()
    ))
