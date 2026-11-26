# W15 AcciMap 合成草图原门禁复跑报告（Grokbot）

时间：2026-11-26 21:15 Asia/Shanghai（CST, UTC+8）
派遣：#106 comment 7192689505
已接：#106 comment 7193074899（2026-11-26 21:14 Asia/Shanghai）

本项在独立验收候选用 `147e322` 的相同夹具和断言，只重钉产品 SHA `2447b14076bbf39db014b8bf4a3a3b350cbf0e05` 与组件摘要 `d6f67ba6d80b19b7a1c212a02ee6ac0bfc7903f6d067affd2acba4e6210c875f`，复跑原门禁。未改产品源码，未改、放宽或删除原断言，未延长超时，未安装，未重跑 W4.1。不是 W15 或 W4 整包。

## 验收候选与产品核对

- 候选分支：`candidate/w15-accimap-arrow-rerun` @ `367ea21e22f3f9b7ce1aee160d318469982c738e`（2026-11-26 21:15:19 +0800）。基于产品 `2447b14`，验收脚本/夹具来自 `147e322`，仅重钉 PIN 与组件摘要校验。`page.tsx` / `index.html` 与 `147e322` 无差异。
- 实际检出 `web/src/accimapPreview/Diagram.tsx` SHA-256 `d6f67ba6d80b19b7a1c212a02ee6ac0bfc7903f6d067affd2acba4e6210c875f`，与派遣摘要一致。跑后摘要未变。

## 官方复跑结果

命令：`timeout --signal=TERM --kill-after=10s 150s run.py`（正常沙箱 Chrome 156.0.8078.47，`chromium_sandbox=True`，未用 `--no-sandbox`；服务仅 127.0.0.1）。未手发信号。退出码 **0**。无第一条失败。`receipt.passed=true`，`scope=synthetic AcciMap draft diagram component only; not W15 or W4 whole package`。两视口均跑到并通过。

### 1440×900

- 真键盘 Tab 进入具名图框 `AcciMap 草图可滚动区域`；`outline: rgb(16, 16, 16) auto 1px`。
- ArrowRight 前：页面 `innerWidth=1440`，`pageScrollWidth=1440`，`pageScrollLeft=0`（整页不横溢）；图框 `scrollWidth=1706`，`clientWidth=1408`，`scrollLeft=0`。
- ArrowRight 后：页面宽度与 `pageScrollLeft` 仍为 1440 / 0；图框 `scrollLeft=48`。只改变图框滚动。
- 原生键盘打开「查看全部输入节点（完整名称）」；分层标题为 政府与法规、监管、公司、船舶管理、船员行为、设备与环境；完整长名称（含「这是必须完整保留且不能只显示十个汉字的合成节点说明」及全部长 ID）已核。

截图：
- `w15-accimap-1440-focus.png` 1440×900，117549 bytes，SHA-256 `d14b04ffcc590693435beecf25cfa9c1df989b78cb78b8affbd558da31b2d67a`
- `w15-accimap-1440-after-arrow.png` 1440×900，111808 bytes，SHA-256 `90a2853986de23263e401d8c7b60e54cef41a420c8568cf61885bb19529e7a7f`
- `w15-accimap-1440-list.png` 1440×900，167553 bytes，SHA-256 `873e64541dd471f8cf3c251dd160138f5331217ce21dbca051df3cced75bec8c`

### 390×844

- 同样真键盘 Tab 进入具名图框，可见焦点 `outline auto 1px`。
- ArrowRight 前：页面 `innerWidth=390`，`pageScrollWidth=390`，`pageScrollLeft=0`；图框 `scrollWidth=1706`，`clientWidth=358`，`scrollLeft=0`。
- ArrowRight 后：页面宽度与 `pageScrollLeft` 仍为 390 / 0；图框 `scrollLeft=48`。只改变图框滚动，整页不横溢。
- 键盘打开文字清单，分层与完整长名称断言通过。

截图：
- `w15-accimap-390-focus.png` 390×844，82840 bytes，SHA-256 `c64cd42a799415b172e6942ec703d9bdf911e82881410de9070bb41b82a33474`
- `w15-accimap-390-after-arrow.png` 390×844，80149 bytes，SHA-256 `29e42513cc66302e423953b986db88249d6ad62df9191d8b703307961a3717a1`
- `w15-accimap-390-list.png` 390×844，95592 bytes，SHA-256 `f5c5bb8a837a8a3a2adea50ea2eadad819708217cf91f484baa65305afad08e6`

已验：1440 与 390×844 的 Tab 焦点、ArrowRight 局部滚动、整页不横溢、键盘打开清单、完整长名称与按层分组。未验：W15 整包、主入口接入、带锚校时、写回、W4.1（本轮按派遣不跑）。
