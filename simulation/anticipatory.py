"""
simulation/anticipatory.py — SPEC v1.4 §1: deployable sequential policy.

Receding-horizon anticipatory routing: at each period t, beam over the next
H periods using the agent's INTERNAL forecast cost model (linear
sum_s p50_s * dist(loc_s) — NOT the realized route cost), pick the first
action of the best candidate, apply it, account the REALIZED cost via the
benchmark's single accounting authority, roll forward.

Information regimes (schedule_aware):
  True  — future move-cost schedule is legitimately knowable (tariff/labor
          calendars); lookahead uses each period's true mc_unit.
  False — surprise shocks: lookahead assumes the CURRENT period's mc persists.

Also provides deployable greedy (H=1, forecast-driven) — what a warehouse
could run today without any lookahead.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from or_experts.policies import EXPERT_IDS, LAYOUT_INDEPENDENT, run_policy


def forecast_pick_cost(view, layout: Dict[str, str]) -> float:
    """Agent's internal cost model: expected pick distance under p50 forecast.
    Deliberately simpler than the realized route metric (deployable agents do
    not get TSP-exact evaluations; model mismatch is part of the question)."""
    total = 0.0
    for s, d in view.fc.items():
        loc = layout.get(s)
        if loc is None:
            continue
        x, y, z = view.xyz[loc]
        total += d.p50 * math.sqrt(x * x + y * y + z * z)
    return total


@dataclass
class AnticipatoryResult:
    total_cost: float                # realized, single accounting authority
    trajectory: List[str]
    per_period: List[dict] = field(default_factory=list)


def anticipatory_rollout(bench, H: int = 2, beam_width: int = 8,
                         schedule_aware: bool = True,
                         seed_for_view: int = 0, log=None) -> AnticipatoryResult:
    current, plans = bench._prepare_periods(seed_for_view)
    layout = current
    prev: Optional[str] = None
    total = 0.0
    traj: List[str] = []
    records: List[dict] = []

    for i, plan in enumerate(plans):
        window = plans[i:i + H]
        # beam over forecast costs in the lookahead window
        cands = [(0.0, (), layout, prev)]
        for w_i, wplan in enumerate(window):
            if schedule_aware or w_i == 0:
                mc = wplan.mc_unit
            else:
                mc = plan.mc_unit  # blind: assume current move cost persists
            new = []
            for cum, tr, lay, prv in cands:
                for e in EXPERT_IDS:
                    fl = run_policy(e, wplan.view, lay, mc).layout
                    mv = sum(1 for s in fl if lay.get(s) != fl[s])
                    sw = 1.0 if (prv is not None and e != prv) else 0.0
                    fc = (forecast_pick_cost(wplan.view, fl)
                          + bench.lambda_move * mv * mc
                          + bench.lambda_switch * sw * mc)
                    new.append((cum + fc, tr + (e,), fl, e))
            new.sort(key=lambda c: c[0])
            cands = new[:beam_width]
        best_e = cands[0][1][0]

        # apply with REALIZED accounting (the benchmark's authority)
        cost, layout, mv = bench._eval_expert(plan, best_e, layout, prev, None)
        total += cost
        traj.append(best_e)
        records.append({"t": plan.t, "phase": plan.phase, "expert": best_e,
                        "cost": cost, "moves": mv})
        prev = best_e
        if log:
            log(f"  anticipatory t={plan.t} {plan.phase:16s} -> {best_e}")

    return AnticipatoryResult(total_cost=total, trajectory=traj, per_period=records)


def deployable_greedy(bench, seed_for_view: int = 0) -> AnticipatoryResult:
    """H=1 forecast-greedy: the realistic no-lookahead baseline."""
    return anticipatory_rollout(bench, H=1, beam_width=8,
                                schedule_aware=True,
                                seed_for_view=seed_for_view)
