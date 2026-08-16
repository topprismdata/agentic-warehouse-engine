# REVIEW v1.5-R17 — 三轮自审(R17 归因实验完成后)

**日期**: 2026-08-17 凌晨 | **审阅对象**: R17(内部成本模型 × H × schedule 归因)
**规则**: 每次更新对完成结果自审 3 次,再决定下一步。

---

## 第一轮:事实核查(取证)

| # | 发现 | 证据 | 处置 |
|---|------|------|------|
| Z1 | **R17 与 R15 的"capture"不是同一指标**:R17 分母基准 = ex-post myopic(clairvoyant 逐期贪心);R15 分母 = greedyFC(deployable H=1 forecast-greedy)。seed 17 上 R17 报 +81.6% 而 R15 报 0% —— 因为 RHC(36444)= greedyFC(36444)≠ myopic(38106) | 两脚本 capture 公式对比 + seed 17 三方数字 | **必须在报告中显式声明两种 capture 的语义差异**;R17 的数值不能与 R15 直接比较 |
| Z2 | **三层成本结构(seed 17)**:myopic=38106 ≫ RHC=greedyFC=36444 > BFIP=36070。myopic 陷阱受害者;RHC/greedyFC 的"懒惰"反而是保护(不做错误过度优化);**真 clairvoyance premium ≈ 374/36444 ≈ 1.0%** | R17 cache + R15 报告 | 论文核心图素材:三层分解 |
| Z3 | **内部模型保真度不是绑定约束**:L1(crudest)+43.4% ≥ L3(route-aware)+24.6% > L2(stop-aware,不稳定)。模型的"精度"与 capture **非单调** —— L1 的保守性(不看到 stop 收益→少搬)恰是 trap 规避机制 | R17 表:L1>L3>L2 | 推翻 v1.4 假设"内部模型保真度是绑定约束";修正为"**保守偏置(即少动)是 trap 规避的机制,模型精度反而不重要**" |
| Z4 | **H 几乎无效**:H=1 vs H=7 在大多数配置下给出相同轨迹/成本 | R17 表同行比较 | lookahead 深度不是杠杆;trap 规避来自"不作为"而非"深谋远虑" |
| Z5 | **schedule aware vs blind 差异小**(L1/L3 几乎无差;L2 aware H≥2 略好) | R17 表 | 与 Z4 一致:前瞻信息几乎不改变决策 |
| Z6 | seed 37/97 分母 <1% 被门控为 NaN;均值由 seed 17(+81.6%)和 117(+5.2%)驱动 | cache 逐 seed | 分布不均,均值需带 per-seed 明细 |

## 第二轮:架构推导 —— 归因结论修正

**v1.4 假设**:"capture≈0 因为内部成本模型太粗糙(线性 Σp50×dist 无 stop 结构)"
**R17 证据**:模型升级(L1→L3)不提升 capture;H 增大不提升;schedule 知情不提升。

**修正后的机制故事**:
1. **Trap 的受害者是 ex-post myopic**(信息完美但短视的贪心)—— 它在转变期
   做出局部最优但全局错误的重排
2. **任何 forecast 驱动的保守策略都自动规避大部分 trap** —— 因为预测误差/
   模型粗糙天然抑制过度重排(懒惰 = 隐式 stickiness = 隐式 robustness)
3. **真 clairvoyance premium 很小(~1%)** —— 需要精确知道 shock 时点才能
   拿到的边际价值;这 ~1% 才是"完美预知"的上限
4. **论文叙事调整**:DWERP 的可部署价值不在于"捕获 clairvoyant 机会",
   而在于**证明保守策略已是最优可部署策略**(在没有完美预测时)—— 这本身
   是一个强结论,与 online optimization 的 competitive-ratio 精神一致

## 第三轮:方法论

- **指标定义纪律**:两个"capture"必须显式命名区分 —— `CaptureVsMyopic`(R17)
  与 `CaptureVsGreedy`(R15);以后所有 capture 值必须带分母定义
- **Z3 的教训**:假设"更好的模型 → 更好的决策"在这里**方向都错了**;
  在 switching-cost 环境中,模型误差的方向(保守 vs 激进)比精度更重要
- R17 的 H 无效应与 R15 的 blind 无效应互证:前瞻不是杠杆,杠杆在
  "动作偏好"(move vs hold)
- 聚合时 per-seed 明细必给(Z6);均值不带分布是误导

## R17 最终判读(供论文)

- **RankingFidelity 假设被否定**:ρ(L1)=0.73-0.88 高但 capture 与 ρ 不单调;
  ρ(L2)=0.48 低但 seed 17 capture 也高 —— **排序保真度不是捕获的必要条件**
- **新假设(待验)**:capture 由"策略的动作偏好谱系"决定 —— 越保守越好
  (在 trap 存在时);激进模型(看到更多优化机会)反而更接近 myopic 的失败模式
- 连接 MTS 理论:这恰好是 MTS 文献中 "work function" 与 "lazy" 策略的
  经典权衡 —— 我们的实验为仓储域提供了实证
