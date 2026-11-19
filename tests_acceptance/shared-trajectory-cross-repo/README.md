# 跨仓契约联调 A：MCIS 固定合成输入

基线：PR #102 / feat/shared-trajectory-contract 的 `a400fa9bf43cc7e686295d2f28823530d22a333a`。本包仅新增三份原样 JSON、离线检查与说明，不修改契约、校验器或业务代码，不是业务导出、AIS 记录或实际 Chromium 验收。没有船名、人员、媒体、原案或外部来源；所有位置、尺寸、速度和身份均为手造声明。

## 输入及预期

共同对齐起点为 `2026-02-01T12:00:00.000Z`，时域 0–14 秒。WGS84 经纬度为十进制度（不等于局部米坐标），角度真北顺时针、速度 knots。所有点 heading 为 missing/null，COG 为 90.25°，不得将 COG 当船首方向。尺寸为 schematic；显示倍率 1 仍不证明真实船体或碰撞。

| 文件 | 案件/船 | 对齐秒点 | 参考结果 |
|---|---|---|---|
| vessel-a.json | SYNTHETIC-CROSS-REPO-A / SYNTHETIC-VESSEL-A | 0,5,6,7,10,14 | sync=true；continuous=false |
| vessel-b.json | 同案 / SYNTHETIC-VESSEL-B | 0,4,6,6.5,7,10,14 | sync=true；continuous=true |
| mixed-case-b.json | SYNTHETIC-CROSS-REPO-OTHER / 同 B 船 | 同 B | 单文件与 B 同样有效；与 A 组合必须判案号不一致 |

A 的 missingIntervals 明确为共同起点后 6–7 秒，处于常见 5→10 秒采样格之间；6 秒和 7 秒各有手造边界观测，内部无点。消费者不得仅检查 5 秒格点而漏掉缺口，也不得跨区间连续插值；契约未细化端点播放处理，本包不凭空定义消费者的半开/闭区间行为。B 同段含 6、6.5、7 秒点且没有声明缺口。实际采样均非等间隔；expectedIntervalSeconds=5 只是名义声明，gapThresholdSeconds=8 为合成工程阈值。参考结果 gaps=[]，A 的阻断来自 missingIntervals，不是大采样间隔自动推断。

B 的源时钟明确手造为慢 2 秒：alignedUtc=sourceUtc+2s，status=corrected；例如源 11:59:58.000Z 对齐为共同起点 12:00:00.000Z。A 为 referenced/零修正。保留 sourceRecordTime；不是测得校时、漂移拟合或消费者已支持证明。

## 原样文件 SHA-256

- vessel-a.json：`ddcca8bec01f1b42a6e3d10117ec4f701a75294c45807912d055647c50845575`
- vessel-b.json：`349a5fa53eeb3a23438019069a4962aa0e1140e9b305e0222fd9dfb71e09f581`
- mixed-case-b.json：`445af0af19302d51590bbc57cc27730a470752bd4dc8c6fdac14d462c4c8d77c`

JSON 本身即交付的原样输入，不需要生成器或读取外部数据。混案文件经深比较确认只有 caseId 不同；不能因各单文件有效就混为一案。

## 离线复验（已执行，开发方）

从候选仓库根目录，使用已有 Python 3 与 jsonschema（本轮未安装依赖）：

```sh
sha256sum -c tests_acceptance/shared-trajectory-cross-repo/SHA256SUMS
python -B tests_acceptance/shared-trajectory-cross-repo/check.py
```

检查器先固定参考 validation.py 和 schema 的 SHA-256，再通过 runpy 仅加载纯校验文件，不导入 mcis_service 包/应用。只读取三个手造输入和明确契约文件；不改写输入，不访问网络/DB/ORM。三个单文件结构及语义通过；同案不同船、共同时间域、非等间隔、缺艏向不回填、短缺口、+2秒修正、混案单文件有效但组合不一致均有明确断言。requiresHumanReview=true、authenticityVerified=false、visualOverlapIsCollisionEvidence=false 保留。

这是 MCIS 参考校验和样例关系检查，不是双船组合 API、业务导出或消费者验收。mcis-3d/Google AI Studio 仓库未读取或修改；没有向外部服务发送样例，唯一交付为获准的 MCIS 候选 Git 推送。消费者仍须独立验证：同案门控、两船 UTC 同步、6–7 秒内连续动画断开/未知提示、边界处理、缺艏向显示、校正符号与非等间隔、坐标单位。未执行浏览器/模型/服务/权限/真实数据/CI 或任何暂停测试。不合并部署。
