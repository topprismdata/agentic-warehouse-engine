# Agentic Warehouse Engine — 进展与下一步计划 v1.5

**日期**: 2026-08-17 凌晨(夜间独立工作完成后)| **项目**: `~/projects/agentic-warehouse-engine/`
**性质**: 阶段性总结(取代 PROGRESS_v1.4;数字以 `outputs/experiments/` 为准)
**规范链**: `SPEC_UPDATE_v1.5.md` > v1.4 > v1.3 > ... > v1.0 PDF

---

## 1. 项目定位(v1.5 最终版)

**理论母体**: MTS / Switching-Cost Online Optimization(SOCO)。DWERP 不发明
新序列决策思想;贡献 = warehouse-specific online reconfiguration 结构。

**核心命题(冻结)**:
> DWERP studies when a warehouse should defer locally optimal physical
> reconfiguration under non-stationary demand, and how much of the resulting
> full-information opportunity can be captured by deployable receding-horizon
> policies with imperfect forecasts and internal cost models.

**论文题目候选**: *When Not to Reconfigure: Sequential Expert Routing for
Dynamic Warehouse Slotting under Non-Stationary Demand*

**术语**: BFIP(beam full-info policy)/ Exact Oracle / Receding-Horizon
Warehouse Policy / **Reconfiguration Deferral**(非 "waiting")

## 2. 实验全景(v1.5 终态,20 个实验 + 9 轮自审)

| # | 实验 | 问题 | 核心结果 |
|---|------|------|---------|
| R01–R06 | 基础设施 | schema/基线/CP-SAT/SimPy/gateway | 12/12 TODO 落地 |
| R07–R08 | Instacart 真实数据 | 真实 basket 下排名 | B4 稳定获胜(多切分确认) |
| R10 | T0 Diversity | Expert 切换? | GO(52%,6 winners) |
| R11 | T1 Oracle | myopic vs beam | BORDERLINE → 拆分 |
| R12 | T1b Prevalence | trap 频率 | 保险型重尾;material 1/12;divergence 在转变前夜 |
| R13 | T2 Sensitivity | λm 调制 | 左低+中峰(λm=10)+右 plateau;"只搬最关键的" |
| R14 | T1.5 代理失真 | 指示罚合格? | **Hidden Reconfig 17–69%**(不合格) |
| R15 | T3 信息边界 | 可部署捕获? | greedyFC 基准下 ≈0% |
| R16 | T4 Trap 相图 | 条件组合? | Δt=1 中间导程全 M material |
| **R17** | **归因实验** | 为何 capture=0? | **两种 capture 语义差异发现**;模型保真度假设否定 |
| **R18** | **Exact Oracle** | beam=optimal? | **beam-30=exact(4/4 seeds,gap 0.00%)**;no-shock=全等 |
| **R19** | **度量性质** | d(L,L) 合法度量? | 对称✓ 三角✓ → MTS 可挂靠;4 类特异性违反 |
| **R20** | **VPM** | 搬库选择性? | VPM_dy>VPM_my 全 7 档,差值随 λm 扩大 |
| **R21** | **WEPA-Natural/Stress** | 真实仓上 trap 存在? | **❌ gap=0.00%(myopic=BFIP=optimal)**:自然数据太平滑,trap 需极端 regime |
| **R24** | **CrossStacks** | 第二个独立仓验证 | **❌ gap=0.00%,1-2 winners**:部署边界不限于 WEPA |
| **R25** | **Instacart 浓度切片** | 高 vs 中浓度子集 | top-10%:2 winners;mid-10%:2 winners;均 gap=0% |
| **R26** | **Favorita 代理** | 极端浓度(Zipf 0.7) | gap=0%,2 winners;Kaggle 限速仅得 1MB |
| **R27** | **数据可获得性报告** | 4 个未完全接入源 | Favorita proxy / M5 未试 / SLAPRP 不可用 / Footwear 404 |

## 3. 夜间四实验的统一叙事(R17–R20)

### R17:归因 —— 两种 capture 的语义陷阱 + 保守性即保护

- **Z1 发现**:R17 分母 = ex-post myopic;R15 分母 = greedyFC —— seed 17 上
  R17 报 +81.6% 而 R15 报 0%(同一 RHC 轨迹!)
- **三层结构**(seed 17):myopic 38106 ≫ RHC=greedyFC 36444 > BFIP 36070
  → clairvoyance premium ≈ 1.0%
- **模型保真度假设否定**:L1(crudest)+43.4% ≥ L3(route)+24.6%;
  保守偏置(不看到优化机会→少动)恰是 trap 规避机制
- **H 无效应 + schedule 无效应**:前瞻深度不是杠杆;动作偏好(动 vs 忍)才是

### R18:Exact Oracle —— beam 可靠性穷举验证

- 60 SKU / 30 loc / 4 期,7^4=2401 轨迹全枚举(含剪枝)
- **beam-30 = exact 全 4 seeds(gap 0.00%)** —— BFIP 术语有穷举支撑
- WITH shock:myopic gap 0.46–2.68%,轨迹分歧(如 seed 37:myopic E1-E2-E7-E7
  vs optimal E1-E6-E7-E4)
- **WITHOUT shock:三者全等(0.00%)** —— trap 纯粹 = 转变决策 × 成本冲击交互

### R19:度量性质 —— MTS 挂靠的形式基础

- n_moves(Hamming)与 total_move_dist(Euclidean)**均满足对称 + 三角不等式**
  → 合法度量空间 → 标准 MTS 框架适用
