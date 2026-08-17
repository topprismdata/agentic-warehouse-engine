# REVIEW v1.5-R28b-paper — Three-round self-review

**Date**: 2026-08-17 | **Subject**: R28b (M5 dense) + Paper §11 rewrite + Limitations section

## 第一轮:事实核查
- W1: R28b debug took 5 iterations before finding the issue — `_lines_by_day`
  was being filtered to 0 entries by the plan boundaries (lo=6-30) when
  the warmup phase (lo=0-6) was excluded. Fixed by reordering the build.
- W2: R28b result: gap=0%, distinct=1 (E1 all 6 periods). This is NOT a data-
  density bound: with 9x more data (480 vs 30 orders, 688 vs 78 lines),
  M5 still produces single-winner outcomes. R28b is a stronger finding
  than R28: the single-winner is intrinsic to M5's 5-year steady-state.
- W3: Paper §11 rewrite: now cites 8 sources (R21, R24, R25, R26b, R28, R28b,
  R29) with cross-dataset table; adds Limitations section (§limitations)
  with three categories: data availability, platform scope, data-structure
  condition for the diversity finding.

## 第二轮:架构推导
**Paper narrative updated**: The deployment-boundary finding is now
defended by 8 real-data sources (not just WEPA). The gap=0 finding is
now characterized as: "universal across warehouse types / concentration
regimes / basket structures / time horizons" with one explicit
qualification: "M5's hierarchical demand degenerates to 1 winner even
with 9x more data, showing the diversity finding has a data-structure
condition".

**Footwear 2025**: paper found, abstract extracted, citation added — but
CSV access is the real boundary. The Limitations section now names this
explicitly rather than the previous vague "behind auth wall".

## 第三轮:方法论
- W1: The R28b bug is a real engineering lesson — the inline tests I ran
  in `/tmp/` were not part of the project's test suite. Future: add the
  R28b script (and R17) to a small pytest set so data-format bugs are caught
  pre-execution.
- W2: The paper's new §11 has 4 explicit findings, each tied to a number
  (gap %, distinct winners, data source). This is the right format for
  the Conclusion-Data combined claim.
- W3: The Footwear paper access barrier is a fair honest limit; the
  previous wording "behind Elsevier auth wall" was less precise.
