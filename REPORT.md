# W12 首批已登记输入试点

官方 2026-11-27 10:58:40–10:58:42 CST，`timeout 150s` + `unshare -r -n`，仅 127.0.0.1:18774，临时 SQLite，退出 0。针 `03a8e786`。只新增 `tests_acceptance/w12-first-registered-pilot/`。未改产品接口、W10.2、算法或权限。未调用 `state_at` / `GET /cpa`。

三项均通过：共同覆盖内 t=10 同刻样本经官方 `mcis-core cpa` 两次结果一致，并带回两份 `previewDigest`；覆盖外（t=0/15/30/40）不返回指标；缺一船回执不返回当前分析。6–7 秒缺口跨越未验。不是同案换版，不是浏览器验收，不是 W12 整包。
