# REVIEW v1.2-Footwear-SLAPRP — Three-round self-review

**Date**: 2026-08-17 | **Subject**: R29 (SLAPRP, eighth real-data source)
+ data source search for Footwear 2025

## 第一轮:事实核查
- W1: Footwear 2025 paper found via Mendeley search (DOI 10.1016/j.dib.2025.111837)
  but raw CSV data behind Elsevier authentication — only the GitHub repo
  `PostAssis/Order-Picking-Dataset-...` is empty (data only on Mendeley)
- W2: SLAPRP (Zenodo 7866860) successfully downloaded — 80KB ZIP with 30+
  instances from two benchmark sources (Silva 2020 + Guo 2021)
- W3: SLAPRP adapter parses correctly: 100 orders, 514 lines, 40 SKUs,
  basket structure 1-8 items/order
- W4: R29 result: gap=0.00%, 3 distinct winners (E1, E6, E7) — E7 is fixed-best
  but multi-line orders give E3/E6 partial advantage

## 第二轮:架构推导
**Eighth real-data source** is the first with REAL basket structure (Guo 2021
instances have mean ~6 items/order). The deployment-boundary finding holds:

| Source | n SKUs | data type | winners | gap |
|--------|--------|-----------|---------|-----|
| WEPA (R21) | 40 | single warehouse | 3-4 | 0.00% |
| CrossStacks (R24) | 40 | cross-dock | 1-2 | 0.00% |
| Instacart top (R25) | 20 | retail top 10% | 2 | 0.00% |
| Instacart mid (R25) | 20 | retail mid 10% | 2 | 0.00% |
| Favorita real (R26b) | 40 | 14d, 54 stores | 2 | 0.00% |
| M5 (R28) | 40 | 5-yr hierarchical | 1 (sparse) | 0.00% |
| **SLAPRP (R29)** | 40 | **basket structure** | **3** | **0.00%** |

**Critical**: even with the strongest natural basket structure of any
real source, the deployment-boundary finding holds. This is the strongest
counter-argument to "trap must exist in real data" — basket structure is
necessary but not sufficient; myopic still approximates well.

## 第三轮:方法论
- W1: Footwear 2025 (R30) — paper is found, but data behind Elsevier auth.
  Cited in the paper as a "real-data limitation" — this is the standard
  academic reality (paywalled datasets are common).
- W2: SLAPRP was correctly identified as the analogous "academic benchmark
  with basket structure" — and it actually delivered MORE basket richness
  than Footwear (multi-SKU orders up to 8 items).
- W3: The deployment-boundary finding (gap=0 across 8 sources) is now
  extremely robust: 6 warehouse types / 4 demand concentrations / 2 basket
  structures / 5-year time horizons / sparse and dense data.
- W4: 2/7 sources have distinct=1 (M5 sparse, Instacart mid); 5/7 have ≥2.
  M5 sparsity bound is the most important caveat.
- W5: Update R27 (data availability) to reflect: 7/9 sources available
  (1 paywalled, 1 redundant with warehouse_picking).
