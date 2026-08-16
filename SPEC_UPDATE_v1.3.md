# SPEC UPDATE v1.3 — T1 裁决与机制研究转向(强制,基于导师 2026-08-16 反馈)

**效力**: 本文件 > SPEC_UPDATE_v1.2 > v1.1 > v1.0。v1.2 的 DWERP 定义、Expert
Library v3.1、三重验证继续有效;本文件修订 **判据、分析对象与路线顺序**。

---

## 1. T1 拆分为 T1a / T1b(判据变更)

**废除判据**:"全 seeds gap ≥2% 才 GO"(与研究问题不一致,过强)。

- **T1a Existence(已完成,YES)**: 是否存在 myopic 被 dynamic 严格支配的状态序列?
  seed 17 构成 constructive evidence:dynamic 在 affinity_shift 接受 +1.6% 当期损失,
  避免 mc_shock 期 55→5 moves,全局省 5.34%。
- **T1b Prevalence(本轮,R12)**: trap 在多少 regime/seeds/参数下出现?
  报告 **gap 分布形态**(而非均值门槛)+ trap window 频率 + P(trap|phase)。

科学立场:DWERP 的价值可能是 **event-dependent**(类似保险:70% 时间无差异,
10% 出现严重 over-reslotting)—— 若如此,研究价值仍成立,且更有意思。

## 2. 新分析对象:Trap Window(冻结定义)

某时间窗口 W_t,若 myopic 的局部最优动作导致未来累计重配置成本显著上升:

```
TrapScore_t = (C_future^myopic − C_future^dynamic) / (C_t^dynamic − C_t^myopic)
              └── future regret ──┘                  └── current sacrifice ─┘
```

- TrapScore_t > τ(默认 τ=2.0)→ 存在 inter-temporal optimization opportunity
- 实现口径:从 myopic/dynamic 轨迹**首个分叉点**计算;current sacrifice ≤ 0
  且 future regret > 0 记为 "free win"(非 trap,单列)
- 研究问题从"平均 gap 多少"升级为:**什么状态条件产生 myopic failure(Trap 概率)?**

## 3. T2 升级为核心机制实验(R13)

λm sweep 扩为 **{0, 0.25, 0.5, 1, 2, 5, 10, 20}**(连续曲线),产出三张图:
1. λm → Moves(总重配置量)
2. λm → Expert Switches
3. **λm → Dynamic-vs-Myopic Gap**(最重要)

**假设(inverted-U)**: 存在 λm* —— λm < λm* 时 move 近乎免费(Dynamic≈Myopic);
λm ≈ λm* 时长期规划价值最大;λm ≫ λm* 时人人不搬,gap 再度收敛。
若成立,结论为:"sequential routing 的价值在重配置成本**既不可忽略又未高到禁止调整**
的中间区域最大" —— 这比"提升 5.34%"强得多。

**实验卫生**: sweep 序列**去掉 move_cost_shock 相位**(move_cost_scale 恒 1),
由全局 λm 单独控制 —— 否则相位 ×20 与全局 λm 交互混杂,曲线不可解释。声明于报告。

## 4. 新增 T1.5:C_move vs C_switch 必须拆分

- **C_move(物理重配置)**: 搬托盘/重设 pick face/叉车/补货调整
- **C_switch(策略切换)**: planning policy 更改/人员认知/参数重配置/WMS 更新/运营稳定性
- T2 三种条件分别跑: move-only / switch-only / both
- **长期方向(声明,不在本轮实现)**: transition penalty 应落在 d(A_t, A_{t-1})
  (物理 action 距离)而非 1[E_t≠E_{t-1}](策略名)—— "两个 Expert 输出相同 layout
  但名字变了,物理上无成本"。DWERP 公式随之升级为 **π(S_t, A_{t-1}) → E_t**。

## 5. Expert Winning Map(核心图,R12/R13 产出)

横轴 Demand Shift(promo 强度/phase 类型)× 纵轴 λm(Move Cost),每格标 modal
winner。证明"不存在全局 dominant Expert"的一张图,胜过十页实验表。

## 6. 路线顺序修订(导师裁决)

```
当前: T1a/T1b + T2
  → Expert Phase Diagram / Trap Analysis   (验证 f(S_t)→E* 有可学习结构)
  → WEPA / SLAPStack                        (真实几何复核)
  → Selector(Rule/XGB/MLP/LLM)             (最后)
```

理由:Selector 开发前必须先确认 winner 是否随机 seed noise;若 pattern 稳定
(high move cost→E7, stable→E1, promotion→E4/E6)才值得 supervised selector。

## 7. 核心研究命题(提升)

**"When NOT to reconfigure"** —— 真正困难的不是"什么时候换更聪明的算法",
而是**什么时候忍住不做眼前看似正确的优化**。Trap Analysis 是其操作化。

## 8. 论文骨架(存档,§7 详细结构见 PROGRESS 附录)

Intro → Research Gap(stateful sequential expert routing with endogenous
state transition + reconfiguration cost)→ DWERP Formulation(π(S_t,A_{t-1}))
→ Expert Library → Environment(Synthetic→Instacart→WEPA, lineage/leakage
control 是 credibility point)→ E0 Diversity → **Myopic Failure(Trap Window,
seed 17 为 illustrative example)** → Dynamic Oracle(beam)→ **Reconfiguration
Sensitivity(λm,λs)** → Learned Selector(靠后)→ Discussion(什么时候 sequential
有价值,什么时候没有)。

## 9. 禁止事项

- 禁止调参数"让所有 seed 出现 >2%"(证明自己 ≠ 研究)
- 禁止以均值 gap 掩盖分布形态
- 禁止在 Selector 之前引用 LLM 作为贡献点
