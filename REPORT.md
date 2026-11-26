# MCIS W15 浏览器原生正文读取验收候选（ad4e56e，基于 508460d）

- 执行时间：2026-11-26 15:20–15:23（北京时间，UTC+8）。Grok Bot 的 Linux 盒子。
- 独立验收候选：`candidate/w15-native-body-read` @ `ad4e56e4e1169aa0505ca5310d3f979876cb1a97`。产品代码未改，仍为切案修复 `508460d`。只改验收脚本：增加 `--native-body`（页面 fetch 钩子对同一笔真实 loopback POST 的 Response 做 clone，并限时 8 秒读取 clone）；默认命令仍走 Playwright `result.json()`，未放宽原门禁。
- 正常沙箱 Chrome 156.0.8078.47，Playwright 1.65.2，真本机回环。外层 `timeout --signal=TERM --kill-after=10s 150s`，未手发信号。未安装，未改产品、CI 或 main，未合并、未部署。未再为 503 正文追加日志。本项不是整包通过。

## 1. 原门禁命令（508460d，不加新旗标）

命令与此前相同：`timeout --signal=TERM --kill-after=10s 150s diagnose.py --source … --node-modules … --host-python … --browser … --evidence …`（无 `--native-body`、无 `--workflow-only`）。

| 项 | 结果 |
| --- | --- |
| 退出码 | **124**（外层 150s TERM） |
| receipt | 未写出 |
| 第一处停留 | `app_ui` 行 173：`assert result.json()["code"]=="BOWTIE_CORE_UNAVAILABLE"`。已见到预览 POST 的 503 头与 `cache-control=no-store`；宿主 `sent_final bytes=74`。未到达切案断言。 |

原门禁命令及其 124 保留。

## 2. 新版同门槛用例（`--native-body`）

同一真实浏览器预览 POST。页面 fetch 钩子在原 Response 返回时按精确 loopback origin 且方法为 POST 的 `/systemic/bowtie:preview` 做 `clone()`，对 clone 限时读取；原响应交回页面，未发第二笔，未兜底到宿主读取。

| 项 | 结果 |
| --- | --- |
| 退出码 | **0**（未用到 150s TERM） |
| 读取 | 一次读到正文。断言通过：HTTP 503、`cache-control=no-store`、JSON `code=BOWTIE_CORE_UNAVAILABLE` |
| 其余门槛 | 所选证据、页面报错且无假图、A→B→A 案隔离、三张原规格截图、390px 重启、SQLite 对比通过 |
| receipt | `nativeBodyVerified=true`，`bodyVerified=true`，`browserVerified=true`，`passed=false`（不是原 `result.json()` 门禁，不报整包通过） |

stdout：`W15 native browser body read and same-threshold UI/SQLite verified; original result.json() gate not this run`。
