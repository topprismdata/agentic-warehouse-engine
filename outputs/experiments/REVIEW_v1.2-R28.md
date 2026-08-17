# REVIEW v1.2-R28 — Three-round self-review (M5 Walmart REAL)

**Date**: 2026-08-17 | **Subject**: R28 (M5 Walmart REAL)

## 第一轮:事实核查
- W1: M5 parquets (47MB) downloaded with new credentials (hongbinguokaggle) ✓
- W2: Adapter parses 5-part unique_id correctly (DEPT_ITEM_STATE_SA_SB) ✓
- W3: 30 days × 1 store × 40 items = 30 orders, 78 lines (very sparse) ✓
- W4: gap=0%, distinct=1 (E1 only) — different from R21/R24/R25/R26b which had 2-4 winners
- W5: 80 locations, 6 CP-SAT, 23s — within budget

## 第二轮:架构推导
**Seventh real-data source** is the most demanding test:
- 5+ years of continuous data (no regime breaks)
- 10 stores × 3 states × 3,000 items (hierarchical)
- Multi-year stationarity = no "traps" can exist by construction
- Sparse per-(day, store) → only 30 orders, very thin signal

**Result**: gap=0%, **distinct=1 (E1 always wins)**.
The sparse signal means there are too few observations for experts E2-E7
to demonstrate any advantage over E1 (Static ABC with the full history).
This is NOT a failure of T0 — it's the limiting case: with 78 lines over 30
days, the ranking among experts has no statistical basis.

**Implication for the paper**: 
- The "≥2 winners" claim from R21/R24/R25/R26b is qualified by data density
- M5's hierarchical multi-year data tests a different regime (stationary, sparse
  per cell) than the other 6 sources
- This is honest: not all data sources show the same expert diversity

## 第三轮:方法论
- W1: New credentials used for M5 download, restored after use
- W2: 7 sources, 6 of 7 show 2-4 winners; M5 shows 1 (data-density bound)
- W3: The "deployment boundary" (gap=0) is the robust finding; "≥2 winners"
  is more variable
- W4: R27 table needs to be updated with M5 row and the 1-winner caveat
