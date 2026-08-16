"""
evaluation/audit.py — Hard-constraint audits for expert plans (spec §10.4).

The v0.2 review finding F2 (B3 violating capacity while B4 obeyed it) showed
rankings are meaningless unless every expert faces the identical constraint
set. `count_capacity_violations` is the checker that makes this auditable.
"""

from __future__ import annotations

import math
from collections import Counter
from typing import Dict


def count_capacity_violations(
    sku_to_loc: Dict[str, str],
    n_locations: int,
    location_capacity: int = None,
) -> Dict[str, int]:
    """Return {location_id: load} for locations EXCEEDING capacity.

    Default capacity = ceil(n_sku / n_locations), the same bound B1's
    round-robin and B4's CP-SAT constraint use.
    """
    n_sku = len(sku_to_loc)
    if location_capacity is None:
        location_capacity = max(1, math.ceil(n_sku / max(n_locations, 1)))
    loads = Counter(sku_to_loc.values())
    return {loc: load for loc, load in loads.items() if load > location_capacity}
