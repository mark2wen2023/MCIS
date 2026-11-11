已按裁定实现规格第 1–9 项，保持现有 API。两个指定 `dotnet build` 均成功：**0 警告、0 错误**。未运行 `dotnet test`；验收源码、缺陷单及契约哈希保持一致。

| 缺陷／裁定 | 实现说明 |
|---|---|
| D01 | 首次形成危险时锁定交叉局面及角色，操纵不再导致角色互换或改判追越。 |
| D02 | 对遇及双方行动义务保持到危险解除，右转后不会改判交叉。 |
| D03 | 显式互见优先于能见度，互见时适用 R13–R17。 |
| D04 | 接入阶梯保持的互见序列；缺省按能见度和距离推导，保留显式转换时刻。 |
| D05 | R19(d) 增加危险／紧迫局面前提，无危险时输出 NotApplicable。 |
| D06 | R17 阶段单调推进，连续操纵按完整行动评估，安全效果检查到危险期结束。 |
| D07 | 补齐规则目录和核查；缺证据输出 NotAssessable，R9 支持航道折线靠右判断。 |
| D08 | 输出稳定 ID、Draft、原样证据引用、互见、角色船号及危险阶段区间。 |
| A3 | 轴线方位参考他船视角；视角矛盾标记 Doubt 并说明原因。 |
| A4 | 默认 ±22.5° 存疑扇区按对遇处理，阈值可配并标记 Doubt。 |
| A5 | 采用 1 nm／720 s、0.3 nm／360 s、30°／60 s 滑窗及初速 30% 默认值；R6/R19(b) 输出 NeedsReview。 |

改动文件：

- [ColregEngine.cs](/workspace/maritime-sim-design/unity/Assets/_Project/Scripts/Domain/Colreg/ColregEngine.cs)、[ColregEvaluator.cs](/workspace/maritime-sim-design/unity/Assets/_Project/Scripts/Domain/Colreg/ColregEvaluator.cs)、[ColregModels.cs](/workspace/maritime-sim-design/unity/Assets/_Project/Scripts/Domain/Colreg/ColregModels.cs)、[ColregThresholds.cs](/workspace/maritime-sim-design/unity/Assets/_Project/Scripts/Domain/Colreg/ColregThresholds.cs)、[ColregRules.cs](/workspace/maritime-sim-design/unity/Assets/_Project/Scripts/Domain/Colreg/ColregRules.cs)。
- 新增 [ColregEncounterState.cs](/workspace/maritime-sim-design/unity/Assets/_Project/Scripts/Domain/Colreg/ColregEncounterState.cs)、[ColregIds.cs](/workspace/maritime-sim-design/unity/Assets/_Project/Scripts/Domain/Colreg/ColregIds.cs)。
- 自测：[ColregEngineTests.cs](/workspace/maritime-sim-design/unity/Tests_W1_Colreg/ColregEngineTests.cs)、[ColregFixRegressionTests.cs](/workspace/maritime-sim-design/unity/Tests_W1_Colreg/ColregFixRegressionTests.cs)。旧期望调整均注明原因，新增 6 个边界回归实例。

逐例推演预计 **8 个 KnownDefect 全部通过**。预计仍失败的共 6 个参数化实例：

| 用例 | 原因 |
|---|---|
| `R8_SubstantialTurnThreshold(10,true)/(25,true)` | 与默认 30° 裁定冲突。 |
| `R19b_SafeSpeedProxy_ConfigurableThreshold` | 硬判期望与 NeedsReview 裁定冲突。 |
| `Thresholds_RestrictedVisibility_Configurable` | 第二个断言与距离内推导互见冲突。 |
| `TimeBands_SplitWhenRiskEnds` | **规格漏列冲突**：转向后 DCPA≈0.638 nm，新阈值下约 280 s 才解除，旧断言要求 60–80 s。 |
| `TimeBands_MultipleTransitions` | **规格漏列冲突**：520 s 首次重新形成危险时为 Crossing，按 A1 必须锁定，旧断言要求随后变成 HeadOn。 |

未解决项是上述验收断言与裁定的冲突，以及待外部实际执行测试确认；当前不能宣称测试已全绿。