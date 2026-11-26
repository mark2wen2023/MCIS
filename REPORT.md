# W4.1 修正定位后复跑报告（Grokbot）

时间：2026-11-26 18:13 Asia/Shanghai（CST, UTC+8）
派遣：#106 comment 7188910227
已接：#106 comment 7189074884（2026-11-26 18:13 Asia/Shanghai）

本项是临时预览初验，不是正式带锚校时、回写、迟到响应或 W4 整包。不把范围内通过报成整包通过。未改产品、未重建核心、未安装、未合并、未改 CI/main、未部署。未使用历史散落 DLL `7afd120c…`。

## 验收 SHA 与制品核对（未重建）

- 验收脚本：`b1586b667402431763f4b984202107894ecd5884`（2026-11-26 18:05:56 +0800，`test(W4): select the preview mapping by its scoped combobox`）。相对 `ce08e1d` 仅将「数据类型」定位改为每个 CSV `fieldset` 中唯一的 combobox，并 `select_option(value="CourseOverGround")` 后 `to_have_value("CourseOverGround")`。产品钉仍为 `94d5e38c926fda232bb987b60fa9145e4bcf01a7`。未改产品、未跳过业务断言、未延长等待。
- 复用上一轮离线构建产物（`/workspace/mcis-w41-core-out`，清单见上一轮 `artifacts/build-manifest.json`）。核对结果全部一致：
  - DLL：`f94197777acc45d7ff4e84f265ded9d43c32e773c17cac462d952574d77ac9cf`
  - runtimeconfig：`3d25821758613e4cd940d143ccb03c93704140077e69104996832510f38f6598`
  - deps：`fda133109cf9fc926cbda09598ad344f75dc57ec02e345b6923ec5fe2dff9d12`
- 跑后 DLL 摘要未变。未触碰 `7afd120cb343a4459b1f012ea96c5ab8df53c04a4ba58b916dcc20f3d1d88337`。

## 复跑结果

命令：`timeout --signal=TERM --kill-after=10s 150s run.py`（正常沙箱 Chrome 156.0.8078.47，`chromium_sandbox=True`，未用 `--no-sandbox`；`--core-dll` 为上列已核制品，`--core-sha256` 为完整哈希）。服务 127.0.0.1。未手发信号。退出码 **0**。无第一条失败。

`receipt.json`：
- `passed=true`
- `scope`: `synthetic unanchored COG preview only; not W4 whole package`
- `sandboxRequested=true`，`browser` / `browserRuntime` = Google Chrome 156.0.8078.47
- `coreDllSha256` 与上列完整哈希一致
- `cases`: SYN-W41-X-A、SYN-W41-X-B
- `previewPosts`: 1440=3、390=3（各视口 A 预览、B 预览、再回 A 预览）
- `sqliteLogicalSha256`: `722547264cbde040ae53126ec54c9fd4d0cb9deb24897f03bc7282689c764ee4`（预览后与服务重开后逻辑库摘要不变，由脚本断言）

已验（均由原 runner 在真 Chrome 中断言，非 HTTP 冒充、非 DOM 模拟）：
- 真实选择并断言 `CourseOverGround`
- 两视口 Evidence 面板读到不同 COG 差值：A 为 5 deg（45/50），B 为 11 deg（70/81）
- 明确「未入库」「未全部校准」
- A→B→A 状态隔离（每视口 3 笔预览 POST；390 重开 0 笔新 POST）
- SQLite 预览后与真实后端重启后逻辑内容不变
- 视口无整页横溢；截图为真尺寸：`w41-1440-fresh.png` / `w41-1440-unanchored.png` 均为 1440×900；`w41-390-fresh.png` / `w41-390-unanchored.png` / `w41-390-reopened.png` 均为 390×844

未验：正式带锚校时、回写、迟到响应、W4 整包（本项范围之外，不当作已通过）。

截图路径：`/workspace/mcis-w41-b1586b6-report/accept-out/`。
