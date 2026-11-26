# W15 AcciMap 合成草图组件隔离验收报告（Grokbot）

时间：2026-11-26 20:24 Asia/Shanghai（CST, UTC+8）
派遣：#106 comment 7191824474
已接：#106 comment 7191856434（2026-11-26 20:19 Asia/Shanghai）

本项只验 MCIS `897297ec97da9f0f33db6122e9dd234a25a31498` 的 AcciMap 合成草图组件。未接主入口；在隔离验收候选用该 SHA 的真实组件与合成测试页。未改产品源码，未安装，未重跑 W4.1，未动带锚校时或写回，未用 W4.1 核心 DLL。不是 W15 或 W4 整包。不把范围内结果报成整包通过。

## 验收候选与产品

- 候选分支：`candidate/w15-accimap-sketch` @ `147e322d402c89b727f95ff84cd51b983d224655`（2026-11-26 20:24:40 +0800）。相对产品 SHA 只新增 `tests_acceptance/w15-accimap-synthetic-browser/`。`web/src` 与 `897297ec` 无差异。
- 产品组件：`web/src/accimapPreview/Diagram.tsx`，SHA-256 `5c1703dbf09665cde748046b91f3791057837e8e9afc574e530c4b0f0b7a7144`（与钉住 SHA 的 blob 一致）。
- 合成测试页用 8 个公司层节点使图宽为 1706，以便桌面 1440 与 390 下图都比容器宽。含完整长名称，供文字清单核对。

## 官方复跑结果

命令：`timeout --signal=TERM --kill-after=10s 150s run.py`（正常沙箱 Chrome 156.0.8078.47，`chromium_sandbox=True`，未用 `--no-sandbox`；服务仅 127.0.0.1）。未手发信号。退出码 **1**。

第一条失败（1440×900，停，未改产品、未改超时门槛）：真键盘 `ArrowRight` 后图框 `scrollLeft` 仍为 0，与按键前相同。组件本身没有 `keydown` 处理器，说明文字写「聚焦图框后按左右方向键」，实际依赖浏览器原生滚动。本轮未用 Playwright 改 `scrollLeft` 或用脚本冒充焦点/滚动。

已留下首错原图与日志：
- `w15-accimap-1440-focus.png` 1440×900（117549 bytes，SHA-256 `d14b04ffcc590693435beecf25cfa9c1df989b78cb78b8affbd558da31b2d67a`）
- `w15-accimap-1440-after-arrow.png` 1440×900（117532 bytes，SHA-256 `f98c9a3c3343d05b464c7ef768016395bdd7ea1d9583929c136ba8a397375f77`）
- `w15-accimap-1440-first-failure.png` 1440×900（117069 bytes，SHA-256 `9198175fd330de82c15e708f4a3a01484560b1abcfe96152b0698f86c7719f99`）

1440 已跑到的部分：
- 真键盘 Tab 进入具名图框 `AcciMap 草图可滚动区域`；`document.activeElement` 为该 region；可见焦点 `outline: rgb(16, 16, 16) auto 1px`。焦点截图可见图框黑框描边，最右侧公司节点被裁切。
- 按键前：页面 `innerWidth=1440`，`pageScrollWidth=1440`，`pageScrollLeft=0`（整页不横溢）；图框 `scrollWidth=1706`，`clientWidth=1408`，`scrollLeft=0`（图比容器宽）。
- 按 ArrowRight 后：页面宽度与 `pageScrollLeft` 仍为 1440 / 0（整页仍不横溢）；图框 `scrollLeft` 仍为 0，**未**只改变图框滚动。

未验：390×844（桌面首错后停）；用键盘展开文字清单、完整长名称与按层分组（未跑到）。

`receipt.json`：`passed=false`，`scope=synthetic AcciMap draft diagram component only; not W15 or W4 whole package`，`sandboxRequested=true`。
