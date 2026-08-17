# Paper Skeleton — When Not to Reconfigure

**Status**: v1.0 draft skeleton | **Date**: 2026-08-17
**Mapping**: 每节标注支撑实验/图/表;数字以 `outputs/experiments/` 为准

---

## Title

**When Not to Reconfigure: Sequential Expert Routing for Dynamic Warehouse
Slotting under Non-Stationary Demand**

*(with Physical Reconfiguration Costs)*

中文: 何时不应重配置:非平稳需求下考虑物理重配置成本的仓储动态专家路由

## Abstract (draft)

Dynamic slotting in FMCG warehouses is typically optimized per-period or over
short rolling horizons, treating each decision as independent. We show that
this myopic approach can be globally suboptimal when physical reconfiguration
costs create inter-temporal coupling: a locally beneficial re-slot made before
a cost shock can lock the warehouse into expensive adjustments. We formalize
this as the Dynamic Warehouse Expert Routing Problem (DWERP), a
warehouse-specific instance of switching-cost online optimization (MTS/SOCO)
where a set of OR experts propose slotting actions and the decision is which
expert to follow each period. Through controlled experiments on a synthetic
platform validated against exact enumeration, we characterize the conditions
under which myopic expert selection fails — finding that traps concentrate at
intermediate lead times before cost shocks, and that the full-information
opportunity is modest (~1–5%) but real. Counter-intuitively, we find that
deployable receding-horizon policies with crude internal cost models capture
most of this opportunity not by predicting better, but by being
conservative — their model imprecision acts as implicit stickiness that avoids
over-reconfiguration. We empirically demonstrate that algorithm-switch counts
are an inadequate surrogate for physical warehouse reconfiguration (hidden
reconfiguration rate 17–69%), and that value-per-move, not move frequency, is
the correct selective-reconfiguration metric. On real warehouse data (WEPA,
3 months, 411K orders), no inter-temporal trap manifests under natural
conditions, bounding trap-aware routing to genuinely non-stationary scenarios
such as promotion seasons and product-line transitions.

---

## 1. Introduction

**Core insight**: 当前最优 ≠ 长期最优,when reconfiguration is costly and demand
is non-stationary.

**Story arc**:
- Traditional dynamic slotting optimizes current/rolling instance
- Physical reconfiguration changes future state + costs (transition cost)
- We ask: *when should a warehouse defer a locally beneficial reconfiguration?*

**Evidence anchors**: seed 17 (sac 80 → regret 2116, TrapScore 26.3);
R18 exact (beam=optimal verified); R16 controlled (Δt=1 band).

## 2. Related Work

**Three adjacent literatures (SPEC v1.5 §8)**:

| Stream | Key works | Our position |
|--------|-----------|--------------|
| MTS / SOCO | Borodin et al. 1992; smoothed online optimization; learning-augmented MTS | DWERP = warehouse-specific instance; NOT claiming new sequential-decision theory |
| Warehouse online reoptimization | Lorenz/Otto/Gendreau (reoptimization quality); anticipation & strategic waiting | Their waiting = picker-level; ours = **reconfiguration deferral** (physical state) |
| Dynamic slotting / DSLAP | DRL DSLAP (2022); contextual bandit put-away (2024); future-order repositioning (2026) | None treat stateful reconfiguration × switching cost × deployable capture jointly |

**Novelty (four elements)**: dynamic algorithm selection × stateful warehouse
reconfiguration × physical switching cost × non-stationary FMCG demand.

## 3. Problem Formulation (DWERP)

π(S_t) → E_t → A_t; S_{t+1} = f(S_t, A_t, ξ_{t+1})

min Σ_t [C_op(S_t, A_t) + C_trans(A_{t-1}, A_t)]

- S_t = (Orders, Demand, Forecast, Inventory, Layout L_t, Resources, Constraints)
- E = {E_1..E_7} = OR Expert Library (each a full policy)
- C_trans = d(L_t, L_{t+1}) — physical layout distance, NOT 1[E_t≠E_{t-1}]

**Information regimes**: ex-post BFIP (upper bound) / Receding-Horizon
Warehouse Policy (deployable) / Myopic (greedy baseline)

## 4. Expert Library (v3.1)

| Expert | Behavior | When best |
|--------|----------|-----------|
| E1 Static ABC | full-history frequency ranking | stable demand, high move cost |
| E2 COI | freq/volume | space-constrained |
| E3 Affinity | recency-weighted co-pick | strong basket structure |
| E4 Forecast | informed forecast p50 | promotion (known events) |
| E5 Robust | p50 − κ·spread | high forecast uncertainty |
| E6 DDSR-lite | opportunistic payback-gated | known-order horizon |
| E7 Joint | CP-SAT pick + move penalty | cost-coupled regimes |

## 5. Experimental Environment

- **Synthetic platform** (primary): 120 SKU / 60 locations / 28-day regime
  sequence (8 phases: stable → promo ramp/peak/decay → reversal → affinity
  shift → move-cost shock); deterministic CP-SAT; canonical schema with
  known_at_time / lineage / constraint_version
- **Instacart Track B** (supplementary): real baskets, user-level split
- **WEPA** (external validity): real layout (1074 cells) + 411K orders

**Figure**: Expert Winning Map (`outputs/figures/expert_winning_map.png`)

