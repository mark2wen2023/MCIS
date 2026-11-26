# W21 合成验收预检阻塞报告（Grokbot）

时间：2026-11-26 21:53 Asia/Shanghai（CST, UTC+8）
派遣：#106 comment 7193191678
已接：#106 comment 7193863761（2026-11-26 21:48 Asia/Shanghai）

本项按派遣使用 MCIS 隔离预检 `e8d86bbfce715e0725e212835eed70167f25b6c8`，从固定 `MCIS@2048c60fd6650c6f2c99a76a16be463a3895655d` 与 `mcis-3d@de9356a4616c0ef593ffff0ca81fd959ff24c1b3` 准备重跑，不找旧包。预检未过，未启动默认应用、未跑官方 runner。未改产品、未改 mcis-3d、未安装、未退沙箱、未合并、未部署。不是 W21 整包通过。

## 所用 SHA

- 隔离预检：`e8d86bbfce715e0725e212835eed70167f25b6c8`（本地 worktree `/workspace/mcis-w21-preflight`）
- MCIS：`2048c60fd6650c6f2c99a76a16be463a3895655d`
- mcis-3d：`de9356a4616c0ef593ffff0ca81fd959ff24c1b3`（私有仓 `mark2wen2023/mcis-3d`）。`GITHUB_MCIS_TOKEN` git fetch/clone 为 403；经已连接的 GitHub 只读确认该提交存在，树完整（136 条，未截断）。本机无带依赖的既有检出。未提交、未推送、未建分支、未改三维仓库任何文件。仓内旧包（如 `mcis3d-215c057e-browser-acceptance.tgz`）未取用。未碰 `/workspace/yuehai-*`。

## 预检逐项

1. Node：有。`/usr/local/bin/node` v24.22.1。
2. Playwright CLI：有。`/workspace/w17-pyplaywright-venv/bin/playwright` 1.65.2。未用 `npx` 安装。
3. Chrome 沙箱：有且可启动。Google Chrome 156.0.8078.47；`/opt/google/chrome/chrome-sandbox` mode `0o104755` uid 0。Playwright `chromium_sandbox=True`，未加 `--no-sandbox`，`launchOk=true`。
4. WebGL：有。预检页在 `127.0.0.1` 上打开，`webgl=true`，`webgl2=true`，renderer `ANGLE (Google, Vulkan 1.3.0 (SwiftShader Device (Subzero) (0x0000C0DE)), SwiftShader driver)`。截图 `preflight/webgl-probe.png`。
5. 锁定源码：MCIS 与隔离预检已在本地按固定 SHA 核对。`tests_acceptance/shared-trajectory-cross-repo-expanded` 三份文件在 `2048c60` 与 `e8d86bb` 字节一致，并与 `prepare.py` 期望摘要相符：vessel-a `a8f9109a33b8c80a6c41219473186e69c16fd59ee64ff325a5559c190028bb1c`，vessel-b `07e043fc227770b6aaa6f1b15a6118e46b85a52e5638ac1b514e9269c6b159ca`，vessel-mismatch `f785399311f5dd045eec6cc8a6a2105d95b376e9aa894342fd4da4f5985dc2f4`。mcis-3d 无本机只读 git 检出（token 403），亦无既有依赖目录。
6. 既有依赖：**缺，预检阻塞。** 本机无 `mcis-3d@de9356a` 的 `node_modules` 或 bun 依赖目录，无对应 `bun.lock` 缓存（`~/.bun` 不存在）。不得 npm/bun install 或下载。未挪用 MCIS `web/node_modules`。工程锁文件为 `bun.lock`（blob `0301fe25…`，121800 bytes）；`package.json` 脚本为 `npm install` / `npm run dev`（`tsx server.ts`）。`bun` 1.4.4 在系统中存在，但未用来安装。

## Vite 实际监听地址

未能用 ss/netstat 核实默认服务的实际监听：因既有依赖缺失不能启动，且按源码不能确保只绑定回环，已停，未启动该服务。

只读源码（`de9356a` `server.ts`）：`const PORT = Number(process.env.PORT || 3000)`，随后 `app.listen(PORT, '0.0.0.0', …)`，日志为 `Listening on http://0.0.0.0:${PORT}`。`npm run dev` 入口是该 Express+Vite（middlewareMode）服务，不是单独的 `vite` CLI。`vite.config.ts` 未设置 `server.host` / `server.port`。默认监听全部接口，不是回环。未改 mcis-3d 把地址改成 127.0.0.1。未碰线上地址（配置里的 `.run.app` / `.googleusercontent.com` 未访问）。

## 官方复跑

未启动。无退出码。第一条失败（预检停）：既有依赖缺失；且默认监听为 `0.0.0.0`，无法确保只绑定回环。

- 浏览器有效启动配置（官方 runner）：未验。预检探测见上（Chrome 156 沙箱开启）。
- 四时点两船原点/插值/缺轨：未验
- 混案拒绝：未验
- 页面首次导航起的本地/外部请求：未验
- `prepare.py` 双仓三对与派生 runner：未验（mcis-3d 侧 runner/夹具无本机检出）

已验：预检所列 Node、Playwright CLI、Chrome 沙箱、WebGL、MCIS 侧三份合成输入摘要、mcis-3d 默认监听源码。未验：官方复跑全部验收项。不是 W21 整包。
