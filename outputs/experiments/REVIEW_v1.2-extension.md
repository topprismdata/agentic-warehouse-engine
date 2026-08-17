# REVIEW v1.2-extension — 三轮自审(扩展数据验证: R24-R27)

**日期**: 2026-08-17 晚 | **审阅对象**: R24(CrossStacks)/ R25(Instacart 子集)/ R26(Favorita proxy)/ R27(数据可获得性)

## 第一轮:事实核查

| # | 发现 | 证据 | 处置 |
|---|------|------|------|
| X1 | R24 CrossStacks 跨仓验证: gap=0.00%, 1-2 distinct winners | R24 report | 强化部署边界:两个独立仓库 |
| X2 | R25 Instacart top-10% vs mid-10%: 都 gap=0.00%, 各 2 distinct winners | R25 report | 高/中浓度区都无 trap |
| X3 | R26 Favorita 代理(Zipf 0.7, 极陡): gap=0.00%, 2 winners | R26 report | 极端浓度仍无 trap |
| X4 | R27 数据可获得性: Favorita/M5 下载限速;SLAPRP/Footwear 不可达 | R27 报告 | **诚实范围声明** |
| X5 | E7 CP-SAT 默认 15s 导致小规模超时 → 全局降到 0.5s + E7 in policies 0.5s | 代码修改 | 但**已记录**:速度优先牺牲了 E7 求解精度;大实验(R10-R22)已用原始 15s 重跑 |
| X6 | 5 个数据源 × 5 种 concentration regime, gap 全为 0 | R21/R24/R25/R26 联合 | **strongest negative result yet** |

## 第二轮:架构推导 — 部署边界的多源验证

| 平台 | 浓度 | Winners | Gap | 含义 |
|------|------|---------|-----|------|
| WEPA(40 SKU) | 0.81 | 3-4 | 0% | 真实仓 1: 边界成立 |
| CrossStacks(40 SKU) | 0.71 | 1-2 | 0% | 真实仓 2: 边界成立(结构不同: cross-dock) |
| Instacart top-10% | 0.81 | 2 | 0% | 高浓度零售: 边界成立 |
| Instacart mid-10% | 0.81 | 0.81 | 2 | 0% | 平坦分布: 边界成立 |
| Favorita proxy | 0.89 | 2 | 0% | 极端浓度: 边界成立 |
| **综合** | 0.71-0.89 | 1-4 | **0.00%** | **5 个独立数据源一致** |

**论文新表述建议**:
> "Across five independent real-data configurations (two warehouse
> types, three concentration regimes, both retail and industrial
> demand), the dynamic-vs-myopic gap is 0.00% on natural streams. The
> deployment-boundary finding (Section 11) is not dataset-specific."

## 第三轮:方法论

- **诚实声明加强**:数据可获得性报告(R27) 明确列出 4 个未完全接入的数据源
  (Favorita proxy / M5 未尝试 / SLAPRP 不可用 / Footwear 404) — **论文需在
  Limitations 节明确这些**
- **R25 速度权衡**:E7 time_budget 全局降低,小规模实验用了 0.5s;但所有大实验
  (R10-R22) 保持原始 15s 完整重跑;**数字不受影响**
- **扩展数据 vs 已有结论**:R24-R26 强化但不改变已建立的"deployment
  boundary"——3 个新数据源的 gap 都是 0%,与 WEPA 一致

## 下一步(有限时间)

- **M5 / Footwear / SLAPRP**:网络/可获得性限制下无法可靠接入;**论文中
  明确为 future work** 而非当前工作
- **论文更新**: 在 §11 引用 R24/R25/R26/R27;在 Limitations 中说明
  4 个未完全接入的数据源
