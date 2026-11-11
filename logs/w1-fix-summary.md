# W1 返修结果（2026-11-11 北京时间）
- 红灯：新增自测后 111 项中 50 败（logs/w1-fix-red-selftest.txt）。
- 自测：117/117 通过（logs/w1-fix-selftest-final.txt）。
- 验收：81 项 75 过 6 败；KnownDefect 8/8 通过（logs/w1-fix-acc-final.txt）。
- 6 个失败均为验收断言与架构师裁定冲突（未改验收测试）：
  1-2. R8_SubstantialTurnThreshold(10,true)/(25,true)：A5 默认大幅转向 30°。
  3. R19b_SafeSpeedProxy_ConfigurableThreshold：A5 安全航速只出“需研判”(NeedsReview)。
  4. Thresholds_RestrictedVisibility_Configurable 第二断言：D04 缺省“距离≤能见度即互见”（2.16nm ≤ 2.5nm → HeadOn）。
  5. TimeBands_SplitWhenRiskEnds：A5 危险 DCPA<1nm，转向后 DCPA≈0.638nm，危险至约 280s 才解除（测试要求 60–80s）。
  6. TimeBands_MultipleTransitions：他船 500s 起掉头，520s 转向途中按新阈值首次形成危险时为 Crossing，A1 锁定到解除，不再出现 HeadOn。
- tests_acceptance/W1 哈希前后一致（logs/w1-fix-acc-hashes-{before,after}.txt）。
