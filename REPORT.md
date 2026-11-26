# W12 等候帧补充 — 官方验收记录

- 稳定态结果保持不变：候选 `9979c087e19e005b9251257048317b13eea421da`，证据 `73aa88bf6378893f83c4f3789ceef89f7da5971d`，回帖 7205529901，表第 48 行。本轮不替代该结果。
- 本轮只新增 `tests_acceptance/w12-snapshot-scope-browser/loading_frame.py`。`run.py` / `host.py` / `synthetic_seed.py` / `README.md` 固定校验未改。未改产品。
- 同一真实本机服务与 web，仅监听 `127.0.0.1:18770`。两案纯合成数据，标题/案号/指标不同。
- Playwright 对真实 `GET /api/v1/cases/SYN-W12-SNAP-B/analysis` 暂缓 `route.continue()`，不 fulfill、不替换响应或服务。挂起期间页面显示「正在读取当前案分析；旧分析已停用。」，无 A 案号或指标；随后放行，B 返回 200 并显示 B；切回 A 只展示 A。
- 官方运行（Asia/Shanghai）：2026-11-27 07:52:05–07:52:10 CST，退出码 0。正常沙箱 Chromium。先跑桌面 1440×900，有条件补 390×844，两次均通过。
- 不是 W12 整包。同案轨迹换版仍为未验。
