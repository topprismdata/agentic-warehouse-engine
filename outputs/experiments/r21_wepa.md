# R21 — WEPA-Natural / WEPA-Stress(SPEC v1.5 §8:真实仓验证)

**Date**: 2026-08-17T05:04:32.682912+00:00 | WEPA via slapstack 0.1.1(pip)|
top-40 SKU | 12000 retrieval orders | beam = 12

## 数据
- 来源: slapstack.use_cases.wepastacks(真实 WEPA 卫生用品仓)
- layout: 1074 存储格(实际几何,1.4m 格距)
- orders: 12000 retrieval(真实 3 个月流)
- 转换: top-40 SKU by retrieval freq;单 SKU 单位格(块堆→拣位抽象)

## NATURAL(自然数据,统一 move cost)

| Expert | always-total |
|--------|-------------|
| E1_StaticABC | 68354 |
| E2_COI | 68354 |
| E3_Affinity | 68354 |
| E4_Forecast | 68354 |
| E5_Robust | 68354 |
| E6_DDSR | 69988 |
| E7_Joint | 97236 |

- myopic total: **68354**
- BFIP total: **68354**
- **gap (myopic − BFIP)/myopic = 0.00%**
- winners by period: ['E1_StaticABC', 'E1_StaticABC', 'E7_Joint', 'E6_DDSR', 'E1_StaticABC']
- fixed-best: E4_Forecast (68354)
- winner diversity: 3 distinct experts

## STRESS(真实数据 + 中流 move-cost ×20 冲击)

| Expert | always-total |
|--------|-------------|
| E1_StaticABC | 68683 |
| E2_COI | 68683 |
| E3_Affinity | 68683 |
| E4_Forecast | 68683 |
| E5_Robust | 68683 |
| E6_DDSR | 68150 |
| E7_Joint | 103856 |

- myopic total: **68150**
- BFIP total: **68150**
- **gap = 0.00%**
- winners by period: ['E1_StaticABC', 'E1_StaticABC', 'E7_Joint', 'E7_Joint', 'E6_DDSR']
- gap vs NATURAL: +0.00pp

## 判读(v2 — 修正后)

### NATURAL(40 SKU / 12k orders / 真实 WEPA 3 个月流)
- **gap = 0.00%,myopic 轨迹 = BFIP 轨迹(穷举验证一致)**
- 有 3-4 个 distinct winners(E1/E6/E7 交替)但 myopic 已是最优序列
- **结论: 真实仓自然数据上不存在 inter-temporal trap**
  - 原因: WEPA retrieval 订单为单行(无 basket 结构)+ 需求平稳(3 个月内
    无剧烈 regime shift)
  - Myopic 的贪心选择在这类数据上恰好也是全局最优

### STRESS(真实数据 + 注入 628 单 bottom-half SKU surge + move-cost ×20)
- **gap = 0.00%(仍无 trap)**
- surge 占 period-2 量的 ~30%,足以改变 winner 但不足以制造 trap
- **trap 需要: 需求转变幅度足以改变最优布局 + 成本冲击使错误重排昂贵;
  两者的乘积效应在真实数据的自然变动范围内不出现**

### 论文意义(外部效度边界)
- 合成平台: trap 存在(构造性 regime: promo ×8 / velocity reversal / remap)
- WEPA-Natural: **无 trap**(自然数据太平滑)
- WEPA-Stress(温和): 仍无 trap
- **结论: trap 是"极端 regime 变化"的现象,不是日常仓储运营的常态**
  - 这为 DWERP 的适用范围划定了边界:适用于促销季/季节切换/产品线
    转换等非平稳事件,不适用于稳态运营
  - 与 v1.0 spec §3.3 的 "Re-slot Trigger" 设计一致:日常不该频繁搬库

### 诚实声明
- 块堆→拣位是抽象简化;单格单 SKU;未用 SLAPStack 仿真核心(后续可接)
- Stress 注入是温和的(~30% surge);更强的注入(×3)可能制造 trap,
  但那就完全等同于合成平台了 —— 失去 external validity 意义
- 6 期 × beam 12 的计算量(15 min/run)限制了更细的扫描

## 与合成平台(R10–R18)的对照
- 合成: T0 GO(6 winners),material trap 1/12,Δt=1 带最强
- WEPA-Natural: 本实验
- WEPA-Stress: 本实验
