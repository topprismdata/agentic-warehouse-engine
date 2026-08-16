"""
world_state/regime_sequence.py — v1.2 §5/§6: regimes as a CONTINUOUS time series.

Replaces v1.1's independent-regime sampler (regimes.py stays for reference).
A RegimeSequence is a list of DayParams — one per day — with phases:
promo has ramp-up/peak/decay, velocity reversal ramps gradually, affinity
re-maps for a stretch, move-cost and forecast-noise shocks hit windows.

Default sequence (28 d / 8 phases):
  stable 4 -> promo-ramp 2 -> promo-peak 4 -> promo-decay 2 -> stable 3
  -> reversal 6 (gradual) -> affinity-shift 4 -> move-cost-shock 3
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

from .schemas import Order, OrderLine, SourceType

PROMO_BAND = (0.3, 0.6)   # mid-rank SKUs get promoted (ABC's blind spot)
PROMO_PEAK = 8.0


@dataclass
class DayParams:
    day: int
    phase: str
    promo_mult: Dict[str, float] = field(default_factory=dict)
    velocity_mix: float = 0.0     # 0 = original Zipf ranks, 1 = fully inverted
    affinity_remap: bool = False
    move_cost_scale: float = 1.0
    forecast_noise: float = 0.0


@dataclass
class Phase:
    name: str
    start: int
    end: int                    # exclusive

    @property
    def days(self):
        return range(self.start, self.end)


def default_phases() -> List[Phase]:
    return [
        Phase("stable", 0, 4),
        Phase("promo_ramp", 4, 6),
        Phase("promo_peak", 6, 10),
        Phase("promo_decay", 10, 12),
        Phase("stable2", 12, 15),
        Phase("reversal", 15, 21),
        Phase("affinity_shift", 21, 25),
        Phase("move_cost_shock", 25, 28),
    ]


def build_sequence(sku_ids: List[str],
                   phases: Optional[List[Phase]] = None) -> List[DayParams]:
    phases = phases or default_phases()
    n = phases[-1].end
    band = [sku_ids[int(len(sku_ids) * lo):int(len(sku_ids) * hi)]
            for lo, hi in [PROMO_BAND]][0]

    seq: List[DayParams] = []
    for ph in phases:
        for d in ph.days:
            p = DayParams(day=d, phase=ph.name)
            if ph.name == "promo_ramp":
                frac = (d - ph.start) / max(1, ph.end - ph.start)
                m = 1.0 + (PROMO_PEAK - 1.0) * frac
                p.promo_mult = {s: m for s in band}
            elif ph.name == "promo_peak":
                p.promo_mult = {s: PROMO_PEAK for s in band}
            elif ph.name == "promo_decay":
                frac = (d - ph.start) / max(1, ph.end - ph.start)
                m = PROMO_PEAK - (PROMO_PEAK - 1.0) * frac
                p.promo_mult = {s: m for s in band}
            elif ph.name == "reversal":
                p.velocity_mix = (d - ph.start + 1) / (ph.end - ph.start)
            elif ph.name == "affinity_shift":
                p.affinity_remap = True
            elif ph.name == "move_cost_shock":
                p.move_cost_scale = 20.0
            seq.append(p)
    assert len(seq) == n
    return seq


def generate_stream(sku_ids, sku_category, seq: List[DayParams], rng,
                    anchor: datetime,
                    orders_per_day_mean=14.0, orders_per_day_std=4.0,
                    concentration=0.7):
    """Order stream over the whole sequence. Same generative mechanics as
    v1.1 (Zipf base + category baskets + optional promo mult / rank inversion /
    category remap), but driven per-day by DayParams — no future-only switch,
    the timeline IS the regime."""
    n = len(sku_ids)
    w_base = [1.0 / ((i + 1) ** 1.5) for i in range(n)]
    w_inv = [1.0 / ((n - i) ** 1.5) for i in range(n)]

    cat_members: Dict[str, List[str]] = {}
    for s in sku_ids:
        cat_members.setdefault(sku_category.get(s, "CAT00"), []).append(s)
    cat_names = list(cat_members)
    cat_weights = {c: [1.0 / ((i + 1) ** 1.5) for i in range(len(m))]
                   for c, m in cat_members.items()}
    remap_shift = max(1, len(cat_names) // 2)

    orders, lines = [], []
    seq_i = 0
    for dp in seq:
        w = [(1 - dp.velocity_mix) * a + dp.velocity_mix * b
             for a, b in zip(w_base, w_inv)]
        n_orders = max(1, int(rng.gauss(orders_per_day_mean, orders_per_day_std)))
        for _ in range(n_orders):
            seq_i += 1
            t = anchor + timedelta(days=dp.day, hours=rng.uniform(8, 18))
            t = t.replace(tzinfo=t.tzinfo or timezone.utc)
            oid = f"O{seq_i:06d}"
            lead = rng.choice(cat_names)
            orders.append(Order(order_id=oid, order_time=t, known_at_time=t,
                                channel="b2c", cutoff=t + timedelta(hours=4),
                                priority=0, wave_id=None,
                                source_type=SourceType.SYNTHETIC))
            for k in range(rng.randint(1, 6)):
                if rng.random() < concentration:
                    pool = lead
                    if dp.affinity_remap:
                        i = cat_names.index(lead)
                        pool = cat_names[(i + remap_shift) % len(cat_names)]
                    m = cat_members[pool]
                    mw = [cw * dp.promo_mult.get(s, 1.0)
                          for cw, s in zip(cat_weights[pool], m)]
                    sku = rng.choices(m, weights=mw, k=1)[0]
                else:
                    we = [wt * dp.promo_mult.get(s, 1.0)
                          for wt, s in zip(w, sku_ids)]
                    sku = rng.choices(sku_ids, weights=we, k=1)[0]
                lines.append(OrderLine(order_id=oid, sku_id=sku,
                                       quantity=float(rng.randint(1, 12)),
                                       uom="each", pick_sequence=k + 1,
                                       source_type=SourceType.SYNTHETIC))
    return orders, lines
