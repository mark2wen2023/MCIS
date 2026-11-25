W4.2@b2bc858：390 窄屏长摘要完整换行并通过；1440 桌面与基线像素完全一致；布局测试退出码 0

# MCIS W4.2 窄屏预览摘要换行复验

- 执行时间：2026-11-25 19:14–19:16（北京时间，UTC+8）。Grok Bot 的 Linux 盒子，uid 1000。
- 候选：`b2bc8585747e2e754d5fdecdb60afe6b2e88b523`（2026-11-25 13:20 +0800，"Keep preview digest readable on narrow screens"），工作树 `/workspace/mcis-w42-b2bc858`。
- 基线：`3ae5166b7522f63bf39827a02341c856e394a0c9`，工作树 `/workspace/mcis-w42-base-3ae5166`。
- 两份工作树在运行前后 `git status --porcelain` 都为空。
- 产品相对基线只改了 `review.html` 一行作用域 CSS：`.image-pane #preview-status{overflow-wrap:anywhere}`。DOM 和脚本与基线字节一致。验收目录是新增的 `tests_acceptance/w42-preview-digest-layout/`。
- 没用真实案卷。本测试按 README **不启动 HTTP 监听、不访问服务、浏览器离线**，在真实 Chromium 里加载完整模板的 HTML/CSS（去掉 script），填入两段合成 64 位摘要。
- 没改产品，没改旧 W4 固定校验，没合并，没部署，没触发远程 CI。测试工具无需修改，没有另推工具分支。

## 1. 工具

Google Chrome 156.0.8078.47（`/opt/google/chrome/google-chrome`）。Node 版 Playwright 1.63.0-alpha（W4 同一 pnpm 路径）。启动参数为 `chromiumSandbox:true`，没有 `--no-sandbox`。Node v24.22.1。

## 2. 命令与退出码

在候选工作树根目录执行（按 README）：

```sh
node tests_acceptance/w42-preview-digest-layout/check.cjs \
  --baseline /workspace/mcis-w42-base-3ae5166/service/mcis_service/image_review/review.html \
  --candidate service/mcis_service/image_review/review.html \
  --playwright /usr/local/lib/pnpm/5/.pnpm/playwright@1.63.0-alpha-2026-08-31/node_modules/playwright \
  --chromium /opt/google/chrome/google-chrome \
  --out /workspace/mcis-w42-report/screenshots
```

退出码 **0**。stdout：`PASS fixed baseline and exact CSS-only change`；浏览器 156.0.8078.47。日志：`logs/01-layout-check.stdout`。

| 模式 | 宽度 | 摘要片段都在状态框内 | PNG 摘要行数 | 页面 scrollWidth |
|---|---|---|---|---|
| 基线 | 390 | 否（负对照：复现溢出，scrollWidth=650） | 1 | 650 |
| 候选 | 390 | 是 | 2（已换行） | 390（无横向溢出） |
| 基线 | 1440 | 是 | 1 | 1440 |
| 候选 | 1440 | 是 | 1（未额外换行） | 1440 |

静态门禁：基线 `review.html` 的 Git blob 为 `ae05f95847e710b0be98ee19963f833c20506138`，候选与基线的唯一差异就是上述一条 CSS。通过。

## 3. 截图与目视

官方四张（测试脚本写入，视口截图，未改脚本）：

- `screenshots/baseline-390.png`：窄屏基线，长摘要向右溢出（负对照）。
- `screenshots/candidate-390.png`：窄屏候选，页面无横向滚动。因状态栏靠近视口底部，视口截图只能看到摘要开头；度量结果是完整 192 字都在 DOM 中，PNG 摘要折成 2 行且不溢出状态框。
- `screenshots/baseline-1440.png` 与 `screenshots/candidate-1440.png`：**像素完全一致**（1296000 像素中 0 个不同，文件 SHA-256 前缀同为 `008e5515a21c235a`）。桌面布局无回归。

补充（仓库外脚本 `tooling/status-element-shot.cjs`，同样是正常沙箱 Chrome，只截 `#preview-status` 元素，便于看清换行，**不替代**上面四张官方截图）：

- `screenshots/status-element/baseline-390-status-el.png`：元素宽度内看不到完整 64 位摘要（被裁切）。
- `screenshots/status-element/candidate-390-status-el.png`：原 PDF 摘要与派生 PNG 摘要（均为 64 个十六进制字符）完整出现并换行，结尾「不是登记原图、OCR结果或事实核验。」也在框内。

## 4. 未验

- Firefox / WebKit；有界面（headed）窗口；真实触屏。
- 不在本测试范围内：启动真实服务后的在线预览、解码器、画布像素、授权与审计。旧 W4 合成 PDF 在线验收（`w4-synthetic-pdf-live`）按要求没有重跑，其固定 HTML 哈希仍指向基线，不能为了跑绿去改。

## 5. 文件

`logs/00-env.txt`、`logs/01-layout-check.*`；`screenshots/`（官方 4 张 + 补充元素截图）；`tooling/status-element-shot.cjs`。
