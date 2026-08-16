# REVIEW v1.4 — 三轮自审(SPEC v1.4 落地 + T1.5/T3/T4 完成后)

**日期**: 2026-08-16(深夜)| **审阅对象**: R14(T1.5)/ R15(T3 信息边界)/ R16(T4 trap phase diagram)
**规则**: 每次更新对完成结果自审 3 次,再决定下一步。

---

## 第一轮:事实核查(取证)

| # | 发现 | 证据 | 处置 |
|---|------|------|------|
| Y1 | **beam oracle 非可采纳**:宽 20 的 oracle 在 seed 17 给 38106,竟高于 greedyFC 的 36444 —— 有限宽度会剪掉后期才显优的轨迹;beam 只保证 ≤ myopic,不保证 ≤ 一切可行策略 | R15 首跑(width 20)vs R11(width 30 = 36070) | **已修**:R15 统一 width 30 重跑,排序恢复(oracle ≤ greedyFC 全 seeds ✓);制度化:oracle 宽度是**全仓声明常量**,任何实验报告须注明;R11–R13 的 gap 是"相对 myopic 的下界"仍然成立,capture 分母才需要强 oracle |
| Y2 | **CaptureRate ≈ 0%**:aware 均值 −0.2%(3 seeds 正、2 seeds 负、7 seeds 零),blind 12/12 全 0(与 greedy 轨迹全同) | R15 表 | 如实报告;绑定约束 = **内部成本模型保真度**(线性 Σp50×dist 无 route/stop 结构,专家错排序),不是日程知识 |
| Y3 | **seed 17 反讽**:greedyFC(36444)< 事后 myopic(38106)—— 预测模型的"懒惰"= 隐式 stickiness,部分规避了 trap | R15 明细 | 论文素材:模型失配作为隐式正则(连向 hysteresis/robustness 文献) |
| Y4 | **Hidden Reconfig 17–69% vs False Switch 0%**;且 switch-only(λs=20)下 dynamic 的 hidden-reconfig 升到 69% —— 策略学会"换内容不换名"来规避指示罚 | R14 表 | **Methodology result 成立**:"algorithm-switch count is an inadequate surrogate";d(L_t,L_{t+1}) 公式化有硬证据 |
| Y5 | **Trap 带非单调**:峰在 Δt=1(全 M material 1.26–1.69%),Δt=0 除 M=20 外不 material,Δt≥2 衰减;my_trans_moves=0(myopic 转变期不动),伤害 = shock 期被迫调整(my 67 vs dy 35 @Δt=1,M=2) | R16 网格 + moves 表 | 如实报告"中间导程带";Δt=0 反常(2 seeds,噪声可能)标注 open |
| Y6 | R15 seed 67 分母≈0 → NaN capture | R15 | 报告保留 NaN,不硬凑 |

## 第二轮:架构推导 —— 叙事重心迁移

1. **论文主线现已完整成形为三层**:
   - 机会存在(T1a:oracle gap 5.34% 构造性证据;T4:trap 带可控复现)
   - **朴素可部署策略捕获 ≈ 0(T3)**→ 真正的研究前沿 = 内部模型保真度 + option-value 机制
   - 代理失真(T1.5:名字 ≠ 物理重配置)
2. **"When NOT to reconfigure"获得两个新支点**:Y3(懒惰即正则)与 R16(dynamic 在
   廉价期预置、shock 期只搬最关键的)—— 与 R13 的 plateau 机制互证
3. T3 的零捕获**不是失败而是定位**:它把 Selector 的工作从"分类专家"精确化为
   "预测 Ĉ(E_i|S_t) 的成本感知排序 + 转变期的 option-value hold"—— SPEC §7 的
   cost-sensitive 框架因此有了直接动机
4. 未完成(如实):SPEC v1.4 §6 的 VPM / Marginal Move Quality 未实现(记入下一步)

## 第三轮:方法论

- **Y1 教训制度化**:近似 oracle 的"保证"必须写清边界(≤ myopic ≠ ≤ optimum);
  跨实验的求解器参数(beam 宽度/时间)须声明一致
- 负结果的报告格式(capture 表含 NaN、aware 的正负混合)保持,不取绝对值美化
- R16 的 2-seed 网格是**扫描**不是**推断**;结论表述用"带"不用"边界",补 seeds
  前不做定量拟合
- cache JSON 模式已在 R13/R16 复用,增量加固成本 ~可接受

## 下一步(三轮后决定)

1. **Anticipatory v2(直接冲着 capture≈0 去)**:内部成本模型升级为 stop-count
   感知(订单级 route 近似),H ∈ {1,2,3} 扫描,schedule-aware/blind 双档;
   目标 = 把 aware capture 从 ~0 提到正区间(哪怕 20–30%)—— 这是 Selector 前
   最后一块可部署性证据
2. **VPM / Marginal Move Quality**(SPEC §6 欠账)+ R16 补 seeds
3. **WEPA-Natural / WEPA-Stress** 双层验证(数据可达性调研先行)
4. Selector(cost-sensitive Ĉ 预测)最后
