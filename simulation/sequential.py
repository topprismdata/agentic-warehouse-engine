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

# experts whose LAYOUT output does not depend on the incoming layout
# (beam search caches these per period; E6/E7 are layout-dependent)
LAYOUT_INDEPENDENT = ["E1_StaticABC", "E2_COI", "E3_Affinity",
                      "E4_Forecast", "E5_Robust"]


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

    # -- myopic rollout (shared preparation with beam search) ------------------

    @dataclass
    class PeriodPlan:
        t: int
        phase: str
        lo: int
        hi: int
        view: StateView
        period_lines: List[OrderLine]
        mc_unit: float          # trajectory-INDEPENDENT (anchored on cold layout)

    def _phases(self) -> List[Tuple[str, int, int]]:
        phases: List[Tuple[str, int, int]] = []
        for dp in self.seq:
            if phases and phases[-1][0] == dp.phase:
                phases[-1] = (dp.phase, phases[-1][1], dp.day + 1)
            else:
                phases.append((dp.phase, dp.day, dp.day + 1))
        return phases

    def _prepare_periods(self, seed_for_view: int):
        """Pre-compute views + move-cost units for all evaluated periods.

        mc_unit is anchored on the COLD-START layout's pick cost per period —
        NOT on the myopic path's current layout. Anchor-independence is what
        makes beam candidates comparable (caliber change vs R10's path-anchored
        mc_unit; R11 reruns myopic under the anchored caliber so both numbers
        come from ONE benchmark instance)."""
        phases = self._phases()
        first_phase_end = phases[0][2]
        cold_hist = self._hist_lines(first_phase_end)
        cold_view = self._view(0, first_phase_end, cold_hist, self.seq[0], seed_for_view)
        cold_layout = run_policy("E1_StaticABC", cold_view, {}, 0.0).layout

        plans = []
        for t, (phase, lo, hi) in enumerate(phases[1:], start=1):
            # phase 0 is warm-up ONLY (built the incumbent; evaluating on it
            # would be self-referential leakage)
            period_lines = self._period_lines(lo, hi)
            hist = self._hist_lines(lo)
            dp = self.seq[lo]
            view = self._view(lo, hi, hist, dp, seed_for_view)
            ref = total_route_cost(period_lines, cold_layout, self.xyz) or 1.0
            mc_unit = self.mc_unit_ratio * ref * dp.move_cost_scale
            plans.append(self.PeriodPlan(t=t, phase=phase, lo=lo, hi=hi,
                                         view=view, period_lines=period_lines,
                                         mc_unit=mc_unit))
        return cold_layout, plans

    def _eval_expert(self, plan, expert_id: str, current: Dict[str, str],
                     prev_expert: Optional[str],
                     layout_cache: Optional[Dict[str, Dict[str, str]]]):
        """Single (period, expert, incoming-layout) evaluation.
        Single accounting authority for myopic AND beam."""
        if layout_cache is not None and expert_id in layout_cache:
            layout = layout_cache[expert_id]
        else:
            layout = run_policy(expert_id, plan.view, current, plan.mc_unit).layout
        pick = total_route_cost(plan.period_lines, layout, self.xyz)
        n_moves = sum(1 for s in layout if current.get(s) != layout[s])
        switch = 1.0 if (prev_expert is not None and expert_id != prev_expert) else 0.0
        cost = (pick + self.lambda_move * n_moves * plan.mc_unit
                + self.lambda_switch * switch * plan.mc_unit)
        return cost, layout, n_moves

    def run(self, seed_for_view: int = 0, log=None) -> BenchmarkResult:
        current, plans = self._prepare_periods(seed_for_view)
        n_loc = len(self.locations)
        results: List[PeriodResult] = []
        violations: List[str] = []
        cum_alone: Dict[str, float] = {e: 0.0 for e in EXPERT_IDS}
        prev_winner: Optional[str] = None
        myopic_total = 0.0

        for plan in plans:
            cache = {e: run_policy(e, plan.view, current, plan.mc_unit).layout
                     for e in LAYOUT_INDEPENDENT}
            costs, picks, moves, layouts = {}, {}, {}, {}
            for e in EXPERT_IDS:
                cost, layout, mv = self._eval_expert(plan, e, current, prev_winner, cache)
                viol = count_capacity_violations(layout, n_loc)
                if viol:
                    violations.append(f"t={plan.t} {e}: {len(viol)} capacity violations")
                costs[e] = cost
                picks[e] = total_route_cost(plan.period_lines, layout, self.xyz)
                moves[e], layouts[e] = mv, layout
                cum_alone[e] += cost

            winner = min(costs, key=costs.get)
            myopic_total += costs[winner]
            current = layouts[winner]
            prev_winner = winner
            results.append(PeriodResult(t=plan.t, phase=plan.phase, costs=costs,
                                        picks=picks, moves=moves,
                                        myopic_winner=winner,
                                        layout_after=current))
            if log:
                ref = max(costs.values())
                log(f"  t={plan.t} {plan.phase:16s} winner={winner:12s} "
                    + " ".join(f"{e.split('_')[0]}={costs[e]/ref:.3f}"
                                for e in EXPERT_IDS))

        fixed_best = min(cum_alone, key=cum_alone.get)
        return BenchmarkResult(periods=results, total_by_expert_alone=cum_alone,
                               myopic_total=myopic_total, fixed_best=fixed_best,
                               fixed_best_total=cum_alone[fixed_best],
                               violations=violations)

    # -- dynamic oracle via beam search (T1) ------------------------------------

    @dataclass
    class BeamResult:
        total_cost: float
        trajectory: List[str]
        per_period: List[dict] = field(default_factory=list)
        beam_width: int = 0

    def beam_search(self, beam_width: int = 30, seed_for_view: int = 0,
                    log=None) -> "SequentialBenchmark.BeamResult":
        """Approximate DYNAMIC ORACLE: beam over expert trajectories with full
        path-dependent rollout.

        The MYOPIC trajectory is injected as a guaranteed incumbent at every
        level (it may otherwise be pruned), so beam-best ≤ myopic-total holds
        EXACTLY. Since both are feasible trajectories, (myopic − beam) is a
        CONSERVATIVE LOWER BOUND on the true dynamic-oracle gap: finding
        beam < myopic by x% proves the oracle gap ≥ x%. A null result is
        beam-limited, not proof of no gap (width sensitivity reported).
        """
        current, plans = self._prepare_periods(seed_for_view)
        cands = [(0.0, (), current, None)]  # (cum, traj, layout, prev_expert)
        # myopic incumbent (same evaluation authority as run())
        my_layout = current
        my_prev: Optional[str] = None
        my_cum = 0.0
        my_traj: List[str] = []

        for plan in plans:
            cache = {e: run_policy(e, plan.view, current, plan.mc_unit).layout
                     for e in LAYOUT_INDEPENDENT}
            # advance the myopic incumbent one step
            my_costs = {e: self._eval_expert(plan, e, my_layout, my_prev, cache)[0]
                        for e in EXPERT_IDS}
            my_e = min(my_costs, key=my_costs.get)
            cost_m, my_layout, _ = self._eval_expert(plan, my_e, my_layout, my_prev, cache)
            my_cum += cost_m
            my_traj.append(my_e)
            my_prev = my_e

            new_cands = []
            for cum, traj, layout, prev in cands:
                for e in EXPERT_IDS:
                    cost, lay, mv = self._eval_expert(plan, e, layout, prev, cache)
                    new_cands.append((cum + cost, traj + (e,), lay, e))
            # guarantee the incumbent survives pruning
            new_cands.append((my_cum, tuple(my_traj), my_layout, my_prev))
            # dedup on trajectory (incumbent may duplicate a beam candidate)
            seen = {}
            for c in new_cands:
                if c[1] not in seen or c[0] < seen[c[1]][0]:
                    seen[c[1]] = c
            cands = sorted(seen.values(), key=lambda c: c[0])[:beam_width]
            if log:
                log(f"  beam t={plan.t} {plan.phase:16s} best={cands[0][0]:.0f}")

        total, traj, _, _ = min(cands, key=lambda c: c[0])
        # replay winner for per-period records (deterministic — assert equality)
        layout = current
        prev = None
        records = []
        cum_check = 0.0
        for plan, e in zip(plans, traj):
            cache = {x: run_policy(x, plan.view, layout, plan.mc_unit).layout
                     for x in LAYOUT_INDEPENDENT}
            cost, layout, mv = self._eval_expert(plan, e, layout, prev, cache)
            cum_check += cost
            records.append({"t": plan.t, "phase": plan.phase, "expert": e,
                            "cost": cost, "moves": mv})
            prev = e
        assert abs(cum_check - total) < 1e-6, f"beam replay mismatch {cum_check} vs {total}"
        assert total <= my_cum + 1e-9, f"beam {total} > myopic {my_cum} — incumbent injection failed"
        return self.BeamResult(total_cost=total, trajectory=list(traj),
                               per_period=records, beam_width=beam_width)

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
