"""
features/forecast.py — Per-SKU demand forecast for E4/E5/E6 (spec update §8).

Interface: given HISTORY lines (+ optional known future events) and a noise
level, produce per-SKU p10/p50/p90 of expected pick-frequency in the eval
window.

v1.1 revisions (R09 review):
  - RECENCY-WEIGHTED history: the last third of the history window gets 3x
    weight, so gradual regime shifts (R3 velocity reversal per spec §9:
    "A 类【逐渐】变 C") leave a signal experts can read. Full-history means
    are what E1 effectively sees; recency is what a *forecast* expert owes.
  - HETEROGENEOUS uncertainty (R5): noise_sigma is drawn per SKU ~ max(0.05,
    N(sigma, sigma/2)); promoted SKUs get +0.15 extra uncertainty (promotion
    forecasting is harder in practice). A flat multiplicative spread re-scales
    every p50 identically and NEVER changes the ranking — which made E5≡E4.

Knowledge modes (spec §13.1: promotions are KNOWN events, not guessed):
  - naive:    p50 = recency-weighted history freq * window ratio
  - informed: p50 *= promotion_multiplier(sku)
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from world_state.schemas import OrderLine


@dataclass
class SkuForecast:
    p10: float
    p50: float
    p90: float


def forecast_demand(
    sku_ids: List[str],
    history_lines: List[OrderLine],
    future_days: float,
    history_days: float,
    history_time_span_days: float = 0.0,   # for recency weighting
    line_day: Optional[Dict[str, float]] = None,  # order_id -> day index (0-based)
    promotion: Optional[Dict[str, float]] = None,
    noise_sigma: float = 0.0,
    seed: int = 0,
) -> Dict[str, SkuForecast]:
    rng = random.Random(seed)
    if history_days <= 0:
        history_days = 1.0
    scale = future_days / history_days

    # recency weights: last third of the span gets 3x (linear ramp)
    def w_of(day: float) -> float:
        if history_time_span_days <= 0 or line_day is None:
            return 1.0
        frac = min(1.0, max(0.0, day / history_time_span_days))
        return 1.0 + 2.0 * max(0.0, frac - 2.0 / 3.0) * 3.0  # 1 -> 3 ramp

    hist_freq: Dict[str, float] = {}
    for ln in history_lines:
        day = line_day.get(ln.order_id, 0.0) if line_day else 0.0
        hist_freq[ln.sku_id] = hist_freq.get(ln.sku_id, 0.0) + ln.quantity * w_of(day)

    out: Dict[str, SkuForecast] = {}
    for sku in sku_ids:
        base = hist_freq.get(sku, 0.0) * scale
        if promotion and sku in promotion:
            base *= promotion[sku]
        # per-SKU heterogeneous noise (R5); promoted SKUs harder to forecast
        sigma = 0.0
        if noise_sigma > 0:
            sigma = max(0.05, rng.gauss(noise_sigma, noise_sigma / 2))
            if promotion and sku in promotion:
                sigma += 0.15
            base *= max(0.0, rng.gauss(1.0, sigma))
        p50 = base
        cv = max(0.10, sigma if sigma > 0 else 0.10)
        out[sku] = SkuForecast(p10=max(0.0, p50 * (1 - 1.2816 * cv)),
                               p50=p50,
                               p90=p50 * (1 + 1.2816 * cv))
    return out
