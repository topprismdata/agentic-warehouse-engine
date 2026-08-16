"""
world_state/validate.py — Anti-leakage and lineage checks for canonical schemas.

Spec anchor: §4.3 (no future leakage), §8.4 principle 8 (data lineage), §10.4
(hard constraint graph), §15.4 (decision record).

`validate_pipeline()` returns a `ValidationReport` and either raises
`ValidationError` on hard failure or returns the report for soft diagnostics.

These checks mirror `cultivating-ml-agent/framework/pipeline/validate.py`
behavior — fail fast, log clearly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Dict, Any, Set

from .schemas import (
    SkuMaster, Order, OrderLine, Location,
    InventorySnapshot, SlotAssignment, Constraint,
    DecisionPlan, ForecastDaily,
    SourceType,
    required_tables,
)


# -------------------------------------------------------------------------
# Error type
# -------------------------------------------------------------------------

class ValidationError(RuntimeError):
    """Raised on any hard-fail check; soft-warn checks populate report only."""


@dataclass
class ValidationReport:
    hard_failures: List[str] = field(default_factory=list)
    soft_warnings: List[str] = field(default_factory=list)
    tables_seen: Set[str] = field(default_factory=set)
    record_counts: Dict[str, int] = field(default_factory=dict)

    def is_clean(self) -> bool:
        return not self.hard_failures

    def summary(self) -> str:
        return (
            f"tables={sorted(self.tables_seen)} "
            f"records={self.record_counts} "
            f"hard_fails={len(self.hard_failures)} "
            f"warnings={len(self.soft_warnings)}"
        )


# -------------------------------------------------------------------------
# Schema-level validators
# -------------------------------------------------------------------------

def _awareness_check(dt: datetime, label: str, report: ValidationReport):
    if dt.tzinfo is None:
        report.hard_failures.append(
            f"{label} is tz-naive; world_state requires tz-aware datetimes (spec §8.4)"
        )


def _check_orders(orders: List[Order], report: ValidationReport):
    for o in orders:
        # §4.3 known_at_time present
        if o.known_at_time is None:
            report.hard_failures.append(f"order {o.order_id}: known_at_time is None")
            continue
        _awareness_check(o.known_at_time, f"order {o.order_id}.known_at_time", report)
        _awareness_check(o.order_time, f"order {o.order_id}.order_time", report)
        # anti-future-leakage
        if o.known_at_time > o.order_time:
            report.hard_failures.append(
                f"order {o.order_id}: known_at_time ({o.known_at_time.isoformat()}) "
                f"> order_time ({(o.order_time or datetime.min).isoformat()})"
            )


def _check_lineage(items, label: str, report: ValidationReport):
    for it in items:
        if it.source_type is None:
            report.hard_failures.append(f"{label} id={getattr(it, 'sku_id', None) or getattr(it, 'order_id', None)}: source_type is None")


def _check_constraints(cs: List[Constraint], report: ValidationReport):
    """rule_version must look like semver ('vMAJOR.MINOR[.PATCH]'). spec §10.4."""
    import re
    pat = re.compile(r"^v\d+\.\d+(\.\d+)?$")
    for c in cs:
        if not pat.match(c.rule_version or ""):
            report.hard_failures.append(
                f"constraint {c.constraint_id}: rule_version '{c.rule_version}' "
                f"is not semver"
            )


def _check_decision_plans(plans: List[DecisionPlan], report: ValidationReport):
    for p in plans:
        if p.lineage != SourceType.DERIVED:
            report.hard_failures.append(
                f"decision_plan {p.decision_id}: lineage must be DERIVED, got {p.lineage}"
            )
        if not (0.0 <= p.confidence <= 1.0):
            report.hard_failures.append(
                f"decision_plan {p.decision_id}: confidence {p.confidence} ∉ [0,1]"
            )


# -------------------------------------------------------------------------
# Public API
# -------------------------------------------------------------------------

def validate_pipeline(world_state: Dict[str, List[Any]]) -> ValidationReport:
    """`world_state` is a dict of table_name -> List[rows]. Returns a report;
    raises ValidationError if any hard failure occurred.
    """
    report = ValidationReport()

    # Coverage check — all 9 canonical tables present (even if empty list)
    seen_tables = set(world_state.keys())
    for required in required_tables():
        if required not in world_state:
            report.hard_failures.append(f"required table missing: {required}")
        report.tables_seen.add(required)
        report.record_counts[required] = len(world_state.get(required) or [])

    if "orders" in world_state:
        _check_orders(world_state["orders"], report)
    if "constraints" in world_state:
        _check_constraints(world_state["constraints"], report)
    if "decision_plan" in world_state:
        _check_decision_plans(world_state["decision_plan"], report)

    # lineage completeness (soft unless missing in ANY row)
    for tbl in [
        "sku_master", "order_lines", "forecast_daily",
        "locations", "inventory_snapshot", "slot_assignment",
    ]:
        rows = world_state.get(tbl) or []
        if rows:
            _check_lineage(rows, tbl, report)

    # No-future-orders-in-past-window soft warning (sample data follows this rule;
    #    if user passes real-world orders with offset, we surface a hint)
    if "orders" in world_state:
        anchor = datetime(2025, 1, 1, tzinfo=timezone.utc)
        for o in world_state["orders"]:
            if o.order_time < anchor:
                report.soft_warnings.append(
                    f"order {o.order_id}: order_time predates canonical anchor 2025-01-01"
                )
                break

    if report.hard_failures:
        raise ValidationError(
            "validation hard-fail: " + " | ".join(report.hard_failures)
        )
    return report
