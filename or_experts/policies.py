"""
or_experts/policies.py — v1.2 §4: Expert Library v3.1 as POLICIES.

A policy reads (state view, current layout) and returns a PolicyDecision:
new layout + explicit move list. Costs are computed by the sequential
benchmark, not by the policy (single accounting authority).

Experts:
  E1 StaticABC   full-history frequency ranking        (slow-moving -> stable)
  E2 COI         freq/volume ranking
  E3 Affinity    recency-weighted co-pick clustering
  E4 Forecast    informed forecast p50 ranking (promotions known)
  E5 Robust      p50 - kappa*spread
  E6 DDSR-lite   OPPORTUNISTIC reposition from current layout: move a SKU
                 only if expected saving > move_cost * margin (spec §3.3
                 payback trigger; Karimi et al. DDSR spirit, simplified)
  E7 Joint       CP-SAT: forecast pick cost + move penalty (replenish joint
                 component deferred, declared)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from world_state.schemas import Location, OrderLine
from features.affinity import AffinityGraph, compute_affinity
from features.forecast import SkuForecast
from or_experts.b1_static_abc import assign_static_abc as _e1
from or_experts.b2_coi import assign_coi as _e2
from or_experts.b3_affinity import assign_affinity as _e3
from or_experts.e4_e7 import assign_e4_forecast_abc as _e4
from or_experts.e4_e7 import assign_e5_robust as _e5
from or_experts.e4_e7 import assign_e7_rolling_lite as _e7
from ortools.sat.python import cp_model

EXPERT_IDS = ["E1_StaticABC", "E2_COI", "E3_Affinity", "E4_Forecast",
              "E5_Robust", "E6_DDSR", "E7_Joint"]

# experts whose LAYOUT output does not depend on the incoming layout
# (beam search caches these per period; E6/E7 are layout-dependent)
LAYOUT_INDEPENDENT = ["E1_StaticABC", "E2_COI", "E3_Affinity",
                      "E4_Forecast", "E5_Robust"]


@dataclass
class StateView:
    """What policies may see at period t (no future orders beyond `known`)."""
    sku_ids: List[str]
    sku_master: list
    locations: List[Location]
    xyz: Dict[str, Tuple[float, float, float]]
    hist_lines: List[OrderLine]           # all past lines
    hist_line_day: Dict[str, float]       # order_id -> day index
    hist_span_days: float
    fc: Dict[str, SkuForecast]            # informed forecast for THIS period
    fc_known_promo: Dict[str, float]      # the promotion map (known events)
    aff: AffinityGraph                    # recency-weighted
    move_cost_scale: float                # regime move-cost multiplier


@dataclass
class PolicyDecision:
    expert_id: str
    layout: Dict[str, str]
    moves: List[Tuple[str, str, str]] = field(default_factory=list)  # (sku, from, to)

    @property
    def n_moves(self) -> int:
        return len(self.moves)


def _diff(current: Dict[str, str], new: Dict[str, str]) -> List[Tuple[str, str, str]]:
    return [(s, current.get(s), l) for s, l in new.items() if current.get(s) != l]


def _wrap(expert_id, current, new_map) -> PolicyDecision:
    return PolicyDecision(expert_id=expert_id, layout=new_map,
                          moves=_diff(current or {}, new_map))


def e1_static(view: StateView, current: Dict[str, str]) -> PolicyDecision:
    _, m = _e1(view.sku_ids, view.hist_lines, view.locations, view.xyz,
               "DP-E1", datetime.now(timezone.utc))
    return _wrap("E1_StaticABC", current, m)


def e2_coi(view: StateView, current: Dict[str, str]) -> PolicyDecision:
    _, m = _e2(view.sku_master, view.hist_lines, view.locations, view.xyz,
               "DP-E2", datetime.now(timezone.utc))
    return _wrap("E2_COI", current, m)


def e3_affinity(view: StateView, current: Dict[str, str]) -> PolicyDecision:
    _, m = _e3(view.sku_ids, view.hist_lines, view.aff, view.locations, view.xyz,
               "DP-E3", datetime.now(timezone.utc))
    return _wrap("E3_Affinity", current, m)


def e4_forecast(view: StateView, current: Dict[str, str]) -> PolicyDecision:
    _, m = _e4(view.sku_ids, view.fc, view.locations, "DP-E4",
               datetime.now(timezone.utc))
    return _wrap("E4_Forecast", current, m)


def e5_robust(view: StateView, current: Dict[str, str]) -> PolicyDecision:
    _, m = _e5(view.sku_ids, view.fc, view.locations, "DP-E5",
               datetime.now(timezone.utc))
    return _wrap("E5_Robust", current, m)


def e6_ddsr(view: StateView, current: Dict[str, str],
            move_cost_units: float, margin: float = 1.5) -> PolicyDecision:
    """Opportunistic reposition: for each SKU (by expected demand desc), try to
    grab a strictly-better free/occupied slot ONLY if expected per-period pick
    saving exceeds margin * move_cost_units. Otherwise stay. Capacity-safe by
    construction (swap-only), never creates violations.

    `move_cost_units` is expressed in the SAME units as pick route cost."""
    if not current:
        # cold start: behave like a forecast slotting (nothing to reposition from)
        return e4_forecast(view, current)
    layout = dict(current)
    ranked_locs = sorted(view.locations,
                         key=lambda l: math.dist((l.x, l.y, l.z), (0, 0, 0)))
    dist = {l.location_id: math.dist((l.x, l.y, l.z), (0, 0, 0)) for l in ranked_locs}
    demand = {s: view.fc[s].p50 for s in view.sku_ids}
    loc_of = {}
    for sku, loc in layout.items():
        loc_of.setdefault(loc, []).append(sku)

    moves: List[Tuple[str, str, str]] = []
    for sku in sorted(view.sku_ids, key=lambda s: demand.get(s, 0.0), reverse=True):
        d = demand.get(sku, 0.0)
        cur = layout.get(sku)
        if cur is None:
            continue
        best_gain, best_pair = 0.0, None
        # try swaps with any SKU closer to the entrance
        for other_loc in ranked_locs:
            if other_loc.location_id == cur:
                continue
            gain = d * (dist[cur] - dist[other_loc.location_id])
            if gain <= best_gain:
                continue
            occupants = loc_of.get(other_loc.location_id, [])
            # empty-enough swap: either free slot or swap with a lower-demand sku
            if not occupants:
                best_gain, best_pair = gain, (sku, cur, other_loc.location_id, None)
            else:
                for other in occupants:
                    og = demand.get(other, 0.0) * (dist[other_loc.location_id] - dist[cur])
                    if gain - og > best_gain and demand.get(other, 0.0) < d:
                        best_gain, best_pair = gain - og, (sku, cur, other_loc.location_id, other)
        if best_pair and best_gain > margin * move_cost_units:
            sku_, frm, to, other = best_pair
            if other is None:
                loc_of.setdefault(to, [])
            else:
                layout[other] = frm
                loc_of[frm] = [x for x in loc_of.get(frm, []) if x != other] + [other]
                loc_of[to] = [x for x in loc_of.get(to, []) if x != other] + [sku_]
                moves.append((other, to, frm))
            layout[sku_] = to
            if other is None:
                loc_of[to].append(sku_)
                loc_of[frm] = [x for x in loc_of.get(frm, []) if x != sku_]
            moves.append((sku_, frm, to))
    return PolicyDecision(expert_id="E6_DDSR", layout=layout, moves=moves)


def e7_joint(view: StateView, current: Dict[str, str],
             move_cost_units: float) -> PolicyDecision:
    if not current:
        d = e4_forecast(view, current)
        d.expert_id = "E7_Joint"
        return d
    _, m = _e7(view.sku_ids, view.fc, view.locations, view.xyz, current,
               "DP-E7", datetime.now(timezone.utc),
               move_cost=move_cost_units, time_budget_s=0.5)
    return _wrap("E7_Joint", current, m)


POLICIES = {
    "E1_StaticABC": lambda v, c, mc: e1_static(v, c),
    "E2_COI": lambda v, c, mc: e2_coi(v, c),
    "E3_Affinity": lambda v, c, mc: e3_affinity(v, c),
    "E4_Forecast": lambda v, c, mc: e4_forecast(v, c),
    "E5_Robust": lambda v, c, mc: e5_robust(v, c),
    "E6_DDSR": lambda v, c, mc: e6_ddsr(v, c, mc),
    "E7_Joint": lambda v, c, mc: e7_joint(v, c, mc),
}


def run_policy(expert_id, view: StateView, current, move_cost_units) -> PolicyDecision:
    return POLICIES[expert_id](view, current, move_cost_units)
