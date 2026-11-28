# W15 正式页面 + 原 .NET 核心成功出图联验（Grokbot）

时间：2026-11-28 09:50（北京时间，Asia/Shanghai）
派遣：#106 comment 7231546932，同单补充 7231576723
接单：#106 comment 7231869952

## 检索

同一固定版本下没有可复用的真浏览器原件覆盖「正式页面 → 真实回环 FastAPI 调用原 .NET 核心 → 页面实际出图」。已通过的原 .NET 核心（`8d10844`，`browserVerified=false`）、真实网页失败路径和移动布局（`912d96a`）均未重跑。`cbb3997` 等其他包回执不能代替本项。

## 组合核对

网页候选 `912d96a39f1a68e98008a7317a211f5e29ed3845` 与原核心验收包 `8d108442f94901bee862ba5f53dd6343350b2718` 均以产品底版 `2c72d022f3d3275af637b0cdc6e545735e3200a9` 为祖先，彼此不是包含关系。两边的 FastAPI 预览契约、`bowtie_preview/router.py`、`BowtieForm.tsx` 与核心 15 个文件 blob 一致。`912d96a` 相对底版只改了 3 个网页文件（会话不取消、390 布局 CSS、navigation）。`912d96a` 网页 host 仍故意把 .NET 指向不存在的位置；`8d10844` 正向 host 不提供网页资产。两者不能拿现成 host 直接对跑，但版本与现有连接点一致，可用新验收目录把固定网页资产和原核心组合在同一回环服务上。旧 503 门禁文件未改。

## 独立验收候选

- 分支：`candidate/w15-page-core-browser`
- 完整 SHA：`e54d6651a1d4d1d32f939ff4c92921dd8c6098b7`
- 只新增 `tests_acceptance/w15-page-core/` 四份验收文件；产品树未改，未改 CI/main，未安装、未合并、未部署。

## 正式跑

`timeout 150` 官方脚本退出码 **0**（2026-11-28 09:50 北京时间）。Google Chrome 156.0.8078.47，正常沙箱，没有 `--no-sandbox`。服务 127.0.0.1（本跑 origin `http://127.0.0.1:35767`）。.NET SDK 8.0.428。合成案 `SYN-W15-A`，来源 `EV-001` 仅作整份草稿已登记元数据。

- 真实 POST `/api/v1/cases/SYN-W15-A/systemic/bowtie:preview` HTTP **200**，`Cache-Control: no-store`；宿主与浏览器记录同一笔请求，浏览器 `requestfinished`。
- 返回 `coreVersion=mcis-bowtie/1`，`structureValid=true`，5 节点 / 4 连线，`persisted=false`，`assessment=hypothesis-structure-only`，`sourceBinding=registered-metadata-only`。
- 页面独立「核心结构核查结果 · 非事实确认」面板同次显示结构通过、临时接收节点 5 / 连线 4、输入摘要 `83c40c01aa3f47436a93ac5b9e4923afbdf256463320bd4c0f6b15497ebacee3` 与返回一致。
- 请求体为合成 5 节点模型（顶事件 + 4 节点 + 4 连线）且 `sourceEvidenceIds=["EV-001"]`。不声称节点级引用或原件核验。
- 预览前后及同一 SQLite 重启/重开后库摘要不变；重开后仍可读到来源，表单为空，无结果面板，无新的预览 POST。
- 草图 SVG 在提交前就会画，截图本身不能证明核心通了；本项以 POST 200、原核心版本和结果面板为准。

截图 `01` 与 `03` 像素相同（提交前空表与重开后空表在页面上看不出差别）；重开路径的无写入、无新预览由脚本与库摘要断言。

## 验收脚本两次修正（均未改产品、未放宽断言）

1. 首次启动服务失败：把服务 venv 的 `bin/python` 用 `resolve()` 跟到了系统 `/usr/bin/python3.13`，缺少 uvicorn。改为保留 venv 入口路径后重跑官方路径。
2. 第一次退出 0 的全页截图未滚到结果面板（应用壳层内部滚动，`full_page` 仍是 1440×900）。只增加 `scroll_into_view_if_needed()` 后重跑官方路径，本报告依据该次退出码 0 的原件。

## 未验 / 边界

此项不等于 W15 整包。未发送、未签发、未保存、未导出、未接真案。未验 Firefox/WebKit、headed。未重跑原核心关口、503 失败路径或移动布局关口。

临时 SQLite 位于 `/tmp`，不随证据打包。
