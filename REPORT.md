# W15 移动布局候选报告（Grokbot）

时间：2026-11-26 16:54 Asia/Shanghai（CST, UTC+8）
派遣：#106 comment 7186473922
已接：#106 comment 7187021900

## 固定候选

- 分支：`candidate/w15-mobile-layout`
- 完整 SHA：`912d96a39f1a68e98008a7317a211f5e29ed3845`
- 起点：`ad4e56e4e1169aa0505ca5310d3f979876cb1a97`（产品修复 508460d + `--native-body` 验收）
- 未合并、未改 CI/main、未部署。默认 `result.json()` 门禁未改；本轮未复跑原 124 命令（未验）。

## 产品差异

仅改 `web/src/styles/w15-bowtie.css`（W15 作用域，未改全局 `styles.css` / `Layout.tsx`）。`pins.json` 中该文件 blob 由 `c76fa8da…` 更新为 `b72261b3dc29c4fd89dcc6cde45ddd4403002441`。验收脚本在 `--native-body` 路径增加 1440/390 真尺寸视口截图、横向溢出断言，以及导航 / 案号 / 角色可见且可聚焦检查；默认门禁路径不变。`diagnose.py` 的 `ORIGINAL_SHA256` 随 `run.py` 更新为 `9867a01e532e0d5a83f28c708786f1f3e75ad72eb38ab4781f5d176ad555bca4`。

CSS 要点（`.app:has(.w153-page)` 作用域）：
- `grid-template-columns: var(--sidebar-w) minmax(0, 1fr)`，打破 1fr 自动最小尺寸跟着 nowrap 顶栏走的问题
- 顶栏 `min-width: 0`；≤1100px 允许换行（`.case-chip` 可折行，`.role-select` 不被隐藏）
- ≤600px 单列堆叠侧栏（侧栏可纵向滚动，不隐藏导航）
- `.w153-diagram`：`min-width: 0; max-width: 100%; overflow: auto`（图仅在自身容器内平移）
- 无全局 `overflow: hidden`，未隐藏导航、案号或角色选择

## 修前度量（真 Chrome 156.0.8078.47，正常沙箱，viewport 390×844 / 1440×900）

修前 390（首处超宽 = document，delta 483）：

| 节点 | clientWidth | scrollWidth | 备注 |
|---|---:|---:|---|
| document | 390 | 873 | 首处超宽 |
| app | 390 | 873 | grid `224px 648.891px` |
| topbar | 649 | 649 | min-width auto，nowrap 撑开 1fr |
| main | 649 | 649 | 等于被撑开的主列，本身不额外超宽 |
| diagram | 565 | 1100 | overflow-x auto，已是局部滚动 |

侧栏 width 224px、clientWidth 223。修前 390 全页截图实际 **873×844**（与 Dot 指出的旧 `03-restart-390.png` 一致）；视口截图 **390×844**。

修前 1440：document/app 1440/1440，grid `224px 1216px`，diagram 1132/1132，无超宽。截图 1440×900。

## 修后度量（同一套真 Chrome，候选已含 CSS）

修后 390（页面/主区无横向溢出；首处超宽仅 diagram，属局部滚动）：

| 节点 | clientWidth | scrollWidth | 备注 |
|---|---:|---:|---|
| document | 390 | 390 | 整页不再横滚 |
| app | 390 | 390 | grid 变为单列 `390px` |
| topbar | 390 | 390 | 换行后不再撑宽 |
| main | 390 | 390 | 主区无横向溢出 |
| diagram | 322 | 1100 | overflow-x auto，仅图内滚动 |

修后 390 视口截图 **390×844**；全页截图 **390×1930**（侧栏堆叠后变高，宽度仍为 390，不是失真的 873 宽图）。

修后 1440：与修前一致，document/app 1440/1440，grid `224px 1216px`，diagram 1132/1132，无超宽。截图 1440×900。

功能复跑（`--native-body`，150s 外限，未手发信号）写入的 `layout-390-metrics.json` / `layout-1440-metrics.json` 与上表一致；`pageOverflow` 均为 `[]`。

## 390 与 1440 功能复跑（`--native-body`）

- 命令：`timeout --signal=TERM --kill-after=10s 150s diagnose.py --native-body`（正常沙箱，127.0.0.1）
- 退出码：**0**
- 整页/主区横向溢出：无（390 与 1440 的 document/app/main 均 clientWidth=scrollWidth）
- 图仅局部滚动：390 时 diagram 322/1100、overflow-x auto；1440 时 diagram 1132/1132，无需滚动
- 案隔离：A→B→A 仍通过；390 重开无新预览（`host-reopened.log` 为空，与上一轮 `--native-body` 相同）
- `--native-body`：`receipt.json` 为 `nativeBodyVerified=true`，`bodyVerified=true`，`browserVerified=true`，`passed=false`，`sandboxRequested=true`，`browserVersion=Google Chrome 156.0.8078.47`
- SQLite 重开：脚本打印 “W15 native browser body read and same-threshold UI/SQLite verified”；行为与上一轮一致
- 导航、`.case-chip`、`.role-select` 在 390 与 1440 均可见，角色选择与导航链接可聚焦
- 原 `result.json()` 门禁：本候选未复跑（未验）；默认路径未改，124 未为跑绿而修改
- 不把范围内通过报成整包通过（`passed=false`）

## 真尺寸截图（勿把全页加高或旧 873 宽图当成 390 视口）

- 修前：`before/before-390-viewport.png` 390×844；`before/before-390-fullpage.png` 873×844（溢出证据）
- 修前 1440：`before/before-1440-viewport.png` 与 fullpage 均为 1440×900
- 修后：`after/after-390-viewport.png` 390×844；`after/after-390-fullpage.png` 390×1930
- 修后 1440：`after/after-1440-viewport.png` 与 fullpage 均为 1440×900
- 功能复跑：`native-out/layout-390-viewport.png` 390×844；`native-out/layout-1440-viewport.png` 1440×900
- 功能复跑全页：`native-out/01-core-unavailable-1440.png` 与 `02-case-switch-1440.png` 为 1440×900；`native-out/03-restart-390.png` 为 **390×1930**（不再是 873×844）

## 约束执行情况

服务只监听 127.0.0.1；Chrome 正常沙箱（`chromium_sandbox=True`，未用 `--no-sandbox`）；合成数据；不安装、不改 CI/main、不合并、不部署；停止只用 150s 外限。未打包 NetLog。
