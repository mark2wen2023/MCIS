W7@590e0da：真浏览器新建安全建议通过；两段中文正文与空正文均保存为本地草稿；刷新后正文和草拟状态仍在；审计仅 safetyrec.create；退出码 0

# MCIS W7 建议正文真浏览器验收

- 执行时间：2026-11-25 20:17–20:27（北京时间，UTC+8）。Grok Bot 的 Linux 盒子。
- 固定候选：`590e0da2f144f3ae970400580afc84301348bf6b`（2026-11-25 20:08:03 +0800，“Allow optional safety recommendation body when creating a draft”），独立工作树 `/workspace/mcis-w7-590e0da`。运行前后 `git status --porcelain` 为空。
- Chrome：Google Chrome 156.0.8078.47（`/opt/google/chrome/google-chrome`）。Playwright 以 `chromiumSandbox:true` 启动，进程参数中没有 `--no-sandbox` / `--disable-setuid-sandbox`。
- 后端：同版 `create_app` + uvicorn，仅监听 `127.0.0.1:18793`，`seed_demo=False`，临时 SQLite `/workspace/mcis-w7-report/target-data/mcis.db`。仅预置一个虚构合成案 `SYN-W7-CREATE-BODY`（标题「合成 W7 建议正文案」），不含建议。
- 前端：同工作树 Vite，仅监听 `127.0.0.1:18794`，代理到上述后端。无 `page.route` 替身，无接口模拟。
- 未改产品，未合并，未部署，未触发远程 CI，未接真实账号。

## 1. 命令与退出码

```sh
# 空白目标库 + 合成案
python tooling/empty_server.py --repo <worktree> --data <data> --port 18793 --case SYN-W7-CREATE-BODY
# Vite
MCIS_API=http://127.0.0.1:18793 node web/node_modules/vite/bin/vite.js --host 127.0.0.1 --port 18794 --strictPort
# 真浏览器
node tooling/browser_flow.cjs <playwright> /opt/google/chrome/google-chrome \
  http://127.0.0.1:18794 screenshots logs/04-browser.json
```

浏览器流程退出码 **0**。浏览器 156.0.8078.47。页面角色为首席调查官（LeadInvestigator）。路径：实际「＋ 新建安全建议」页填写两段中文并保存 → 读取正文与登记回复 → 刷新后再次确认 → 另建一条空正文并刷新确认。

## 2. 草稿与审计的合成断言

写入恰好两次 `POST /api/v1/cases/SYN-W7-CREATE-BODY/recommendations`，均 201，无其他 POST/PUT/PATCH/DELETE，无 `:transition` / 回复 / 签发 / 发送。请求日志中没有指向非 `127.0.0.1` 的外部地址。

| 编号 | 标题 | 状态 | 正文 |
|---|---|---|---|
| SR-2026-01 | 合成建议 0 | Draft（页面「草拟」） | `  第一段：整改建议，保留段落和空格。\n\n第二段：核验措施。  `（与输入逐字一致，含首尾空格与空行） |
| SR-2026-02 | 合成建议 1 | Draft（页面「草拟」） | 空字符串。页面显示「未记录正文，不能据此认定建议内容完整。」 |

SQLite 与页面「完整内容核查」刷新前后一致。看板「已发布」始终为 0。已登记回复 0 条。核查文案写明「仅读取…不编辑、不对外发送。已发布只是本地状态，不证明已送达。」

审计（库表 `audit_events` 与页面摘要）仅两条，都是 `safetyrec.create`：

1. `新建安全建议 SR-2026-01`，操作者「首席调查官」，LeadInvestigator
2. `新建安全建议 SR-2026-02`，同上

无 `safetyrec.transition` / `progress` / `update`，无签发或发送。建议文档自身 `history` 仍为空数组（创建审计写在审计链，不预填状态机历史）。

受控日志：`logs/04-browser.json`（真实 `/api` 响应）、`logs/05-db-audit.json`、`logs/02-backend.log`、`logs/03-vite.log`。

## 3. 截图

- `screenshots/01-recs-empty.png`：进入合成案，看板为空
- `screenshots/02-create-form-filled.png`：新建表单已填两段中文正文
- `screenshots/03-saved-draft-card.png`：SR-2026-01 出现在「草拟」列
- `screenshots/04-read-body.png`：完整内容核查，状态草拟，两段正文，回复 0
- `screenshots/05-audit-create-only.png`：该建议审计摘要仅 `#1 · 新建安全建议` / `safetyrec.create`
- `screenshots/06-after-reload-body.png`：刷新后正文与草拟仍在
- `screenshots/07-empty-body-form.png`：空正文新建表单
- `screenshots/08-empty-body-read.png`：SR-2026-02 草拟，空正文兼容说明
- `screenshots/09-empty-after-reload.png`：刷新后空正文兼容仍在
- `screenshots/10-first-rec-still-present.png`：再点开第一条，两段正文仍在

## 4. 未验

- Firefox / WebKit；headed；触屏。
- 非 LeadInvestigator 的拒绝路径；已发布/发送/状态转换（本轮明确要求不走到签发）。
- 正文编辑（PATCH）、导入/导出、远程 CI。

## 5. 文件

`logs/00-env.txt`、后端/Vite/浏览器/库断言日志；`tooling/empty_server.py`、`browser_flow.cjs`；`screenshots/`；`target-data/`（合成库）。