## 6. Expert Diversity (T0)

**Result**: no single expert dominates (52% top share, 6 distinct winners).
Winners switch with regime phase: promo→E3/E4 family, stable→E1, mc_shock→E7.

**Evidence**: R10 (3 seeds × 7 phases); `outputs/experiments/r10_t0_diversity.md`

## 7. Myopic Failure: The Trap Window

**Definition**: NormalizedTrapGain_t(H) = (C^M_{t:t+H} − C^D_{t:t+H}) / C^M_{t:t+H}
MaterialTrap: NTG > 1%

**Key results**:
- **Existence (T1a)**: constructive evidence (seed 17: sac 80 → regret 2116)
- **Prevalence (T1b)**: insurance-shaped distribution — 10/12 seeds gap≈0,
  1/12 material; divergence concentrates at promo_ramp + stable2 ("eve of
  structural shifts")
- **Causation (controlled, T4)**: trap band at Δt=1 intermediate lead time,
  ALL shock magnitudes material (1.26–1.69%); without shock → zero gap (R18
  exact control)

**Figures**: `trap_phase_diagram.png`; R18 exact table

## 8. The Deployment Paradox

**Finding**: deployable RHC ≈ greedyFC (no better than naive), yet both ≪
ex-post myopic. The clairvoyance premium is only ~1%.

**Mechanism**: forecast imprecision = implicit stickiness = protection.
Model fidelity hypothesis REJECTED: crudest model (L1) captures most (43.4%),
better models (L2/L3) capture less. Conservatism direction > precision.

**Connection to MTS**: this is the classic lazy-vs-aggressive tradeoff —
our experiments provide the warehouse-domain empirical instance.

**Figures**: `rf_capture.png`; R17 table

## 9. Reconfiguration Sensitivity (T2)

**λm → gap curve**: left end low (~0.1%) → mid peak (λm=10: 1.26%) → right
plateau (λm=20-50: 1.0-1.2%, NOT converging to zero)

**Interpretation**: at high move cost, dynamic moves MORE but BETTER
(164 vs 152 at λm=50) — "Not fewer moves, better moves."

**VPM analysis**: VPM_dynamic > VPM_myopic at ALL 7 λm levels, gap widens
monotonically (+0.1 → +5.5). In absolute terms, VPM is negative vs
never-move baseline at high λm → "when NOT to reconfigure" quantified.

**Figures**: `t2_lambda_curves.png`; `vpm_curve.png`

## 10. Transition Cost: An Inadequate Surrogate

**Finding**: algorithm-switch count 1[E_t≠E_{t-1}] fails:
- False Switch (name changed, layout ~same): 0% — no false positives
- **Hidden Reconfiguration (name same, layout massively changed): 17–69%**
  — systematically misses real cost; worsens under high switch penalties
  (policies learn to "change content without changing name")

**Metric properties**: d(L,L) satisfies symmetry + triangle inequality →
valid MTS metric; but 4 warehouse-specific violations (asymmetric costs,
capacity-infeasible transitions, batch effects, swap chains — 663 detected)

**Evidence**: R14, R19

## 11. Real Warehouse Validation

**WEPA-Natural** (40 SKU / 12k orders / real geometry): gap = 0.00%,
myopic trajectory = BFIP = optimal. No natural trap.

**WEPA-Stress** (+30% surge + mc×20): still gap = 0.00%.

**Interpretation**: traps require regime changes beyond normal operational
variation — bounding applicability to promotion seasons, seasonal transitions,
product-line changes.

**Evidence**: R21

## 12. Discussion

1. **When sequential routing matters**: only under genuine non-stationarity
   (promotion/reversal/affinity shift), at intermediate reconfiguration cost
   (λm ~10), with intermediate lead time (Δt ~1)
2. **When it doesn't**: steady-state operations (WEPA-Natural gap=0);
   near-zero move costs (planning unnecessary); extremely high move costs
   (nobody moves, plateau)
3. **The deployment paradox**: conservative policies are self-protecting;
   model fidelity is NOT the binding constraint (R17)
4. **Reconfiguration Deferral** ≠ strategic picker waiting (Lorenz et al.) —
   we defer PHYSICAL state changes, not labor decisions
5. **Practical implication**: WMS vendors should measure d(L,L') not expert
   switches; cost-aware selectors should predict Ĉ(E_i|S_t) not classify

## 13. Conclusion

We formalized, demonstrated, and bounded the inter-temporal trap in dynamic
warehouse slotting. The core insight — "when NOT to reconfigure" — is
quantified as the option value of deferring locally beneficial reconfiguration
under future uncertainty. The deployment paradox (conservatism = protection)
suggests practical systems should err toward stickiness rather than
sophistication.

---

## Appendix: Experiment-to-Section Map

| Paper § | Experiments | Key figures |
|---------|------------|-------------|
| 6 (Diversity) | R10, R12 | expert_winning_map |
| 7 (Trap) | R11, R12, R16, R18 | trap_phase_diagram |
| 8 (Deployment) | R15, R17 | rf_capture |
| 9 (Sensitivity) | R13, R20 | t2_lambda_curves, vpm_curve |
| 10 (Transition) | R14, R19 | — |
| 11 (Real data) | R07, R08, R21 | — |
