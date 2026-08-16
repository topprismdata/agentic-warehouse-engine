"""
simulation/sequential.py — v1.2 Step 1: sequential DWERP benchmark core.

Rolls the timeline phase by phase. At each period t:
  - every expert produces a PolicyDecision (from the CURRENT layout on the
    myopic path — see SPEC v1.2 §9 scope note)
  - per-expert period cost = pick(route) + λm * moves * mc_unit  [λs = 0 in T0]
  - myopic winner = argmin; the myopic path's layout advances to the winner's
Outputs the full cost matrix + myopic labels, which are the direct input to
T1 (dynamic oracle needs the same machinery under trajectory rollouts).
"""

from __future__ import annotations

import random
import statistics
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from world_state.schemas import OrderLine
from world_state.regime_sequence import DayParams, Phase, build_sequence, generate_stream
from features.affinity import compute_affinity
from features.forecast import forecast_demand
from evaluation.route_cost import total_route_cost
from evaluation.audit import count_capacity_violations
from or_experts.policies import EXPERT_IDS, StateView, run_policy


@dataclass
class PeriodResult:
    t: int
    phase: str
    costs: Dict[str, float]           # expert -> total period cost
    picks: Dict[str, float]
    moves: Dict[str, int]
    myopic_winner: str
    layout_after: Dict[str, str]


@dataclass
class BenchmarkResult:
    periods: List[PeriodResult]
    total_by_expert_alone: Dict[str, float]   # "always-X" cumulative cost
    myopic_total: float
    fixed_best: str
    fixed_best_total: float
    violations: List[str] = field(default_factory=list)


class SequentialBenchmark:
    def __init__(self, sku_master, locations, xyz, orders, lines, seq: List[DayParams],
                 anchor: datetime, mc_unit_ratio: float = 0.0005,
                 lambda_move: float = 1.0, lambda_switch: float = 0.0):
        self.sku_master = sku_master
        self.sku_ids = [s.sku_id for s in sku_master]
        self.locations = locations
        self.xyz = xyz
        self.orders = orders
        self.lines = lines
        self.seq = seq
        self.anchor = anchor
        self.mc_unit_ratio = mc_unit_ratio   # unit move cost as share of mean period pick cost
        self.lambda_move = lambda_move
        self.lambda_switch = lambda_switch
        # day -> lines index (single pass; the naive nested loop was O(orders*lines))
        order_day = {o.order_id: int((o.order_time - anchor).days) for o in orders}
        self._lines_by_day: Dict[int, List[OrderLine]] = {}
        for ln in lines:
            self._lines_by_day.setdefault(order_day.get(ln.order_id, 0), []).append(ln)
        self._order_day = {o.order_id: float((o.order_time - anchor).days)
                           for o in orders}

    # -- helpers ---------------------------------------------------------------

    def _period_lines(self, lo: int, hi: int) -> List[OrderLine]:
        out = []
        for d in range(lo, hi):
            out.extend(self._lines_by_day.get(d, []))
        return out

    def _hist_lines(self, upto: int) -> List[OrderLine]:
        return self._period_lines(0, upto)

    # -- main roll -------------------------------------------------------------

    def run(self, seed_for_view: int = 0, log=None) -> BenchmarkResult:
        # phases from the sequence (contiguous equal-phase day runs)
        phases: List[Tuple[str, int, int]] = []
        for dp in self.seq:
            if phases and phases[-1][0] == dp.phase:
                phases[-1] = (dp.phase, phases[-1][1], dp.day + 1)
            else:
                phases.append((dp.phase, dp.day, dp.day + 1))

        n_loc = len(self.locations)
        results: List[PeriodResult] = []
        violations: List[str] = []

        # cold-start incumbent: E1's layout after the FIRST phase (that phase
        # is the warehouse's history — myopic path starts from its ABC layout)
        first_phase_end = phases[0][2]
        cold_hist = self._hist_lines(first_phase_end)
        cold_view = self._view(0, first_phase_end, cold_hist, self.seq[0], seed_for_view)
        current = run_policy("E1_StaticABC", cold_view, {}, 0.0).layout

        cum_alone: Dict[str, float] = {e: 0.0 for e in EXPERT_IDS}
        prev_winner: Optional[str] = None
        myopic_total = 0.0

        for t, (phase, lo, hi) in enumerate(phases[1:], start=1):
            # phase 0 is warm-up ONLY: its orders built the incumbent layout,
            # evaluating on them too would be self-referential leakage
            period_lines = self._period_lines(lo, hi)
            hist = self._hist_lines(lo)
            dp = self.seq[lo]
            view = self._view(lo, hi, hist, dp, seed_for_view)

            # unit move cost calibrated on this period's scale, scaled by the
            # REGIME multiplier (v1.2 R6 — review W2: this was not wired, so
            # move-cost-shock phases didn't actually raise relocation cost)
            ref = total_route_cost(period_lines, current, self.xyz) or 1.0
            mc_unit = self.mc_unit_ratio * ref * dp.move_cost_scale

            costs, picks, moves, layouts = {}, {}, {}, {}
            for e in EXPERT_IDS:
                dec = run_policy(e, view, current, mc_unit)
                viol = count_capacity_violations(dec.layout, n_loc)
                if viol:
                    violations.append(f"t={t} {e}: {len(viol)} capacity violations")
                pick = total_route_cost(period_lines, dec.layout, self.xyz)
                mv = dec.n_moves
                switch = 1.0 if (prev_winner is not None and e != prev_winner) else 0.0
                costs[e] = pick + self.lambda_move * mv * mc_unit \
                    + self.lambda_switch * switch * mc_unit
                picks[e], moves[e], layouts[e] = pick, mv, dec.layout
                cum_alone[e] += costs[e]

            winner = min(costs, key=costs.get)
            myopic_total += costs[winner]
            current = layouts[winner]
            prev_winner = winner
            results.append(PeriodResult(t=t, phase=phase, costs=costs, picks=picks,
                                        moves=moves, myopic_winner=winner,
                                        layout_after=current))
            if log:
                log(f"  t={t} {phase:16s} winner={winner:12s} "
                    + " ".join(f"{e.split('_')[0]}={costs[e]/ref:.3f}" for e in EXPERT_IDS))

        fixed_best = min(cum_alone, key=cum_alone.get)
        return BenchmarkResult(periods=results, total_by_expert_alone=cum_alone,
                               myopic_total=myopic_total, fixed_best=fixed_best,
                               fixed_best_total=cum_alone[fixed_best],
                               violations=violations)

    # -- state view ------------------------------------------------------------

    def _view(self, lo: int, hi: int, hist: List[OrderLine], dp: DayParams,
              seed: int) -> StateView:
        span = float(max(1, lo))
        fc = forecast_demand(
            self.sku_ids, hist, future_days=hi - lo, history_days=span,
            history_time_span_days=span,
            line_day={oid: d for oid, d in self._order_day.items()},
            promotion=dp.promo_mult, noise_sigma=dp.forecast_noise, seed=seed)
        aff = compute_affinity(hist, line_day=self._order_day,
                               history_time_span_days=span)
        return StateView(sku_ids=self.sku_ids, sku_master=self.sku_master,
                         locations=self.locations, xyz=self.xyz,
                         hist_lines=hist, hist_line_day=self._order_day,
                         hist_span_days=span, fc=fc,
                         fc_known_promo=dp.promo_mult, aff=aff,
                         move_cost_scale=dp.move_cost_scale)
