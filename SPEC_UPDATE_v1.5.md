# SPEC UPDATE v1.5 — 理论定位校准(强制,导师 2026-08-17 反馈)

**效力**: > v1.4 > v1.3 > ... > v1.0。冲突处以本文件为准。

---

## 1. 理论母体与 novelty 边界(冻结)

**DWERP ⊂ MTS / Switching-Cost Online Optimization(SOCO)**:目标函数
Σ C_op(S_t,A_t) + C_trans(A_{t-1},A_t) 与 MTS(1992–)/SOCO 同构。

**禁止单独作为 novelty**: sequential decision / switching cost / finite
lookahead / receding horizon(online optimization 文献成熟)。
**安全表述**: "a warehouse-specific online reconfiguration problem +
针对离散物理布局、OR Expert 候选动作、真实 relocation cost、非平稳需求、
不完全预测这一特殊结构的决策机制"。
下一轮 novelty audit 聚焦三个交叉面:MTS/SOCO × warehouse online
reoptimization(Lorenz/Otto/Gendreau)× anticipation/strategic waiting;
不再泛搜 "agentic warehouse"。

## 2. 核心命题(冻结,替换 v1.4 开头)

> **DWERP studies when a warehouse should defer locally optimal physical
> reconfiguration under non-stationary demand, and how much of the resulting
> full-information opportunity can be captured by deployable receding-horizon
> policies with imperfect forecasts and internal cost models.**

中文:在非平稳需求下,仓库何时应延迟眼前最优的物理重配置;以及在预测与
内部成本模型均不完美时,可部署的滚动决策能捕获多少全信息长期规划价值。

## 3. T3(capture≈0)升格为核心实验;v1.5 四件优先工作

1. **归因实验(R17,最优先)**: 固定相同 warehouse trajectory,内部成本模型
   逐级 Linear → Stop-aware → L0 Route Surrogate → 高保真 Replay,×
   H ∈ {1,2,3,7};每级记录 predicted vs realized expert ranking 的
   **Spearman ρ / Kendall τ、Top-1/Top-2 hit、Dynamic Regret、CaptureRate**。
   区分限制因素 = cost-model error / horizon insufficiency / forecast
   error / schedule uncertainty。
2. **Small-instance Exact Full-Information Oracle(R18)**: 缩小实例上
   DP/分层最短路/exact 求完整轨迹 optimum;大实例继续 beam;报告
   Gap_{beam→exact};seed 17 机制从 beam evidence 升级为 exact constructive
   evidence。
3. **C_trans 全面转为 d(L_t,L_{t+1})**(物理状态距离): 检测 symmetry /
   triangle inequality;满足 → 自然连 MTS;不满足(开/撤 pick-face 不对称)
   → warehouse-specific generalized switching cost(T1.5 的 17–69% 已是实证
   动机)。**"algorithm-switch counts are an inadequate surrogate" 升格为独立
   Methodology Finding**。
4. **Trap 相图扫机制参数而非 seed**: LeadTime × ShockMagnitude ×
   ShockPersistence × DemandShift × λm,P(MaterialTrap | ObservableState)。

## 4. 术语纪律(冻结)

| 旧 | 新 | 理由 |
|----|----|------|
| Dynamic Oracle(beam) | **Beam Full-Information Policy(BFIP)** | 避免审稿人按"oracle=真 optimum"纠缠 |
| (将来 exact 的) | **Exact Full-Information Oracle** | 三层:C_Exact ≤ C_BeamFI ≤ C_Myopic |
| Anticipatory policy | **Receding-Horizon Warehouse Policy(RHC/MPC 语言)** | 不"发明 anticipatory";表述 = "把 RHC/MPC 引入 DWERP,研究内部模型保真度如何影响可捕获 sequential value" |
| option value of waiting | **Reconfiguration Deferral**(主文用语) | 与 picker strategic waiting 文献(Lorenz 等)切割:他们的是"拣货员是否等未来订单",我们的是"是否延迟物理重配置" |

## 5. Ranking Fidelity(新指标,冻结)

RF_t = corr(Ĉ_t(E_1..E_7), C_t^realized(E_1..E_7))(Spearman/Kendall)。
核心假设:**sequential opportunity 只有在内部规划模型保持候选策略相对排序时
才可被捕获**(RF→capture 曲线;若呈单调关系 = 比 warehouse 更一般化的
方法学发现)。

## 6. VPM 正式定义(冻结)与 T2 重释

VPM = (ΔC_future_operation − C_move) / N_moves;比较 VPM_dynamic vs
VPM_myopic;**预期假设:λm 越高,dynamic 总 moves 降但 VPM 升**。
T2 高 λm 结果的规范表述:**"When NOT to Reconfigure ≠ Move Less —
Reconfigure Selectively"**;主目标不是 move frequency 而是 expected future
value per reconfiguration。

## 7. 贡献重排(冻结)

**Expert Routing 从主贡献降为 Decision Architecture**。主贡献:
① stateful warehouse reconfiguration ② physical transition cost
③ myopic trap characterization ④ deployable anticipation under imperfect
internal models。

## 8. 邻近文献坐标(存档,进 Related Work)

- MTS(Borodin et al. 1992–)/SOCO/带预测 online optimization
  (prediction window vs 预测误差 trade-off;learning-augmented MTS)
- Lorenz, Otto, Gendreau:动态到达订单下 warehouse online reoptimization
  (简单 reoptimization 在 batching/routing 可很好)+ anticipation 研究
  (strategic waiting 可能是高风险 all-in)—— 对照组:picker waiting ≠
  reconfiguration deferral
- 论文少用 "waiting",主文用 Reconfiguration Deferral

## 9. 执行顺序(v1.5)

R17 归因实验(最优先)→ R18 exact oracle(小实例)→ d(L,L) 主模型切换 +
度量性质检测 → Trap 相图机制参数版 → VPM/RankingFidelity 曲线 →
WEPA Natural/Stress → Selector(最后,Decision Architecture 角色)。
