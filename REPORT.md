# W4.1 临时预览初验 — 阻塞报告（Grokbot）

时间：2026-11-26 17:21 Asia/Shanghai（CST, UTC+8）
派遣：#106 comment 7187574566
已接：#106 comment 7187756149（2026-11-26 17:18 Asia/Shanghai）

本项是临时预览初验，不是正式带锚校时、回写、迟到响应或 W4 整包。浏览器与核心实跑未开始（未验）。未改产品、未安装、未从网络拉依赖、未合并、未改 CI/main、未部署。

## 固定对象

- 脚本提交：`ce08e1d3a917b6956e3cd2279b9acc9a7b3852c9`（2026-11-26 17:11:24 +0800，`test(W4): add scoped synthetic unanchored preview browser runner`）
- 目录：`tests_acceptance/w4-synthetic-unanchored-browser/`（仅 `run.py` 与 `README.md`）
- 固定产品：`94d5e38c926fda232bb987b60fa9145e4bcf01a7`（本地 git 对象已存在：`Merge PR #91: integrate offline expert review and traceability`）
- README 要求：已有依赖 + 独立核验过的预构建 `mcis-core.dll`，经 `--core-dll` 与 `--core-sha256` 钉死字节；不构建、不安装、无兜底输出。禁用 demo seed，只建 SYN-W41-X-A/B。

## 第一处阻塞（预编译核心出处不足，未启动 run.py）

固定产品源码齐：`git cat-file -t 94d5e38…` 为 commit。McisCore.csproj 以 glob 编入 `unity/Assets/_Project/Scripts` 下 Primitives/Common/Models/Geo/Cpa/Colreg/Evidence/Timeline/Vdr 以及 `tools/mcis-core/src`，合计 56 个编译输入。这 56 个文件在 `94d5e38` 与本地 `c6113bee` 的路径集合和 Git blob 完全一致。

预编译且可证明来自该固定源码的核心 DLL **缺**：

- 官方包装路径 `tools/mcis-core/out/mcis-core.dll`（`mcis-core-norebuild.sh` 默认）在 `/workspace/*/tools/mcis-core/out/` 与 `/tmp` 均未找到。
- 仓库不跟踪该制品（`.gitignore` 忽略 `bin/` 与 core/out）。先前出处调查（`logs/core-dll-provenance-investigation.md`）亦记载 GitHub Releases/Actions 无已上传原 DLL。
- 箱上仅观察到一份未被出处绑定的文件：`/workspace/maritime-sim-design/tools/mcis-core/bin/Release/net8.0/mcis-core.dll`
  - SHA-256：`7afd120cb343a4459b1f012ea96c5ab8df53c04a4ba58b916dcc20f3d1d88337`
  - 大小 250368；mtime 2026-11-22 10:20:26 Asia/Shanghai（与大量沙箱快照文件同时戳，不能当作构建时间证明）
  - 程序集字符串中无 SourceRevisionId / 仓库提交
  - 与已记录历史制品 `b0e507b80b41f2d3a5de0dd73adac2b070dd7310e2f9c52b65a6ab44b9b652f3` 不符
  - 与同 56 项输入、PathMap、无 revision 的可复现记录 `f94197777acc45d7ff4e84f265ded9d43c32e773c17cac462d952574d77ac9cf` 不符
  - 全仓报告检索不到该 SHA
- 按派遣：不能放宽、不能拿这份未绑定出处的 DLL 开跑，也不能安装或从网络拉依赖后现场编译补缺。

因此 **未执行** `run.py`（退出码：未跑）。以下均为未验：两视口 Evidence 面板 COG 差值、未校准/不入库、A→B→A 隔离、SQLite 重开、截图。

## 已核对、但因核心阻塞未使用的现成工具链

- Chrome：`/usr/bin/google-chrome`，Google Chrome 156.0.8078.47（将用正常沙箱，未用 `--no-sandbox`）
- Python Playwright 1.65.2：`/workspace/w17-pyplaywright-venv`
- 宿主 Python：`/workspace/mcis-w17-871db66/service/.venv/bin/python`
- 现成 `web/node_modules`：`/workspace/mcis-w17-871db66/web/node_modules`
- .NET SDK 8.0.428：`/home/box/.dotnet/dotnet`（未用于本轮构建）

## 清单文件

`inventory/core-provenance.json`（含 56 项 94d5e38 blob 与对未绑定 DLL 的观察，不含 DLL 本体）。
