# REVIEW v1.5-R21 — 三轮自审(R21 WEPA-Natural/Stress 完成后)

**日期**: 2026-08-17 上午 | **审阅对象**: R21(WEPA 真实仓验证)
**规则**: 每次更新对完成结果自审 3 次,再决定下一步。

---

## 第一轮:事实核查(取证)

| # | 发现 | 证据 | 处置 |
|---|------|------|------|
| V1 | **WEPA-Natural:myopic = BFIP(轨迹逐一相同)** | 40 SKU/12k orders/beam 12:identical trajectory,moves per period [0,32,27,36,18] | 确认:自然数据上贪心即最优 |
| V2 | **WEPA-Stress(温和注入 628 单 surge + ×20 mc):仍 gap=0.00%** | stress 变体 myopic=68150=bfip;winners 变化但轨迹一致 | 确认:温和 stress 不足以制造 trap |
| V3 | **stress 变体原始代码有 bug**:只改了 phase 标签,没改实际需求流 | 代码 diff(修复前后) | 已修:注入 bottom-half SKU surge orders;修复后仍无 trap(结论不变) |
| V4 | WEPA retrieval 订单为**单行**(1 SKU/order),无 basket 结构 | 数据检查:411,830 订单全部单行 | 解释了为何 E3(affinity)无信号;与 Instacart(3.25 行/单)本质不同 |
| V5 | 计算耗时 ~15 min/run(6 期 × 7 experts × CP-SAT) | 运行时间 | 限制了扫描密度;cache 不可用(WEPA 数据不走 regime_sequence cache) |
| V6 | slapstack 0.1.1 通过 pip 可得,**WEPAStacks 数据在包内** | `slapstack/use_cases/wepastacks/`(43MB orders + 21KB layout) | 重大发现:无需 GitHub/外部下载 |

## 第二轮:架构推导 —— 外部效度边界(论文核心素材)

**关键结论:trap 不出现在自然仓数据上**

| 平台 | 需求特征 | trap | 含义 |
|------|---------|------|------|
| 合成(28 天 8 相位) | promo ×8 / reversal / remap | ✅ 1/12 material | 构造性 regime 产生 trap |
| Instacart(真实 basket) | 真实共现,无 regime shift | 未测(Track B) | — |
| **WEPA-Natural** | 单行 retrieval,3 个月平稳 | **❌ gap=0.00%** | **自然数据太平滑** |
| **WEPA-Stress(温和)** | +30% surge(628 单) | **❌ gap=0.00%** | 温和注入不够 |

**论文表述建议**:
> "Inter-temporal reconfiguration traps require demand regime changes of a
> magnitude not present in steady-state warehouse operations (WEPA-Natural:
> gap = 0). This bounds the practical applicability of trap-aware expert
> routing to promotion seasons, seasonal transitions, and product-line
> changes — precisely the non-stationary scenarios the DWERP formulation
> targets."

这与 v1.0 spec §3.3 的 Re-slot Trigger 设计(不频繁搬库)一致 —— **"When NOT
to Reconfigure" 的日常答案就是"别折腾"**。

## 第三轮:方法论

- **Null result 的价值被正确呈现**:WEPA-Natural 的 gap=0 不是失败,是
  external validity 的边界刻画(什么条件下 trap 不存在)
- **块堆→拣位抽象的局限已声明**:SLAPStack 的 lane/block 结构被简化为
  单 SKU 单格;后续可接 SLAPStack 仿真核心(但工作量较大)
- **计算效率**:WEPA 实验无 cache(不走 regime_sequence 路径),~15 min/run
  限制扫描;后续可加 WEPA-specific cache
- **数据探索**:pip 包发现(use_cases/wepastacks)优于预期 —— spec v1.0 的
  GitHub 引用路径不可达但 pip 路径可达,记录为 lesson

## 下一步(三轮后决定)

1. **论文骨架初稿**(最高优先级 —— 20+ 实验的证据链已齐,开始组装)
2. R16 维度扩展(ShockPersistence × DemandShift)—— 低优先级,信息增量有限
3. Selector 开发(按 SPEC §7 cost-sensitive 框架)—— 论文骨架定稿后启动
