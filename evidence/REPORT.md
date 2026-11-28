# W3 现有笔录定位入口的键盘可用性（Grokbot）

时间：2026-11-28 13:17（北京时间，Asia/Shanghai）
派遣：#106 comment 7234535872
接单：#106 comment 7234544567

## 检索

固定产品 `d4452bb6c8aac41f2ce99c157b02a7e501f4f4ba` 与已通过门槛 `8af8f3e8662c70b074cd9f0a5081d9a14ccdd4df` 下，没有可复用的真浏览器原件覆盖「用键盘从现有定位入口到已定位问答，并核 activeElement、视觉焦点、原问答 ID 与继续 Tab」。`8af8f3e` 用填写和点击做精确 UTC 定位与已确认比对回跳，未核键盘路径；其时间匹配与来源内容测试本轮不重跑。组件测试 `interview-turn-locator.test.cjs` 只模拟了 `focus()`，不是真键盘。`candidate/evidence-selection-keyboard` 不含本固定 SHA，是另一路径。

## 独立验收候选

- 分支：`candidate/w3-transcript-keyboard-browser`
- 完整 SHA：`858e6dd20275e0caf67a526e04ea2c981fd43c1a`
- 只新增 `tests_acceptance/w3-transcript-keyboard/` 三份验收文件；产品树未改，未改 `tests_acceptance/w3-transcript-utc/`，未改权限、契约、数据、CI 或主线。未跑真人、模型或评分。

## 正式跑

`timeout 150` 官方脚本退出码 **0**（2026-11-28 13:17 北京时间）。Google Chrome 156.0.8078.47，正常沙箱，没有 `--no-sandbox`。服务与页面均在 127.0.0.1。身份为页面官方角色选择器中的 LeadInvestigator。沿用同一份固定合成笔录（案 `SYN-W3-UTC-001`，笔录 `IR-01`，陈述 `IR-01-S01`）。

- 从现有「问答 UTC 时间」输入框起，全程键盘：33 次 Tab 到达该输入（`placeholder=YYYY-MM-DDTHH:mm:ssZ`，` :focus-visible `），键入 `2026-02-01T12:01:40Z` 后按 Enter，未点击「定位问答」。
- 定位后 `document.activeElement` 为 `[aria-current=location]`、`data-round=2` 的原问答，文中有「已定位 · 第 2 轮」和「唯一时间的原有回答」，` :focus ` 与 ` :focus-visible ` 均为真，计算样式为浏览器默认 `outline: auto 1px`。
- 继续 Tab 仍留在 `#/interview?case=SYN-W3-UTC-001`，焦点落到可操作按钮「定位所选比对条目的原文问答」；本轮没有激活该按钮，也没有触发写入或读取原件字节。

## 未验 / 边界

此项不等于 W3 整包，也不替代已通过的时间匹配或证据来源内容测试。未签发、未外发、未接真案。未验 Firefox/WebKit、headed。W7/W19 两条阻塞未动。
