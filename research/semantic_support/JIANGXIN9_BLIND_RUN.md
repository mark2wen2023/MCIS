# 第二公开案例：Pi / DeepSeek 时间与来源主张盲测

## 运行前冻结

只计划一次真实运行，无自动重试；最多4次模型请求、8次工具、180秒。使用用户授权公开事故报告与既有官方Pi1.5.2研究harness，配置DeepSeek官方HTTPS端点及deepseek-v4-pro（底层模型身份未独立认证）。无生产写入、无事实激活、无部署。

- 固定profile：jiangxin9-v1，8项。
- 报告PDF SHA256：d424673df94377cbf93cad769ca514b08a24b8a0bb552b042cc34e5149c4ff55。
- corpus SHA256：f7a1a69f2f2bf51236ecfc734952c8249e87b0bbaf0e8913b006167900bff782。
- canonical cases inputDigest：a754aaeb1ff5a2d2852186bc513542356a3c93f44e00831ae7a686f4c6383c96。
- 投影JSON文件SHA256：56e09066bf71aa74eb786d4f6fd534458493f1122d525dd3f7427efb1a33352d，和上述canonical摘要不是同一对象。
- manifestDigest：5a553a8dca41f1cbd1242f261d535aa66e19070c09f3b11abea5ec53c889bc9a；执行过程未改变，案例绑定由另两个摘要承担。

参考建议标签冻结但不进入模型；opaque IDs、逐字材料及待检主张进入模型。一般方法提示沿用上一轮，因此不是无方法指导的零样本基准。校验工具只检查schema/覆盖，不反馈答案。密钥只由Python父进程内存及官方请求鉴权使用，不给Node、模型、环境变量、参数、文件或日志。

这是受控文本材料的时间/来源主张语义支持测试，不是完整时间线提取、视觉OCR、生产专家群或专业结论验收。截图秒值由AI查看渲染页后明确转录；正文保留原页引用、约数与日期差异。联合材料包每段标注页码，主定位不是完整的单页定位。参考标签仅AI建议，未获两名业务专家独立确认，不报告权威准确率。

## 实际运行

安全独立审查无阻断后执行一次，runId `33acba11-3c47-48d3-9ab5-64f103ce0c64`。3次实际DeepSeek请求均完成、3模型轮次、2工具调用、8项预测；realPi=true、realModel=true、transportMocked=false。host完成/close、Node完成及Python进程exit0已核对。无重试，无正式事实激活。

模型正确按给定截图转录计算44秒，并分别保留页8和页11离泊记载，拒绝据两段材料断定真实日期或指定某处必为笔误。但这不代表专业验收：

- `distance_false_precision`模型标签conflicted，与AI建议insufficient不同，仍需专家区分缺少支持与明确反证；不计算权威准确率。
- `distance_proves_contradiction`标签insufficient虽与建议相同，解释却将正文两个距离断言为分别对应两个截图精确时刻。材料仅支持截图时钟不同，未独立建立文字测距时刻与截图同步关系，属于额外推断。标签相同不能掩盖理由风险。

保留未经改写的run/predictions/receipt和离线comparison，文件名前缀 `jiangxin9-real-`。比较器的realModelCalled=false仅描述离线比较步骤，不能解释为上游未调用模型。回执是未签名运行记录，不是第三方审计；provider模型身份未独立认证。

运行前合并107项Python离线安全回归及Node2脚本（包括6runner情景）通过。这些mock/fixture只验证工程边界，非模型能力。首次独审测试将文件SHA混作canonical cases摘要，3项断言失败；独立重算纠正预期后通过，模型前输入未改变。
