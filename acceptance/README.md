# W3 登记笔录精确 UTC 定位 + 已确认比对回跳（真浏览器门槛）

独立验收候选，底版为原甘特固定候选 `d4452bb6c8aac41f2ce99c157b02a7e501f4f4ba`。
不改产品、权限、主线、CI 或合同。不是 W3 整包，也不是 W12，也不重复 `6a231db` / 表格第 14 行的草稿冲突。

## 范围

用正式询问笔录比对页与真实本机服务（临时 SQLite、`seed_demo=False`），经官方写入接口准备**一份**合成登记笔录：

- 登记证据只提交合成 `sha256`，不上传、不读取原件字节。
- 空草稿绑定该 `evidenceId`，由服务端写入 `sourceSha256`。
- 追加三轮问答（一轮无时间、一轮唯一整秒 UTC、一轮毫秒 UTC）。
- 在唯一整秒那一轮登记一条陈述并完成重新比对 + 确认。

再用正常沙箱 Chrome 打开正式页面，验：

1. 唯一准确 UTC 可定位原问答；
2. 无同刻不猜近点；
3. 已确认且唯一的比对可跳回该轮；
4. 界面写明这是笔录问答时间，不是事故或录音时点；
5. 不生成引文，不读取原件。

以当前服务能合法提供的合成状态为准。浏览器结果不得用 DOM 模拟或纯 HTTP 冒充。

## 运行

在候选工作树根目录，现成服务 Python 启动宿主，现成 Playwright venv 跑浏览器。外层有界 150 秒：

```sh
timeout 150 env \
  MCIS_HOST_PYTHON=<existing service .venv/bin/python> \
  MCIS_PLAYWRIGHT_PYTHON=/workspace/w17-pyplaywright-venv/bin/python \
  MCIS_CHROMIUM=/opt/google/chrome/google-chrome \
  MCIS_NODE_MODULES=<existing web/node_modules> \
  MCIS_BROWSER_EVIDENCE_DIR=<abs evidence dir> \
  /workspace/w17-pyplaywright-venv/bin/python tests_acceptance/w3-transcript-utc/run.py
```

服务与 Vite 只监听 127.0.0.1。Chrome 开沙箱，不使用 `--no-sandbox`。
