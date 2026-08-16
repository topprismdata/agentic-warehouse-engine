"""
execution/gateway.py — Spec §15.4 Execution Gateway (v0.3 stub: dry-run only).

The LAST line of defense between an optimizer's plan and physical motion.
This stub performs every CHEAP check and refuses to execute anything —
"dry_run" emits ExecutionTask records or rejections with reason codes.

Check chain (ordered, fail-fast per action):
  1. SOLVER_STATUS      plan.verifier_status must be 'feasible' (spec §14.2 —
                        an unverified plan is not a plan)
  2. CONSTRAINT_VERSION plan.constraint_version must match the live constraint
                        set's rule_version (stale plans are dangerous)
  3. CAPACITY_VIOLATION hard capacity ceil(n/L) per location (spec §10.4)
  4. RISK_ROUTING       per-action risk class → execution mode (spec §15.2):
                        low → auto | medium → approve_required
                        high → sim + human approval (never auto)
                        safety_critical → BLOCKED, period
  5. NEGATIVE_PAYBACK   MOVE actions must have expected_saving > move_cost
                        (spec §3.3 re-slot trigger: don't move what doesn't pay)

No WMS connection, no DB writes — v0.3 scope is the contract + audit trail.
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from world_state.schemas import DecisionPlan, RiskClass, SourceType
from evaluation.audit import count_capacity_violations


# --- Reason codes (auditable, stable strings) --------------------------------

R_SOLVER_STATUS = "SOLVER_STATUS_NOT_FEASIBLE"
R_CONSTRAINT_VERSION = "CONSTRAINT_VERSION_MISMATCH"
R_CAPACITY = "CAPACITY_VIOLATION"
R_RISK_SAFETY = "SAFETY_CRITICAL_BLOCKED_FOR_LLM"
R_PAYBACK = "NEGATIVE_PAYBACK"
R_MISSING_FIELD = "MISSING_REQUIRED_FIELD"


# --- Records ------------------------------------------------------------------

@dataclass
class ExecutionTask:
    task_id: str
    decision_id: str
    action_type: str            # ASSIGN / MOVE / REPLENISH
    sku_id: str
    to_location: str
    from_location: Optional[str]
    risk_class: RiskClass
    execution_mode: str         # auto / approve_required
    approved_by: Optional[str]  # None until a human signs
    expected_value: float
    move_cost: float
    payback_days: Optional[float]
    model_version: str
    constraint_version: str
    reason: str
    created_at: datetime
    source_type: SourceType = SourceType.DERIVED

    def audit_row(self) -> Dict:
        """The §15.4 mandated provenance tuple for every physical action."""
        return {
            "task_id": self.task_id,
            "decision_id": self.decision_id,
            "model_version": self.model_version,
            "constraint_version": self.constraint_version,
            "expected_value": self.expected_value,
            "approved_by": self.approved_by,
        }


@dataclass
class GatewayVerdict:
    decision_id: str
    accepted: List[ExecutionTask] = field(default_factory=list)
    rejected: List[Dict] = field(default_factory=list)   # {sku, code, detail}

    @property
    def ok(self) -> bool:
        return not self.rejected

    def summary(self) -> str:
        codes = Counter(r["code"] for r in self.rejected)
        return (f"decision={self.decision_id} accepted={len(self.accepted)} "
                f"rejected={len(self.rejected)} {dict(codes) if codes else ''}")


# --- Gateway -------------------------------------------------------------------

@dataclass
class GatewayConfig:
    location_capacity: Optional[int] = None      # default: ceil(n_sku / n_loc)
    auto_max_move_skus: int = 5                  # ≤5 MOVE actions stays medium-risk
    large_reslot_skus: int = 5                   # >5 actions = high risk (spec §15.2)
    require_payback_for_move: bool = True


class ExecutionGateway:
    def __init__(self, config: GatewayConfig = None):
        self.config = config or GatewayConfig()

    # -- risk routing (spec §15.2) --------------------------------------------

    def _risk_of(self, plan: DecisionPlan, n_actions: int) -> RiskClass:
        # safety_critical never originates from slotting plans, but the gateway
        # must still be able to REJECT one if it ever arrives
        if plan.risk_class == RiskClass.SAFETY_CRITICAL:
            return RiskClass.SAFETY_CRITICAL
        if n_actions > self.config.large_reslot_skus:
            return RiskClass.HIGH          # large-scale re-slot
        if plan.risk_class == RiskClass.HIGH:
            return RiskClass.HIGH
        if plan.risk_class == RiskClass.MEDIUM:
            return RiskClass.MEDIUM
        return RiskClass.LOW

    # -- main entry -------------------------------------------------------------

    def dry_run(
        self,
        plan: DecisionPlan,
        live_constraint_version: str,
        n_locations: int,
    ) -> GatewayVerdict:
        v = GatewayVerdict(decision_id=plan.decision_id)

        # 1. solver-verified gate
        if plan.verifier_status != "feasible":
            v.rejected.append({
                "sku": "*", "code": R_SOLVER_STATUS,
                "detail": f"verifier_status={plan.verifier_status!r}; only "
                          f"solver-verified plans may enter execution (spec 14.2)",
            })
            return v

        # 2. constraint-version freshness
        if plan.constraint_version != live_constraint_version:
            v.rejected.append({
                "sku": "*", "code": R_CONSTRAINT_VERSION,
                "detail": f"plan built under {plan.constraint_version!r} but live "
                          f"rules are {live_constraint_version!r}; re-solve required",
            })
            return v

        # 3. hard capacity over the whole plan (location loads from actions)
        sku_to_loc = {}
        for a in plan.actions:
            sku = a.get("sku_id")
            loc = a.get("to_location")
            if sku and loc:
                sku_to_loc[sku] = loc
        viol = count_capacity_violations(
            sku_to_loc, n_locations, self.config.location_capacity
        )
        if viol:
            v.rejected.append({
                "sku": "*", "code": R_CAPACITY,
                "detail": f"{len(viol)} locations over capacity: "
                          f"{dict(list(viol.items())[:5])}...",
            })
            return v

        # 4-5. per-action risk routing + payback
        n_actions = len(plan.actions)
        risk = self._risk_of(plan, n_actions)
        now = datetime.now(timezone.utc)

        if risk == RiskClass.SAFETY_CRITICAL:
            v.rejected.append({
                "sku": "*", "code": R_RISK_SAFETY,
                "detail": "safety-critical control is reserved for deterministic "
                          "controllers; an LLM/optimizer plan can never execute it",
            })
            return v

        for i, a in enumerate(plan.actions):
            sku = a.get("sku_id") or "?"
            action_type = str(a.get("action_type", "ASSIGN")).upper()
            missing = [k for k in ("sku_id", "to_location", "expected_saving")
                       if a.get(k) is None]
            if missing:
                v.rejected.append({"sku": sku, "code": R_MISSING_FIELD,
                                   "detail": f"missing {missing}"})
                continue

            # payback only binds physical re-slotting, not initial ASSIGN
            move_cost = float(a.get("move_cost", 0.0))
            expected_saving = float(a["expected_saving"])
            payback = None
            if action_type == "MOVE" and self.config.require_payback_for_move:
                if expected_saving <= move_cost:
                    v.rejected.append({
                        "sku": sku, "code": R_PAYBACK,
                        "detail": f"saving {expected_saving:.2f} ≤ move cost "
                                  f"{move_cost:.2f} (spec 3.3 trigger)",
                    })
                    continue
                payback = move_cost / expected_saving if expected_saving > 0 else None

            mode = "auto" if risk == RiskClass.LOW else "approve_required"
            v.accepted.append(ExecutionTask(
                task_id=f"T-{plan.decision_id}-{i:04d}",
                decision_id=plan.decision_id,
                action_type=action_type,
                sku_id=sku,
                to_location=a["to_location"],
                from_location=a.get("from_location"),
                risk_class=risk,
                execution_mode=mode,
                approved_by=None,
                expected_value=expected_saving,
                move_cost=move_cost,
                payback_days=payback,
                model_version=plan.model_version,
                constraint_version=plan.constraint_version,
                reason=str(a.get("reason", "")),
                created_at=now,
            ))
        return v
