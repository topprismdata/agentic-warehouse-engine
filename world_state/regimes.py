"""
world_state/regimes.py — Demand regime generation (spec update §9, R1–R7).

A regime is a parameterization of the order-stream generator. The Go/No-Go
experiment (R09) builds states = regime × seed; experts slot on the HISTORY
window and are evaluated on the FUTURE window, so the regime's effect must
be visible in the FUTURE window (see R2/R3/R4 split definitions).

Regime → expected winner (falsifiable predictions):
  R1 stable            -> E1 ABC
  R2 promotion shock   -> E4 forecast (knows the promo; ABC only sees past)
  R3 velocity reversal -> E4 forecast (past ranking is anti-predictive)
  R4 affinity shift    -> E3 affinity (fresh co-pick structure)
  R5 forecast error    -> E5 robust (spread-aware; E4/E6 mis-rank)
  R6 move-cost shock   -> E1 static / E7 frozen (re-slotting not worth it)
  R7 capacity shock    -> tighter packing favors solver (E6/E7)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

REGIMES = ["R1_stable", "R2_promotion", "R3_velocity_reversal",
           "R4_affinity_shift", "R5_forecast_error", "R6_move_cost", "R7_capacity"]


@dataclass
class RegimeSpec:
    name: str
    # order-stream shaping
    promotion: Optional[Dict[str, float]] = None   # sku -> multiplier, FUTURE window only
    velocity_reversal: bool = False                # GRADUAL rank inversion (spec §9:
                                                    # "逐渐变" — starts in late history)
    affinity_remap_future: bool = False            # R4: basket re-groups (structure shift,
                                                    # not disappearance) starting late-history
    affinity_conc_hist: float = 0.7                # basket concentration, HISTORY
    affinity_conc_future: float = 0.7              # ... FUTURE
    # forecast-side (affects E4/E5/E6 inputs, not the stream itself)
    forecast_noise: float = 0.0                    # R5: 0.1/0.2/0.4 (per-SKU heterogeneous)
    # execution-side
    move_cost_scale: float = 1.0                   # R6: 1/5/20
    location_keep_frac: float = 1.0                # R7: 0.7 keeps 70% of locations


def regime_specs(seed: int) -> Dict[str, RegimeSpec]:
    """Canonical regime set for the Go/No-Go experiment."""
    return {
        "R1_stable": RegimeSpec("R1_stable"),
        "R2_promotion": RegimeSpec("R2_promotion", promotion={}),   # filled per-world (mid-rank SKUs)
        "R3_velocity_reversal": RegimeSpec("R3_velocity_reversal", velocity_reversal=True),
        "R4_affinity_shift": RegimeSpec("R4_affinity_shift", affinity_remap_future=True),
        "R5_forecast_error": RegimeSpec("R5_forecast_error", forecast_noise=0.4),
        "R6_move_cost": RegimeSpec("R6_move_cost", move_cost_scale=20.0),
        "R7_capacity": RegimeSpec("R7_capacity", location_keep_frac=0.7),
    }


def make_regime_orders(
    sku_ids: List[str],
    sku_category: Dict[str, str],
    n_days_hist: int,
    n_days_future: int,
    regime: RegimeSpec,
    rng,
    day_anchor,
    orders_per_day_mean: float = 14.0,
    orders_per_day_std: float = 4.0,
):
    """Generate history+future order lines under a regime.

    Returns (orders, lines, promo_mult) where promo_mult is the KNOWN future
    promotion map (fed to informed forecast; the stream itself multiplies).
    Base popularity: Zipf(1.5) over sku order — same as sample.make_orders.
    """
    from datetime import timedelta
    from .schemas import Order, OrderLine, SourceType

    n = len(sku_ids)
    weights_hist = [1.0 / ((i + 1) ** 1.5) for i in range(n)]
    weights_future = list(weights_hist)
    if regime.velocity_reversal:
        weights_future = [1.0 / ((n - i) ** 1.5) for i in range(n)]  # rank inverted

    # R2: promote the mid-rank band (history-median popularity) x8 — the case
    # where ABC's past ranking is actively wrong and the promo is KNOWABLE
    promo_mult = dict(regime.promotion or {})
    if regime.name == "R2_promotion" and not promo_mult:
        lo, hi = int(n * 0.3), int(n * 0.6)
        for i in range(lo, hi):
            promo_mult[sku_ids[i]] = 8.0

    eff_weights_future = [w * promo_mult.get(s, 1.0)
                          for w, s in zip(weights_future, sku_ids)]

    # basket sampling pools by category (for concentration control)
    cat_members: Dict[str, List[str]] = {}
    for s in sku_ids:
        cat_members.setdefault(sku_category.get(s, "CAT00"), []).append(s)
    cat_names = list(cat_members)
    cat_weights = {c: [1.0 / ((i + 1) ** 1.5) for i in range(len(m))]
                   for c, m in cat_members.items()}

    orders, lines = [], []
    seq = 0
    total_days = n_days_hist + n_days_future
    for day in range(total_days):
        is_future = day >= n_days_hist
        conc = regime.affinity_conc_future if is_future else regime.affinity_conc_hist

        # R3 GRADUAL reversal: linear ramp starting at 60% of history, fully
        # inverted by 40% of future (spec §9 "逐渐变" — late history carries the
        # signal that a recency-weighted forecaster can read)
        w = list(weights_hist)
        if regime.velocity_reversal:
            t0 = 0.6 * n_days_hist
            t1 = n_days_hist + 0.4 * n_days_future
            if day >= t0:
                frac = min(1.0, (day - t0) / max(1e-9, t1 - t0))
                w = [(1 - frac) * wh + frac * wf
                     for wh, wf in zip(weights_hist, weights_future)]
        elif is_future:
            w = weights_future

        # R4 basket RE-GROUPING: from 60% of history onward, choosing lead
        # category i actually draws from category (i+shift)'s members — the
        # CO-PURCHASE GROUPS re-form (concentration preserved, pairs change),
        # and a recency-weighted affinity learner sees the new pairs emerging
        remap_shift = 0
        if regime.affinity_remap_future and day >= 0.4 * n_days_hist:
            remap_shift = max(1, len(cat_names) // 2)

        def draw_basket_sku(lead: str) -> str:
            pool_cat = lead
            if remap_shift:
                i = cat_names.index(lead)
                pool_cat = cat_names[(i + remap_shift) % len(cat_names)]
            m = cat_members[pool_cat]
            mw = cat_weights[pool_cat]
            # promotion applies to the FUTURE window only (hist must be clean —
            # R09 review: applying it in history too erased E4's information
            # edge because E1's historical frequencies already "saw" the promo)
            if is_future:
                mw = [cw * promo_mult.get(sku, 1.0)
                      for cw, sku in zip(mw, m)]
            return rng.choices(m, weights=mw, k=1)[0]

        w_eff = w if not is_future else [
            wt * promo_mult.get(s, 1.0) for wt, s in zip(w, sku_ids)]

        n_orders = max(1, int(rng.gauss(orders_per_day_mean, orders_per_day_std)))
        for _ in range(n_orders):
            seq += 1
            t = day_anchor + timedelta(days=day, hours=rng.uniform(8, 18))
            t = t.replace(tzinfo=t.tzinfo or __import__("datetime").timezone.utc)
            oid = f"O{seq:06d}"
            lead = rng.choice(cat_names)
            orders.append(Order(order_id=oid, order_time=t, known_at_time=t,
                                channel="b2c", cutoff=t + timedelta(hours=4),
                                priority=0, wave_id=None,
                                source_type=SourceType.SYNTHETIC))
            for k in range(rng.randint(1, 6)):
                if rng.random() < conc and lead in cat_members:
                    sku = draw_basket_sku(lead)
                else:
                    sku = rng.choices(sku_ids, weights=w_eff, k=1)[0]
                lines.append(OrderLine(order_id=oid, sku_id=sku, quantity=float(rng.randint(1, 12)),
                                       uom="each", pick_sequence=k + 1,
                                       source_type=SourceType.SYNTHETIC))
    return orders, lines, promo_mult
