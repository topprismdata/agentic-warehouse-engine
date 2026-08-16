"""
features/affinity.py — Spec §12.2 / §13.2 Affinity Score.

Metrics per SKU pair (i, j):
  CoPick_ij    = # orders containing both i and j
  Support_i    = # orders containing i
  Confidence   = CoPick_ij / Support_i        (i → j)
  Lift_ij      = CoPin_ij * N / (Support_i * Support_j)
  A_ij         = log(1 + CoPick_ij) * Lift_ij ** alpha   (spec §12.2)

Top-K truncation keeps the graph sparse (spec §12.2: avoid O(N^2) blowup).
`alpha` sweep is a v0.3 concern; default 1.0.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from itertools import combinations
from typing import Dict, List, Optional, Tuple

import pandas as pd


@dataclass
class AffinityGraph:
    df: pd.DataFrame                       # all pairs with CoPick > 0
    topk: Dict[str, List[Tuple[str, float]]]  # sku -> [(neighbor, A_ij), ...] best-first
    n_orders: int
    alpha: float

    def neighbors(self, sku: str, threshold: float = 0.0) -> List[Tuple[str, float]]:
        return [(j, a) for j, a in self.topk.get(sku, []) if a > threshold]


def compute_affinity(
    order_lines,
    alpha: float = 1.0,
    top_k: int = 5,
    line_day=None,
    history_time_span_days: float = 0.0,
) -> AffinityGraph:
    """Build the affinity graph from order lines (basket = distinct SKUs per order).

    v1.1: optional recency weighting (same ramp as features.forecast — last
    third of the span gets up to 3x weight) so DYNAMIC affinity (E3 under
    regimes) can read emerging co-pick structure, per spec §13.2's long-term
    vs recent affinity distinction."""
    def _w_of(day: float) -> float:
        if history_time_span_days <= 0 or line_day is None:
            return 1.0
        frac = min(1.0, max(0.0, day / history_time_span_days))
        return 1.0 + 2.0 * max(0.0, frac - 2.0 / 3.0) * 3.0

    order_skus: Dict[str, set] = defaultdict(set)
    for line in order_lines:
        order_skus[line.order_id].add(line.sku_id)
    n_orders = len(order_skus)
    if n_orders == 0:
        return AffinityGraph(pd.DataFrame(), {}, 0, alpha)

    order_weight: Dict[str, float] = {}
    for oid in order_skus:
        d = line_day.get(oid, 0.0) if line_day else 0.0
        order_weight[oid] = _w_of(d)

    support: Dict[str, float] = defaultdict(float)
    copick: Dict[Tuple[str, str], float] = defaultdict(float)
    for oid, skus in order_skus.items():
        wgt = order_weight[oid]
        for s in skus:
            support[s] += wgt
        for i, j in combinations(sorted(skus), 2):
            copick[(i, j)] += wgt

    rows = []
    for (i, j), c in copick.items():
        denom = support[i] * support[j]
        lift = (c * n_orders / denom) if denom > 0 else 0.0
        a_ij = __import__("math").log1p(c) * (lift ** alpha)
        rows.append({
            "sku_i": i, "sku_j": j,
            "copick": c, "support_i": support[i], "support_j": support[j],
            "confidence_ij": c / support[i] if support[i] else 0.0,
            "confidence_ji": c / support[j] if support[j] else 0.0,
            "lift": round(lift, 4),
            "affinity": round(a_ij, 4),
        })
    df = pd.DataFrame(rows)
    if df.empty:
        return AffinityGraph(df, {}, n_orders, alpha)
    df = df.sort_values("affinity", ascending=False).reset_index(drop=True)

    # Top-K per SKU, both directions
    topk: Dict[str, List[Tuple[str, float]]] = defaultdict(list)
    for r in df.itertuples(index=False):
        if len(topk[r.sku_i]) < top_k:
            topk[r.sku_i].append((r.sku_j, r.affinity))
        if len(topk[r.sku_j]) < top_k:
            topk[r.sku_j].append((r.sku_i, r.affinity))

    return AffinityGraph(df=df, topk=dict(topk), n_orders=n_orders, alpha=alpha)
