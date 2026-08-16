# R05 — honest evaluation: time-split + capacity-fair (supersedes R02-R04 rankings)

**Date**: 2026-08-16T09:45:19.426728+00:00 | seed = 42 | split@day7 | pickers = 3

## Protocol fixes (v0.2 three-round review)
- **F1 leakage**: experts slot on days 1-7 ONLY; evaluation replays days 8-14. No clairvoyant slotting (spec §4.3, §16.1).
- **F2 fairness**: capacity = ceil(n/L) audited per expert — the same hard constraint CP-SAT obeys (spec §10.4). B3 now splits clusters instead of overflowing.
- **F6 gates**: validate_pipeline runs on a world WITH assignments + decision plans (R02-R04 validated an empty world).

## Results (both metrics on FUTURE orders only; B1 slotted-on-history anchor = 1.0)

| Expert | L0 norm (honest) | L1 norm (honest) | capacity violations |
|--------|------------------|------------------|---------------------|
| B1_StaticABC | 1.0000 | 1.0000 | 0 |
| B2_COI | 0.9707 | 0.9852 | 0 |
| B3_Affinity | 0.8442 | 0.9189 | 0 |
| B4_CPSAT(l=0) | 0.8089 | 0.9056 | 0 |
| B0 Random (5 seeds) | 1.6686 | 1.2893 | 0 |

## The headline correction (B3's three numbers)
- R02 reported: **0.4527** (capacity-violating + clairvoyant — invalid)
- capacity-fixed, still clairvoyant (full 14 d used for both): **0.7136**
- honest (slot on 1-7, replay 8-14): **0.8442**
- leakage correction: **-0.1306**

## Gates
- zero capacity violations (all experts incl. B0): **PASS**
- B0 worst on both L0 and L1 (all seeds): **PASS**
- validate_pipeline clean (non-vacuous, 600 assignments + 5 plans): **PASS**
- L0/L1 ranking consistency: **PRESERVED** (L0: ['B4_CPSAT(l=0)', 'B3_Affinity', 'B2_COI', 'B1_StaticABC'] / L1: ['B4_CPSAT(l=0)', 'B3_Affinity', 'B2_COI', 'B1_StaticABC'])

## Interpretation
- These numbers **supersede R02-R04** for any ranking claim.
- Gap compression vs in-sample is expected: affinity from 7 days is noisier, and B3 lost its illegal >capacity co-locations.
- Whatever the honest ranking is, it is the first number in this repo that would survive the spec's own §4.3 replay discipline.
