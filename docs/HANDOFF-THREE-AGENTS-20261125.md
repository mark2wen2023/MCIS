# MCIS 三方开发交接书

2026-11-25（UTC+8）。适用对象：Dot、Grokbot、AI Studio。本文分配下一轮工作，不是集成版本，也不代表扩大验收范围。

## 先看哪里

- [原甘特图](https://chatgpt.com/space/page_d59ce90cb8ac81918005a5642f50e655)：整体验收 **10/22**；W4、W21 的新增进度先记到子关口，不提前勾选。
- [Dot 交付总清单](./HANDOFF-CLOSURE-20261125.md)：已验证的候选版本和六套可复跑入口（W7/W11、W4、W17、W21、W9、W19）。MCIS 主分支基线 `94d5e38c926fda232bb987b60fa9145e4bcf01a7`；这些候选未合并。三维当前主分支 `0b9acc56e10a90515713112f6b7bd9e8071d8580`，不是 W21 的固定测试版本。
- 待验工作包：W3、W4、W7、W9、W11、W12、W13、W15、W17、W19、W20、W21。W12 暂停，等原前置关口；不要靠新增 Demo 功能绕过验收。

## 三条线并行，首轮只交一项

### Dot：MCIS 主仓、智能体与独立验收

已完成：整理并推送上述候选交付；在限定样例上复验真实 HTTP/SQLite、报表引用到 PDF/DOCX 等分项。未完成：把 W21 新三维回执与正式 MCIS 流程对上，及把仍未合并的候选做成整体可交付版本。不要把历史预检当成新回执，也不要夹带其他本地改动。

第一步：收到 AI Studio 原件后，先验压缩包和内件 SHA-256、三个输入哈希、实际 SHA、时间点及状态，再走 [固定 Git 历史复验](./HANDOFF-CLOSURE-20261125.md#w21固定-git-历史复验) 两条 MCIS 历史（`17247747272fb53623b144e199260f59d6befcbd` 和 `8d68f6fa076b7acad90fab10e95ab88c6945a018`），在隔离工作树分别验收：四时点对账；合成同案 joined 测试（8 次读 Access + 1 次草稿准备审计，`saved=false`、零 Report、无已保存绑定，不含重开）。重开另验 [固定 `afc72a1`](https://github.com/mark2wen2023/MCIS/blob/afc72a1180ae345556a85fb63a4020a476893d14/tests_acceptance/registered-trajectory-pair/REOPEN.md)，复用同一轮拉取的历史，单独重开同一个合成 SQLite 并读回 T+100 登记原件；这是 3 登记 / 8 次 Access 的独立组件测试，不是 joined 库重开或报告持久化。拿不到完整历史或浏览器字段就交差异表，不补造数据。Dot 负责审 Grokbot 的验收原件和两仓的验收记录；W21 等包时不占其他两条线，按甘特安排无依赖的 MCIS 事项。真实模型不在这轮授权范围。

### Grokbot：Linux 真浏览器验收，优先 W4

从 [候选 `3ae5166b7522f63bf39827a02341c856e394a0c9`](https://github.com/mark2wen2023/MCIS/commit/3ae5166b7522f63bf39827a02341c856e394a0c9) 开独立工作树，不从主分支起。按 [W4 复验说明](https://github.com/mark2wen2023/MCIS/blob/3ae5166b7522f63bf39827a02341c856e394a0c9/tests_acceptance/w4-synthetic-pdf-live/README.md)，用正常安全沙箱的 Chromium、已安装的 Playwright，在本机回环地址运行：

```sh
service/.venv/bin/python -I -B tests_acceptance/w4-synthetic-pdf-live/run.py \
  --repo . --browser --playwright-module /path/to/playwright --chromium /usr/bin/chromium
```

必须看实际浏览器：红页显示完成、切案/切轮不会被旧回调覆盖、受控重读蓝页、两次受控读取各一条 Access；交浏览器版本、固定 SHA、命令、退出码、日志和截图。若没有验证窄屏、真实延迟下的 A→B→A 或人工视觉，单列未验。失败时给第一条错误和复现步骤，不关沙箱、不改机器权限、不跑远程 CI。只读复验无需改代码；若必须改复验工具，只改此验收目录，推自己的候选分支。完成后再由 Dot 分配下一个无冲突关口，优先考虑 W17 真浏览器。

W4 交件后，下一项 W17：从固定产品 `29cbfe255967fc6814abafd919ed9a7485ef8710`，用 Vite 构建，再跑 **Python Playwright**（不是 W4 的 Node Playwright）：

```sh
./web/node_modules/.bin/vite build --config web/tests/evidence-page-browser/vite.config.ts
python web/tests/evidence-page-browser/check.py \
  --chromium /usr/bin/chromium --dist "$PWD/.evidence-page-browser-dist" --output /tmp/w17-browser-new
```

使用实际浏览器路径和新输出目录。退出码 0、回执 `passed=true`、`externalRequests=0` 才算这个子关口通过。1440/390 浏览器验的是证据页选择、切案、迟到响应和冲突，HTTP 是受控样例；另一个 [`a80226d`](https://github.com/mark2wen2023/MCIS/commit/a80226d7e32d79ce8ab7a035a16e5089bfbac377) 验的是真 FastAPI/SQLite 与模拟 DOM 的登记回执。两份分别记，不等于登记在真实浏览器连后端通过。

### AI Studio：三维回放与 W21 原始制品

本轮先不开发新功能。从已报告通过的三维 `de9356a4616c0ef593ffff0ca81fd959ff24c1b3` 运行中，导出原样 `four-point-clock-receipt.jsonl`、`report.json`、`SHA256SUMS` 和 12 张原图，给附件或可下载直链及包 SHA-256。补具体 Chromium 版本；原脚本在第一次打开后才开始监听，若没有独立日志覆盖首次打开，标「首次打开未采集」。不要重跑或改写原件，不重发已核对的 MCIS@2048c60f 三份样例。对账时点：T+100 / 121 / 124.250 / 127.500。

交完原件，再单独处理三维背景交通：`0b9acc5` 固定样例的水泥船端点推导约 076.4°、7.67 kn，但记录 COG/艏向 275°、中段 SOG 5.7 kn；运行采样器复现，浏览器画面未验。另有静止工程船继承机动航行默认状态。只改合成背景样例和对应回归，不改事故双船、跨仓契约或 W21 固定样例。实际浏览器验航迹、船首朝向、尾流和状态显示，再交独立候选 SHA。

## 回执、协作与通过标准

1. 马克转发下方任务，不共享账号。各自在授权环境工作；候选按仓库权限推 GitHub，原附件用有权限的渠道传，不发真实案卷、4A 数据、凭据、个人信息或付费模型请求。不合并、不部署。
2. 代码、固定 SHA、复跑命令和验收结论留 GitHub；讨论走聊天。每条回执写：任务号 / 仓库及固定 SHA / 工作区状态 / 环境与工具版本 / 命令和退出码 / 证据包链接与 SHA-256 / 未验与阻塞。只读验收原件交 Dot；需要改代码才开候选分支供审。不得把本地文件路径当交付。
3. 两小时检查点看是否有证据、明确下一步，不承诺两小时完成。单项完成即报告；Dot 独立验后更新原甘特表。阶段闭环至少要从干净工作树按清单复现，并明确何处是浏览器实跑、何处是模拟、何处待验。没有报告或原件时不写通过。

## 可直接转发的两条启动指令

**给 Grokbot：** 请在你的 Linux 独立接 W4，从固定 `3ae5166b7522f63bf39827a02341c856e394a0c9` 按上文 README 跑正常沙箱 Chromium 的真实浏览器模式，仅用随测生成的合成 PDF。回来给固定 SHA、浏览器版本、命令、退出码、截图、审计和未验项；失败就报第一条错误。先不改产品、不合并、不部署。

**给 AI Studio：** 先交固定 `de9356a4616c0ef593ffff0ca81fd959ff24c1b3` 已跑的 W21 原包（JSONL、report、SHA256SUMS、12 原图），附件或可访问链接加包哈希，标具体 Chromium 版本及首次打开网络覆盖范围。不要重跑、改写原件或同步新 SHA。交完原包后，再按本书单独处理背景交通；不动事故双船或 cross-repo 样例。
