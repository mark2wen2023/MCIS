W20 笔录草稿：真浏览器通过（固定验收 b0d2917 官方脚本 --build-only 与浏览器运行均为退出码 0；376 针与产品底版 e15f982 一致；未改工装、未改产品）。合成模型替身不算真模型。

# MCIS W20 当前来源人工确认真浏览器验收

- 执行时间：2026-11-26 01:42–01:44（北京时间，UTC+8）。Grok Bot 的 Linux 盒子。
- 固定验收：`b0d291788d9167365ab72be873c9871265b96807`（2026-11-26 01:21:37 +0800，“test(W20): add a pinned browser gate for current-source review”）。相对产品底版仅新增 `tests_acceptance/w20-chromium/{README.md,component.tsx,host.py,pins.json,run.py}`。本轮按该提交原脚本跑通，未再改验收文件，也未改产品。
- 产品底版：`e15f98267936bb2ba26a1a8c845df7410db8c8d1`（2026-11-25 20:22:15 +0800，“Bind manual statement confirmation to the current visible transcript”）。
- 独立工作树 `/workspace/mcis-w20-b0d2917` 作为 `--source`。`pins.json` 中 376 个固定文件（73 contracts + 146 service + 156 web + 1 `tests_acceptance/w20-visible-context/check_service.py`）与工作树及底版 Git blob 逐一对照，全部一致。
- Chrome：Google Chrome 156.0.8078.47（`/opt/google/chrome/google-chrome`）。官方脚本以 `chromium_sandbox=True` 启动，没有 `--no-sandbox`。现成 Python Playwright 1.65.2（支持 `route_web_socket`），CPython 3.13.5，未新装依赖。
- 试验宿主仅监听 127.0.0.1；临时 SQLite。页面请求限制在该回环源，拒绝 WebSocket 与 Service Worker。仅合成案。宿主使用受控本地 fixture 代替模型推理（`controlled-fake-not-real-model`），禁止出站套接字；这不是真模型验收。未跑、也未把 `--http-only` 写成真浏览器通过。
- 未改产品，未合并，未部署，未触发远程 CI，未安装任何软件。

## 1. 固定核对与构建

```sh
<existing python-with-playwright> -B tests_acceptance/w20-chromium/run.py \
  --source <worktree b0d2917> --node-modules <existing web/node_modules> --build-only
```

退出码 **0**。打印 `W20 pins: 376 exact Git blobs at e15f982…`，`Built app JS bytes=4598250`，`Built component JS bytes=686981`。日志：`logs/01-build-only.*`。

## 2. 真浏览器（两条路径分开记录）

```sh
<existing python-with-playwright> -B tests_acceptance/w20-chromium/run.py \
  --source <worktree> --node-modules <existing web/node_modules> \
  --host-python <existing service .venv/bin/python> \
  --browser /opt/google/chrome/google-chrome \
  --evidence <absent abs dir>
```

退出码 **0**。`receipt.json`：`result=passed`，`trueBrowser=true`，`browserVersion=Google Chrome 156.0.8078.47`，`browserSandboxRequested=true`，`httpOnly=false`。

- DraftReview 合成组件（无服务写入）：7 个本地 prop 场景。原文缺失时勾选与「确认以上陈述并写回」均禁用，提示「当前可见原文缺失此引用或有多处匹配…不能确认。」变化场景取消已勾选；恢复 baseline 后须重新勾选才能本地回调一次。此路径不证明当前受保护笔录 API 会产出这些 props。
- 实际笔录页＋回环服务（1440）：提取待审草稿后，服务追加一轮合成原文，确认写入返回 409 `SOURCE_CHANGED`，无陈述提交，草稿仍「待人工审核」，仅一次 review POST。
- 同一临时 SQLite 重启后，390×844 新会话：同一草稿仍待审、复选框未勾、确认按钮禁用、零陈述、无 review POST。390 仅为读回，不是完整响应式签收。

日志：`logs/02-browser.*`、`logs/02-browser-receipt.json`。

## 3. 截图

官方脚本写出的三张合成页截图：

- `screenshots/01-component-missing.png`：组件「missing」场景，不能确认
- `screenshots/02-product-source-changed.png`：1440 笔录页，原文已追加第 2 轮（官方断言 409 / 仍待审；该壳层未把审核条拉进视口）
- `screenshots/03-product-reopened.png`：390 重启后仍待审、未勾选、零陈述

## 4. 现成 SDK 只读核对（W20 完成之后，未安装、未 restore、未跑 C#）

`dotnet` 不在 PATH。盒子上已有 `/home/box/.dotnet/dotnet`：.NET SDK **8.0.428**，运行时 Microsoft.NETCore.App / Microsoft.AspNetCore.App **8.0.34**（linux-x64），无额外 workload。既有 W11/W17 示例工程 `unity/DotnetTests/Mcis.Pure.csproj` 的 TargetFramework 为 `netstandard2.1`，该 SDK 从版本上看可以承载，但本轮没有执行 restore 或 `dotnet test`，因此 **W17/W11 的 C# 关口仍为未验**。此前 W11 单边原文与 W17 真浏览器关口走的是 Python/Node + Chrome，并不依赖此 SDK。

## 5. 未验

Firefox / WebKit；headed；完整响应式；真实模型或真实案卷；远程 CI。`--http-only` 未跑，也不算真浏览器。合成模型 fixture 不算真模型。W17/W11 C# 未跑。

## 6. 文件

`logs/00-env.txt`、构建与浏览器原始日志、`receipt.json`、SDK 盘点 `logs/03-sdk-inventory.txt`；`screenshots/`；`browser-out/`。
