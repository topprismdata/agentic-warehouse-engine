# REVIEW v1.5 — 三轮自审(夜间独立工作:R17–R20 完成后)

**日期**: 2026-08-17 凌晨 | **审阅对象**: R17(归因)/ R18(exact oracle)/ R19(度量)/ R20(VPM)
**规则**: 每次更新对完成结果自审 3 次,再决定下一步。

---

## 第一轮:事实核查(取证)

| # | 发现 | 证据 | 处置 |
|---|------|------|------|
| Z1 | **两种 capture 的语义差异**(R17 vs R15 分母不同:ex-post myopic vs greedyFC) | 两脚本公式对比 | 已写入 REVIEW_v1.5-R17;以后所有 capture 值须标注分母 |
| Z2 | **R17 归因结论**:模型保真度假设被否定(L1 crudest 反而最好) | R17 表:L1>L3>L2 非单调 | 修正机制解释:保守偏置(而非精度)是保护机制 |
| Z3 | **R18 无 shock 控制完美**:exact=beam=myopic 全 0% gap → trap 纯粹是"转变期决策×成本冲击"的交互 | R18 no-shock 输出 | 控制实验设计获验证;因果链干净 |
| Z4 | **R19 三角不等式在 Hamming 与 Euclidean 上均成立**;663 个 swap 对(真实成本被系统性低估) | 三元组穷举检验 | MTS 连接的形式基础确立 |
| Z5 | **R20 VPM 全为负(vs 零搬库)**;"VPM 随 λm 递增"假设被否定(绝对口径) | R20 cache 全表 | 诚实报告;相对口径(VPM_dy>VPM_my 全 7 档)才是正确表述 |
| Z6 | R17 的 H 无效应 + R20 的 λm 敏感性互证:前瞻深度不是杠杆;动作偏好谱系才是 | 两实验交叉 | 论文 Discussion 素材 |

## 第二轮:架构推导 —— 夜间四实验的统一叙事

R17–R20 合起来给出 DWERP 的**完整机制图景**:

1. **机会的存在性**(R18):exact = beam < myopic(gap 0.46–2.68%);
   无 shock → 无 gap → trap 因果 = 转变决策 × 成本冲击
2. **朴素部署的悖论**(R17):RHC ≈ greedyFC(不比朴素贪心好);但 RHC ≪
   ex-post myopic(预测的"懒惰"反而是保护)→ 真正的 clairvoyance premium
   只有 ~1%
3. **度量的合法性**(R19):d(L,L) 构成合法度量(对称+三角不等式)→ MTS
   理论可挂靠;但 4 类仓储特异性(不对称/硬约束/批量/交换链)构成广义成本
4. **选择性的量化**(R20):VPM_dy > VPM_my 全 7 档且差值随 λm 扩大 →
   "Not fewer moves, better moves" 在相对口径成立;"高成本→最优趋近不搬"
   在绝对口径成立

**论文四层贡献链(最终版)**:
① 机会存在与因果(R18 exact + T4 controlled)→
② 部署悖论(R17:保守 = 保护,naive ≈ optimal deployable)→
③ 度量失真(T1.5 + R19:指示罚 → 物理距离 → 真实劳动)→
④ 选择性重配置(R20:VPM + λm 相图)

## 第三轮:方法论

- **夜间独立工作纪律**:每步先取证再结论;假设被否定时如实报告(R20 的
  "VPM 递增"假设、R17 的"模型保真度"假设)
- R18 的 exhaustive enumeration 是小规模专用工具;大规模仍需 beam(已验证
  beam=exact 于小实例)
- R19 的 swap-pair 计数(663)是代理成本低估的定量证据;论文可展开为
  "swap chain overhead ratio" 的正式分析(记入 future work)
- cache-resume 在 R17/R20 中再次有效(全量 ~80 min → 增量秒级)

## 未完成(如实记录,留给白天)

- SPEC v1.5 §3.4:Trap 相图扫 ShockPersistence × DemandShift(R16 只扫了
  Δt × M;维度可扩但非紧急)
- WEPA-Natural/Stress 数据接入(未开始;需调研可达性)
- Selector 开发(按既定路线,最后)
- R17 报告的 final 版本仍引用了部分中间数据;PROGRESS 更新后统一引用
