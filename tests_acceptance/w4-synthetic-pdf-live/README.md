# W4 合成 PDF 页面实际服务验收

固定产品提交：`67654fd9801735dfe81361caf5e6f0148ab5e7da`。本目录只有验收工具，不改产品或工作流。使用已有 MCIS 服务 Python 和 Poppler，仓库根目录执行：

```sh
service/.venv/bin/python -I -B tests_acceptance/w4-synthetic-pdf-live/run.py --repo .
```

使用普通沙箱 Chromium 与已安装的 Playwright 时，可执行浏览器模式：

```sh
service/.venv/bin/python -I -B tests_acceptance/w4-synthetic-pdf-live/run.py \
  --repo . --browser --playwright-module /path/to/playwright --chromium /usr/bin/chromium
```

执行前核对固定产品的 180 个 Git blob。测试只在临时目录启动监听 `127.0.0.1` 的真实服务，重用实际证据登记与图像复核入口，生成一份合成 PDF，取红色第 1 页与蓝色第 2 页对照。为两次受控读取各留一条 Access，不返回 PDF，不生成 OCR、不处理案件原件，不安装依赖、不上传、不部署。退出自动清除本次临时数据。

- **已实跑**：真实进程 HTTP、SQLite、Poppler、红/蓝像素及审计，退出 0。
- **浏览器仍未验**：现有 Linux Chromium 在导航前启动失败，保留正常沙箱。浏览器脚本已做语法检查，待实际验证切案/切轮旧回调、画布和读审计；浏览器未运行或退出不为 0 均不得计为通过。
