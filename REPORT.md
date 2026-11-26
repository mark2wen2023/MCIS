# W11 撤销独立对照 — 官方验收记录

- 沿用候选 `6fe7777fbad84d60ed0854442734bebb967794b4`（`candidate/w11-isolated-synthetic-pilot`）的本机合成装配
- 只新增 `tests_acceptance/w11-isolated-synthetic-pilot/revoke_control.py`；未改 `run.py` / `server.py` / README 的固定校验，未改产品
- 报告目录：`/workspace/mcis-w11-revoke-control-report`
- 官方运行（Asia/Shanghai）：2026-11-27 04:46:06 CST → 04:46:11 CST
- 退出码：0（`timeout --signal=TERM --kill-after=10s 150s` + `unshare -r -n`，先 `ip link set lo up`）
- 监听：仅 `127.0.0.1:18766`
- HTTP 结果是 HTTP，不是浏览器结果；未跑改版分支；不是 W11 整包通过；不是正式应用验收

## 对上次表述的更正

已核 `service/mcis_service/main.py@875ccc50` SHA-256
`6859848c5a6255740bcb0bfd93609bec13d5ac9ac67b26c8cbfd44a363d10cfa`：
第 88 行 `app.include_router(ecfc_drafts_router)`，固定完整应用已挂载 ECFC 草稿路由。
上次回执写「钉扎 create_app 未挂载 ecfc_drafts_router」仅适用于隔离装配所用的 186 文件钉扎 `main.py`
（SHA-256 `2c21e58417fe208462921543762eaf3a9c81e9fd40238be44de50e5a9ff28d93`），
不等于 `875ccc50` 产品入口未挂载，也不等于产品已有原文接口。

## 执行与结果

真 .NET 使用 `mcis-ecfc.dll` SHA-256
`f548818bd21c45d640293601f2ae271171c086f7e0b22912472a2d7dc771e75a`，
`coreVersion=mcis-ecfc-draft/1`。草稿 revision=1，digest=`2d1ce99dc5ca27cbe7171c4980742975ff22977d011c6d9b943bb19d67b54c63`。

当前有效绑定显式读取 HTTP 200，`excerpt`/`sourceUtc`=`2026-02-01T12:01:49.000Z`，保管链 Register, Access。
随后用既有 `host.py` 撤销机制（`UPDATE pilot_single_source SET revoked=1 WHERE singleton=1 AND revoked=0`，WRITE_LOCK）撤销；
图版本、摘要、身份、边、片段（97–121）均未变，仅 `revoked` 0→1。
同一请求随后 HTTP 404 `SOURCE_UNAVAILABLE`；保管链仍为 Register, Access（无新增 Access）；
`audit:verify` 有效；`/sim/commands` 为空；intake `replayed=false`；ECFC 审计仅 revision 1。

未验：浏览器、正式应用验收、真实案卷、4A、归档、3D、改版分支（按派遣不跑）、W11 整包。

## 固定 SHA（提交后补记）

- 候选 `candidate/w11-isolated-synthetic-pilot`：`cf7decf37fb6e037110c1de96a83f81eb25d17fc`（其上仅新增对照脚本；父提交仍为 `6fe7777fbad84d60ed0854442734bebb967794b4`）
- 证据分支名预留：`evidence/w11-revoke-control-grokbot-cf7decf`
- 已接评论：7203025854