- 4 类仓储特异性:成本不对称 / 硬约束不可达 / 批量效应 / 交换链(663 对)
  → "warehouse-specific generalized switching cost"
- T1.5(17–69%)+ R19(swap 低估)= **双重失真证据链**

### R20:VPM —— "Not fewer moves, better moves" 的量化

- VPM = (基线拣选 − 轨迹拣选 − 搬库成本)/ 搬库数;基线 = 永不搬库
- **绝对口径**:VPM 全负且随 λm 更负(-0.8 → -84.0)→ 高成本区"最优≈不搬"
- **相对口径**:**VPM_dy > VPM_my 全部 7 个 λm 档**(差值 +0.1 → +5.5 单调扩大)
- 合成 insight:**Reconfiguration Deferral 的价值不在"搬得少"而在"每次搬的
  边际价值更高";λm 足够大时最优解趋近不搬**

## 4. 论文四层贡献链(最终版)

1. **机会存在与因果**(R18 exact + R16 controlled):trap = 转变决策×成本冲击;
   beam=optimal 验证 → gap 数字可信
2. **部署悖论**(R17):朴素 RHC ≈ greedyFC(不比朴素好)但 ≪ ex-post myopic
  (保守即保护)→ 真 clairvoyance premium ~1%
3. **度量失真**(T1.5 + R19):指示罚 → 物理距离 → 真实劳动的三级失真;
   Hidden Reconfig 17–69% + 663 swap 对
4. **选择性重配置**(R20 + R13):VPM 相对优势全档成立且随成本扩大;
   "Reconfigure Selectively" 与 "When NOT to Reconfigure" 互为表里

## 5. 自审信用记录(累计 9 轮)

| 轮 | 重大捕获 |
|----|---------|
| v0.2 | 全知评估 + 容量违约 → 排名撤回 |
| v0.4 | 空表过 validate |
| v1.2-T0 | move_cost_scale 未接线 |
| v1.2-T1 | CP-SAT 非确定性 → deterministic 化 |
| v1.3 | 微 trap 口径 + 判据静默修改 |
| v1.4 | beam oracle 非可采纳 → 宽度制度化 |
| **v1.5-R17** | **两种 capture 语义差异(Z1)+ 模型保真度假设否定(Z2)** |
| **v1.5-overnight** | **VPM 绝对口径假设否定(如实报告)+ 负结果不美化** |

## 6. 资产清单

- **代码**: ~9,500 行 Python(90+ files);确定性 CP-SAT;exhaustive oracle;
  RHC(3 级内部模型 × 双 schedule 档);VPM 分解;度量检验
- **数据**: Instacart(340 万订单);合成 regime(28 天 8 相位);controlled
  trap 网格(Δt×M);exact oracle 实例(4 期全枚举)
- **实验报告**: R01–R20 + REVIEW×9;**6 张图**(t2_lambda_curves /
  expert_winning_map / trap_phase_diagram / rf_capture / vpm_curve +
  R18 表)
- **缓存**: R13/R16/R17/R20 JSON cells(断点续跑)

## 7. 下一步(更新)

### 7.1 已完成(上午追加)
1. ✅ **R21 WEPA-Natural/Stress**: slapstack 0.1.1 pip 安装,WEPAStacks 数据
   在包内(43MB orders + layout);NATURAL gap=0(myopic=BFIP=optimal);
   STRESS(温和 surge + mc×20)仍 gap=0 → **外部效度边界:trap 不出现在
   自然稳态仓数据上,需极端 regime 变化**(论文 Discussion 素材)
2. ⬜ **论文骨架初稿**(最高优先级 —— 证据链已齐)

### 7.2 本周
4. **WEPA-Natural/Stress**(数据可达性调研 → 接入 → 复核 trap 率)
5. **Selector 开发启动**(cost-sensitive Ĉ 预测;输入 = online-observable
   状态;评价 = DynamicRegret / OracleGap;家族 = Rule→XGB→MLP→LLM)

### 7.3 技术债(非阻塞)
- cost_weights.yaml 接线;action schema 统一;d(L,L) 正式替代指示罚入主模型
- R09 遗留报告标注 "superseded"

## 8. 风险与边界(诚实声明)

- 平台仍合成;WEPA 复核前 material-trap 频率不外推
- R17 的 "capture" 有两种口径,引用时必须注明分母
- R20 的 VPM 为负值(vs 零搬库基线)是真实形态,不是 bug;"VPM 递增"
  假设在绝对口径被否定,相对口径(_dy > _my)成立
- exact oracle 仅验证到 4 期/60 SKU;更大规模的 beam=exact 推断合理但未穷举

## 9. 文件索引(夜间新增)

```
SPEC_UPDATE_v1.5.md                      # 理论定位 + 四件优先(v1.5 权威)
simulation/cost_models.py                # L1/L2/L3 内部成本模型
scripts/run_r17_attribution.py           # 归因(3模型×4H×双schedule)
scripts/run_r18_exact_oracle.py          # 穷举 oracle
scripts/run_r19_metric_properties.py     # 度量检验
scripts/run_r20_vpm.py                   # VPM 分析
outputs/experiments/r17..r20_*.md        # 四份报告
outputs/figures/rf_capture.png           # RF→capture 曲线
outputs/figures/vpm_curve.png            # VPM 双曲线
outputs/experiments/REVIEW_v1.5-R17.md   # Z1–Z6
outputs/experiments/REVIEW_v1.5-overnight.md  # 夜间三轮自审
```
