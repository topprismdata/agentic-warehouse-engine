"""
evaluation/compute_normalized_cost.py — Spec §16.3 primary metric.

Spec anchor: §3.2 (Cost Model), §16.3 (NormalizedCost = Cost_Model / Cost_StaticABC).

v0.1 implementation notes:
  - Cost_Model reduces to C_pick only (α=1, β..ζ=0 per `cost_weights.yaml`).
  - C_pick is approximated by "Total route distance × quantity" under Euclidean
    warehouse geometry. This is a known proxy: sim-grade replay (Todo #11) will
    swap this for actual picker-route time. Until then, *relative* comparisons
    between experts on the same world_state are valid; absolute numbers are not.
  - We compute by replaying order_lines chronologically.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple, List
import math

from world_state.schemas import OrderLine, Location


@dataclass
class CostComponents:
    pick_distance_total: float      # v0.1's sole active component
    replenishment_count: int = 0    # stub (Todo #11 enables real counting)
    relocation_count: int = 0       # stub (spec §12.5 enables real counting)
    congestion_units: float = 0.0   # stub (spec §3.2 δ)
    risk_units: float = 0.0         # stub (spec §3.2 ε FEFO/etc.)
    service_units: float = 0.0      # stub (spec §3.2 ζ)

    def to_dict(self) -> Dict[str, float]:
        return {
            "pick_distance_total": self.pick_distance_total,
            "replenishment_count": float(self.replenishment_count),
            "relocation_count": float(self.relocation_count),
            "congestion_units": self.congestion_units,
            "risk_units": self.risk_units,
            "service_units": self.service_units,
        }


def compute_components(
    order_lines: List[OrderLine],
    sku_to_loc: Dict[str, str],
    xyz_lookup: Dict[str, Tuple[float, float, float]],
) -> CostComponents:
    """Sum of `distance_from_entrance * quantity`, all per pick line."""
    entrance = (0.0, 0.0, 0.0)
    total = 0.0
    for line in order_lines:
        loc = sku_to_loc.get(line.sku_id)
        if not loc:
            continue
        x, y, z = xyz_lookup.get(loc, entrance)
        d = math.sqrt(x * x + y * y + z * z)
        total += d * float(line.quantity)
    return CostComponents(pick_distance_total=float(total))


def apply_weights(components: CostComponents, weights: Dict[str, float]) -> float:
    """Apply §3.2 cost model: α·C_pick + β·C_replenish + γ·C_relocate +
    δ·C_congestion + ε·C_risk + ζ·C_service.

    Component units differ (distance vs counts vs scores); weights are presumed
    to have been calibrated by `cost_calibration.md` to give the right scale.
    """
    return (
        weights.get("alpha_pick", 1.0) * components.pick_distance_total
        + weights.get("beta_replenish", 0.0) * components.replenishment_count
        + weights.get("gamma_relocate", 0.0) * components.relocation_count
        + weights.get("delta_congestion", 0.0) * components.congestion_units
        + weights.get("epsilon_risk", 0.0) * components.risk_units
        + weights.get("zeta_service", 0.0) * components.service_units
    )


def normalized_cost(cost: float, baseline_cost: float) -> float:
    if baseline_cost <= 0.0:
        return float("nan")
    return cost / baseline_cost
