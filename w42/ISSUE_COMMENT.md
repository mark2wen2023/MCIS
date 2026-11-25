【Grokbot｜W4.2｜待复核】

**W4.2@b2bc858：390 窄屏长摘要完整换行并通过；1440 桌面与基线像素完全一致；布局测试退出码 0**

— Grokbot

### 版本
- 候选（固定）：`b2bc8585747e2e754d5fdecdb60afe6b2e88b523`，独立工作树，运行前后工作区干净。
- 基线：`3ae5166b7522f63bf39827a02341c856e394a0c9`，同样是独立工作树。
- 产品只增加一条作用域 CSS：`.image-pane #preview-status{overflow-wrap:anywhere}`。DOM 和脚本与基线一致。未改旧 W4 固定校验。

### 命令与退出码
按 `tests_acceptance/w42-preview-digest-layout/README.md`，用正常沙箱 Chrome 156.0.8078.47（`/opt/google/chrome/google-chrome`，`chromiumSandbox:true`，没有 `--no-sandbox`）：

```
node tests_acceptance/w42-preview-digest-layout/check.cjs \
  --baseline <3ae5166>/service/mcis_service/image_review/review.html \
  --candidate service/mcis_service/image_review/review.html \
  --playwright <已安装 playwright> --chromium /opt/google/chrome/google-chrome \
  --out <新截图目录>
```

退出码 **0**。静态门禁通过（基线 blob `ae05f958…`，候选仅为上述一条 CSS）。浏览器度量：

| 模式 | 宽度 | 摘要在状态框内 | PNG 摘要行数 | scrollWidth |
|---|---|---|---|---|
| 基线 | 390 | 否（负对照，溢出 650） | 1 | 650 |
| 候选 | 390 | 是 | 2 | 390 |
| 基线 | 1440 | 是 | 1 | 1440 |
| 候选 | 1440 | 是 | 1 | 1440 |

1440 两张官方截图像素完全一致（0 个像素不同）。

本测试按 README 不启动服务、浏览器离线，在真实 Chromium 中加载模板并填入合成 64 位摘要；不是 DOM 模拟。

### 截图
- 基线 390（溢出负对照）：https://raw.githubusercontent.com/mark2wen2023/MCIS/evidence/w42-grokbot-b2bc858/w42/screenshots/baseline-390.png
- 候选 390（视口）：https://raw.githubusercontent.com/mark2wen2023/MCIS/evidence/w42-grokbot-b2bc858/w42/screenshots/candidate-390.png
- 基线 1440：https://raw.githubusercontent.com/mark2wen2023/MCIS/evidence/w42-grokbot-b2bc858/w42/screenshots/baseline-1440.png
- 候选 1440：https://raw.githubusercontent.com/mark2wen2023/MCIS/evidence/w42-grokbot-b2bc858/w42/screenshots/candidate-1440.png
- 补充（元素截图，便于看清窄屏换行，不替代上面四张）：https://raw.githubusercontent.com/mark2wen2023/MCIS/evidence/w42-grokbot-b2bc858/w42/screenshots/status-element/candidate-390-status-el.png 可见完整 64+64 位摘要换行；https://raw.githubusercontent.com/mark2wen2023/MCIS/evidence/w42-grokbot-b2bc858/w42/screenshots/status-element/baseline-390-status-el.png 为基线裁切。

### 未验
Firefox / WebKit；有界面窗口；真实触屏；启动真实服务后的在线预览与解码/审计（不在本布局测试范围内）。旧 W4 在线验收未重跑。

### 原件
- 证据目录（孤立分支，不会合并）：https://github.com/mark2wen2023/MCIS/tree/evidence/w42-grokbot-b2bc858/w42
- 报告：https://github.com/mark2wen2023/MCIS/blob/evidence/w42-grokbot-b2bc858/w42/REPORT.md
- 压缩包：https://github.com/mark2wen2023/MCIS/blob/evidence/w42-grokbot-b2bc858/w42/mcis-w42-report.tar.gz
- SHA-256：`747c6f43273995894533a254fcaedc3d57797e5bb38c659427ae12e348f02c27`

没有修改产品或测试工具，没有合并，没有部署，也没有触发远程 CI。

请 Dot 在本帖回复 【Dot｜复核通过 / 需补证 / 待授权】。
