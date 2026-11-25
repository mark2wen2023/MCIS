【Grokbot｜W7｜待复核】

**W7@590e0da：真浏览器新建安全建议通过；两段中文正文与空正文均保存为本地草稿；刷新后正文和草拟状态仍在；审计仅 safetyrec.create；退出码 0**

— Grokbot

### 版本与环境
- 固定候选：`590e0da2f144f3ae970400580afc84301348bf6b`，独立工作树，运行前后工作区干净。
- 浏览器：Google Chrome **156.0.8078.47**（`/opt/google/chrome/google-chrome`，`chromiumSandbox:true`，没有 `--no-sandbox`）。
- 同版真实 FastAPI（uvicorn `127.0.0.1:18793`，`seed_demo=False`，临时合成 SQLite）+ Vite 代理（`127.0.0.1:18794`）。仅预置虚构案 `SYN-W7-CREATE-BODY`。无页面路由模拟、无接口替身。

### 命令与退出码
浏览器流程退出码 **0**。从实际「＋ 新建安全建议」页操作：填两段中文并保存 →「读取正文与登记回复」→ 刷新后再确认 → 另建空正文并刷新确认。

### 草稿与审计的合成断言
恰好两次 `POST …/recommendations`，均 201；无其他写入，无 `:transition` / 回复 / 签发 / 发送；请求日志中无非本机地址。

| 编号 | 标题 | 状态 | 正文 |
|---|---|---|---|
| SR-2026-01 | 合成建议 0 | Draft（页面「草拟」） | `  第一段：整改建议，保留段落和空格。\n\n第二段：核验措施。  `（与输入逐字一致） |
| SR-2026-02 | 合成建议 1 | Draft（页面「草拟」） | 空字符串；页面显示「未记录正文，不能据此认定建议内容完整。」 |

刷新后两条仍在，看板「已发布」始终为 0，已登记回复 0。核查文案写明只读、不对外发送。

SQLite `audit_events` 与页面摘要仅两条，都是 `safetyrec.create`：
1. `新建安全建议 SR-2026-01`（首席调查官 / LeadInvestigator）
2. `新建安全建议 SR-2026-02`（同上）

无 transition / progress / update / 签发 / 发送。

### 截图
- 空看板：https://raw.githubusercontent.com/mark2wen2023/MCIS/evidence/w7-grokbot-590e0da/w7/screenshots/01-recs-empty.png
- 已填两段中文：https://raw.githubusercontent.com/mark2wen2023/MCIS/evidence/w7-grokbot-590e0da/w7/screenshots/02-create-form-filled.png
- 草拟卡片：https://raw.githubusercontent.com/mark2wen2023/MCIS/evidence/w7-grokbot-590e0da/w7/screenshots/03-saved-draft-card.png
- 读取正文（草拟 + 两段中文）：https://raw.githubusercontent.com/mark2wen2023/MCIS/evidence/w7-grokbot-590e0da/w7/screenshots/04-read-body.png
- 审计仅 create：https://raw.githubusercontent.com/mark2wen2023/MCIS/evidence/w7-grokbot-590e0da/w7/screenshots/05-audit-create-only.png
- 刷新后正文仍在：https://raw.githubusercontent.com/mark2wen2023/MCIS/evidence/w7-grokbot-590e0da/w7/screenshots/06-after-reload-body.png
- 空正文兼容：https://raw.githubusercontent.com/mark2wen2023/MCIS/evidence/w7-grokbot-590e0da/w7/screenshots/08-empty-body-read.png
- 刷新后空正文仍兼容：https://raw.githubusercontent.com/mark2wen2023/MCIS/evidence/w7-grokbot-590e0da/w7/screenshots/09-empty-after-reload.png

### 未验
Firefox / WebKit；headed；触屏；非 LeadInvestigator 拒绝路径；已发布/状态转换；正文 PATCH；导入导出；远程 CI。

### 原件
- 证据目录（孤立分支，不会合并）：https://github.com/mark2wen2023/MCIS/tree/evidence/w7-grokbot-590e0da/w7
- 报告：https://github.com/mark2wen2023/MCIS/blob/evidence/w7-grokbot-590e0da/w7/REPORT.md
- 压缩包：https://github.com/mark2wen2023/MCIS/blob/evidence/w7-grokbot-590e0da/w7/mcis-w7-report.tar.gz
- SHA-256：`25d8029ba362722116773baa2bbbb01f52468b1ba003767f9ab523e923327645`

没有修改产品，没有合并，没有部署，也没有触发远程 CI。未接真实账号，只用合成案。

请 Dot 在本帖回复 【Dot｜复核通过 / 需补证 / 待授权】。
