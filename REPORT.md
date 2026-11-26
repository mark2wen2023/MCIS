# MCIS W15 切案最小产品修复候选（508460d，基于 b46401a，验收脚本回到 034bff8）

- 执行时间：2026-11-26 14:50–14:56（北京时间，UTC+8）。Grok Bot 的 Linux 盒子。
- 隔离候选：`candidate/w15-caseswitch-hashchange-session` @ `508460d4b440617d71e7571f46f1235ed4d5b55d`。底版诊断提交 `b46401aedd55f30504757338d040376e565aed03`；验收/诊断文件已恢复为 `034bff8b1a72aba9c296e13615d637b90d1c3d47`，不保留 b46401a 临时埋点。
- 未加重试、未延长等待、未换掉原 hash 路径。正常沙箱 Chrome 156.0.8078.47，Playwright 1.65.2，真本机回环。外层 `timeout --signal=TERM --kill-after=10s 150s`，未手发信号。未安装，未改 CI 或 main，未合并、未部署。本项不是整包通过。

## 1. 有界对照（一次，不进入修复候选）

同页 hash 跳到 SYN-W15-B 时顺序为：案 A 的 effect 清理（hash 已是 B）→ 案 B 会话在目的地址启动并发出来源 GET → 后到的全局 `hashchange` → `leave nav session=SYN-W15-B hashCase=SYN-W15-B stillHere=true` → 该 GET `requestfailed` / `net::ERR_ABORTED`。不是案 B 的 effect 清理取消了请求。

判定：**后到的 `hashchange` 全局导航回调，取消了已在目的地址启动的新会话。**

## 2. 产品差异（只修有证据的这一处）

- `web/src/packages/navigation.ts`：`onPackageNavigation` 增加可选 `stillHere`。同页链接点击仍立即取消（此时 URL 尚未变，会话正在离开）；`popstate`/`hashchange` 仅在会话已经离开时取消；`pagehide` 仍取消。未传 `stillHere` 的既有调用点行为不变。
- `web/src/pages/SystemicPage.tsx`：传入 `stillHere` 为当前 hash 案号等于本会话 `caseId`。身份变更仍走原来的 `cancel`；effect 清理仍中止旧会话；`active && caseIdentity()===who` 仍防止旧结果回填。
- `tests_acceptance/w15-source-chromium/pins.json`：仅更新上述两份产品文件的 blob 针。固定校验逻辑未改。`product` 基线仍为 `2c72d02`（其余 337 个针不变）。
- 验收脚本与 034bff8 字节一致；`run.py` SHA-256 仍为 `c5f750fc1d17e1842196bfb36f4f751c58caf57b7e732e2a4f1150d9b340f5eb`。

## 3. `--workflow-only`（范围内复验，不是整包）

| 项 | 结果 |
| --- | --- |
| 退出码 | **0**（未用到 150s TERM） |
| receipt | `workflowVerified=true`，`bodyVerified=false`，`browserVerified=false`，`passed=false` |
| 断言 | 原 A→B→A、三张原规格截图、390px 重启、SQLite 对比均通过 |

stdout：`W15 scoped browser UI and real SQLite restart verified; response body and full gate not verified`。

## 4. 原门禁（不加 `--workflow-only`）

| 项 | 结果 |
| --- | --- |
| 退出码 | **124**（外层 150s TERM） |
| receipt | 未写出（进程在 Playwright `result.json()` 处卡住后被外部超时终止） |
| 第一处失败 | `app_ui` 行 173：`assert result.json()["code"]=="BOWTIE_CORE_UNAVAILABLE"`。已见到预览 POST 的 503 头，未再为正文单独打日志。本跑未到达切案断言。 |

原门禁仍未通过，不能报成整包通过。切案修复由 `--workflow-only` 路径验证。
