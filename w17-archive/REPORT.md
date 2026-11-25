W17归档@d40e3b5：真浏览器一次导入通过；预检/回执版本 1.4.0、案号 CASE-INTAKE、包 SHA-256 一致；进入新案读回两条合成时间线；退出码 0

# MCIS W17 归档真实浏览器验收

- 执行时间：2026-11-25 19:52–19:59（北京时间，UTC+8）。Grok Bot 的 Linux 盒子。
- 固定候选：`d40e3b5fd2e208af84c84d6faf61095d0a0a89fb`（2026-11-25 19:17:55 +0800，“Integrate bounded timeline archive and intake on fixed custody baseline”），独立工作树 `/workspace/mcis-w17-archive-d40e3b5`。运行前后 `git status --porcelain` 为空。
- Chrome：Google Chrome 156.0.8078.47（`/opt/google/chrome/google-chrome`）。Playwright 以 `chromiumSandbox:true` 启动，进程参数中没有 `--no-sandbox` / `--disable-setuid-sandbox`。
- 后端：同版 `create_app` + uvicorn，仅监听 `127.0.0.1:18791`，`seed_demo=False`，目标库 `/workspace/mcis-w17-archive-report/target-data/mcis.db` 导入前各表为空。
- 前端：同工作树 Vite 开发服务，仅监听 `127.0.0.1:18792`，`MCIS_API=http://127.0.0.1:18791` 同源代理。无页面路由模拟、无接口替身。
- 合成 1.4 包由同仓测试助手生成（不是页面导入）：`tests.test_bounded_timeline_archive_increment.populate` / `exported`，以及 `tests.test_working_record_archive.client_at`。源库与目标库分离。包内两条时间线：`TE-01`「Synthetic 1」、`TE-02`「Synthetic 2」。标注虚构/合成。
- 未改产品，未合并，未部署，未触发远程 CI，未接真实账号。

## 1. 合成包

命令：`service/.venv` 的 Python（3.13，uvicorn 0.54.0，fastapi 0.165.0）执行 `tooling/gen_package.py`。退出码 **0**。

| 字段 | 值 |
|---|---|
| 案号 | `CASE-INTAKE` |
| 案件包版本 | `1.4.0` |
| 包 SHA-256 | `18c3d29a91d641691f01a9a6dc7f9db8effe733afe469f0637f668416da14a98` |
| 字节数 | 8598 |
| 事件 | TE-01 Synthetic 1（timeSec=1）；TE-02 Synthetic 2（timeSec=2） |

原件：`fixtures/synthetic-1.4.mcase`、`fixtures/expected.json`。日志：`logs/01-gen-package.stdout`。

## 2. 真实页面流程与退出码

```sh
node tooling/browser_flow.cjs \
  <playwright> /opt/google/chrome/google-chrome \
  http://127.0.0.1:18792 \
  fixtures/synthetic-1.4.mcase fixtures/expected.json \
  screenshots logs/04-browser.json
```

退出码 **0**。浏览器 156.0.8078.47。角色在页面上选为首席调查官（LeadInvestigator）。步骤：选择文件 → 上传并预览 → 人工勾选确认（勾选前「确认首次导入」不可点）→ 仅一次导入（`intakes:commit` POST 恰好 1 次，`replayed=false`）→ 「进入导入案件」读回时间线。

预检与回执（真实 HTTP 及页面 DOM）均为：

- 版本 `1.4.0`
- 案号 `CASE-INTAKE`
- 包 SHA-256 `18c3d29a91d641691f01a9a6dc7f9db8effe733afe469f0637f668416da14a98`

进入新案后 `GET /api/v1/cases/CASE-INTAKE/timeline` 返回上述两条合成事件。页面时间线图可见两个事件点，并标出「Synthetic 1」（两点靠近，ECharts `hideOverlap` 可能遮住「Synthetic 2」标签；两条事件以响应正文和两枚图上标记核对）。

受控日志：`logs/04-browser.json`（记录真实 `/api` 响应，没有 `page.route` 替身）、`logs/02-backend.log`、`logs/03-vite.log`。

## 3. 截图

流程（视口 1440×900）：

- `screenshots/01-lobby-lead.png`：大厅，已切换 LeadInvestigator
- `screenshots/02-file-selected.png`：已选 `synthetic-1.4.mcase`（8598 字节）
- `screenshots/03-preview.png`：预检可见案号 `CASE-INTAKE` 与包 SHA-256（版本字段在内层滚动区下方；DOM 已读到 `1.4.0`）
- `screenshots/04-confirmed.png`：已人工勾选确认
- `screenshots/05-receipt.png`：已核验服务端导入回执，案号与 SHA-256
- `screenshots/06-timeline.png`：新案 `CASE-INTAKE` 时间线，两个事件点，标签「Synthetic 1」
- `screenshots/07-timeline-hover.png`：同页补拍（未额外打出第二条标签）

补充（只读，不再次导入）：

- `screenshots/08-receipt-block.png` 与 `08-receipt-version-scrolled.png`：按 SHA 只读回执，滚动后可见「案件包版本：1.4.0」、案号、包 SHA-256。因是导入后的查询，回执标明「已存在的同包回执」；首次导入的 HTTP 回执为 `replayed=false`。

## 4. 未验

- Firefox / WebKit；有界面（headed）窗口；真实触屏。
- 除 LeadInvestigator 以外的角色（页面说明默认 Investigator 无 1.4.0 原文恢复权限，本轮未测拒绝路径）。
- 第二次导入、导入后再次归档导出、解码器以外的业务页。
- 远程 CI。

## 5. 文件

`logs/00-env.txt`、生成/后端/Vite/浏览器日志；`fixtures/`；`tooling/gen_package.py`、`empty_server.py`、`browser_flow.cjs`（及只读补拍脚本）；`screenshots/`。
