# REVIEW v1.3 — 三轮自审(SPEC v1.3 落地 + T1a/T1b/T2 完成后)

**日期**: 2026-08-16 | **审阅对象**: R12(T1b prevalence)+ R13(T2 sensitivity)+ 判据体系变更
**规则**: 每次更新对完成结果自审 3 次,再决定下一步。

---

## 第一轮:事实核查(取证)

| # | 发现 | 证据 | 处置 |
|---|------|------|------|
| U1 | **微型 trap 计入 headline**:R12 报"9/12 traps",但其中 8 个是 sacrifice≤48、regret≤384 的微 trap(gap 贡献 <0.5%),仅 seed 17 是大 trap(regret 2116) | R12 逐 seed 表 | 分布表 + gap buckets 已如实分层;**headline 修正口径**:prevalence of inter-temporal structure = 9/12,prevalence of *material* trap(regret>1% 总成本)= 1/12。已写入本 REVIEW,论文引用后者时须带前者 |
| U2 | **判据静默修改**:R13 补丁中把 inverted-U 的端点比 2× 改为 1.5×,未预先声明 | 脚本 diff | **流程违规,记录**。结果未翻转(两种阈值下均 NO,峰值 1.26 < 1.5×1.16),且主结论改用"实测形态"表述而非 gate 布尔;教训:任何判据改动必须先 commit 声明 |
| U3 | R13 winning map 的 winner 来自 myopic 路径(非 dynamic) | 脚本 winner_map 收集自 m.periods | 报告已标 "modal myopic winner";learnable-structure 检查的对象就是"可部署规则能预测的 winner",myopic 口径正确 |
| U4 | λm=0 时 gap≈0.10% 非 0 | per-seed 表(s17=0.15,s37=0.14) | 非 move 的 trajectory 差异(纯布局质量),量级无害,报告已含 |
| U5 | R13 曲线仅 3 seeds,λm=5 处 mean 低谷属采样方差 | per-seed 表 | 如实标注;cache(JSON)已支持增量补 seeds |

## 第二轮:架构推导 —— 三个实验的科学结论

1. **T1a(YES,已固化)**:当期最优 ≠ 长期最优,constructive evidence = seed 17。
2. **T1b**:gap 呈**保险型重尾**(10 个 ~0 / 1 个 small / 1 个 large;9/12 存在
   inter-temporal 结构,但 material trap 1/12)。divergence 集中于
   **promo_ramp(4)+ stable2(4)= 结构转变前夜**。myopic failure 不是随机噪声,
   是"平稳/爬坡期的局部优化 × 后续成本冲击"的**复合事件** —— P(trap|state) 有结构,
   值得建模(这正是 Selector 的输入)。
3. **T2**:λm→Moves 单调降(635→167);gap 曲线 = **左端低(≈0.1%)+ 中段峰
   (λm=10,mean 1.26%/max 3.47%)+ 右端 plateau(1.0–1.2%,未收敛)**。
   经典 inverted-U 的右半不成立;实际机制更好:高 move 成本下 dynamic 搬得
   **更多但更好**(λm=50:164 vs 152 moves,pick 节省 > move 罚)——
   **"when not to reconfigure" 在高成本区的答案不是'不搬',而是'只搬最关键的'**。
   规划价值随赌注上升而非消失。
4. **Winning map(可学习结构检查)**:mc_shock→E7 100%、reversal→E7 83%、
   promo_peak 33%(E7/E3/E4 分裂)。结论:f(S_t)→E* 在成本/结构冲击相位
   **稳定可学**,在 promotion 峰值相位需要更细的状态特征 —— 支持 Selector
   开发,但不支持"一个全局规则搞定"。

## 第三轮:方法论

- **三统计报告(mean/median/max)应成为 gap 类指标的标准形态** —— U1 再次证明
  mean 掩盖重尾;R13 已重画三线图
- **判据纪律**(U2):gate 阈值属预声明科学对象,改动需单独 commit;本轮靠
  "主结论用实测形态而非布尔"兜底,下不为例
- SPEC v1.3 的 T1.5(move-only / switch-only / both 三分)**未完成** —— 本轮只跑了
  move-only(λs=0);如实记录为下一步,不冒充完成
- cache-resume 机制(JSON cells)已落地:补 seeds 的边际成本降至 ~85s/seed

## 下一步(三轮后决定)

1. **T1.5 补全**:switch-only(λs>0,λm=0)与 both 条件;顺带验证
   C_switch 罚 1[E_t≠E_{t-1}] 的失真(两个 Expert 同 layout 切换不该有成本)
   —— 为论文的 d(A_t,A_{t-1}) 公式化提供实证
2. **曲线平滑**:≥10 seeds 增量补 R13(cache 已支持),重估 peak/plateau
3. **Trap 建模前置分析**:以 divergence phase + 后续 shock 组合为特征,
   统计 P(material trap | phase pair) —— Selector 的标签正是它
4. 之后按 SPEC v1.3 §6:Trap/Phase-Diagram 分析 → WEPA → Selector
