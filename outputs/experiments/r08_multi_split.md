# R08 — multi-split variance: is B4's edge real? (REVIEW v0.4 #1)

**Date**: 2026-08-16T10:05:11.296417+00:00 | splits = [42, 101, 202, 303, 404] | users = 3000 | top SKUs = 120 | pickers = 3

## Per-split detail

- seed 42: conc=0.2302, train 24658/eval 10884 orders, B4 L0=0.9115, B3 L0=0.9803
- seed 101: conc=0.2285, train 25609/eval 11445 orders, B4 L0=0.9305, B3 L0=0.9781
- seed 202: conc=0.2253, train 24626/eval 10898 orders, B4 L0=0.9342, B3 L0=1.0153
- seed 303: conc=0.2308, train 26135/eval 10592 orders, B4 L0=0.9479, B3 L0=1.0109
- seed 404: conc=0.2208, train 26483/eval 10528 orders, B4 L0=0.9020, B3 L0=0.9812

## Aggregate (5 splits)

| Expert | L0 norm (mean ± std) | L1 norm (mean ± std) | B4 wins L0 | B4 wins L1 |
|--------|----------------------|----------------------|------------|------------|
| B1_StaticABC | 1.0000 ± 0.0000 | 1.0000 ± 0.0000 | 5/5 |5/5 |
| B2_COI | 1.0702 ± 0.0268 | 1.2183 ± 0.1005 | 5/5 |5/5 |
| B3_Affinity | 0.9932 ± 0.0183 | 0.9506 ± 0.0572 | 5/5 |5/5 |
| B4_CPSAT(l=0) | 0.9252 ± 0.0184 | 0.8021 ± 0.0401 | —/5 |—/5 |
| B0 Random (mean of means) | 1.1979 | 1.6426 | — | — |

- observed concentration across splits: min=0.2208 max=0.2308 mean=0.2271

## Gates
- B4 beats B3 on EVERY split, both metrics: **PASS**
- B4 beats B1 on every split: **PASS**
- B0 worst on every split: **PASS**
- validate (split 0, non-vacuous): **PASS**

## Verdict
- **B4 CP-SAT's edge is STABLE across 5 independent user splits** (mean L0 0.9252 ± 0.0184, L1 0.8021 ± 0.0401).
- R07's single-split numbers were representative; the ranking B4 > B3 > B1 may now be cited with variance attached.
