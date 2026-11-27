# W7 同一页面切轮/刷新（真浏览器门槛）

独立验收候选，底版为原甘特固定候选 `cbb3997ccb9f948b9762c7954fde21d8d9b275d7`。
该提交原先只有 Happy DOM 模拟，不能当成真浏览器证据。本目录只新增验收工装，不改产品、权限、主线、CI 或合同。不是 W7 整包，也不是 W12 或 W3 整包，也不重复 `0092734` 期限/重开。

## 范围

用正式「安全建议与报告」页上的征求意见面板与真实本机服务（临时 SQLite、`seed_demo=False`），经官方写入接口预先登记**一案两轮**合成记录；浏览器验证期间只读：同一实际页面切轮或刷新，确认当前轮的内容与来源不混旧。不发征求意见、不中途写库，不让脚本捏造响应。

若能在既有入口叠放第二次真实只读读取：延迟旧轮真实响应，当前轮显示后旧响应完整抵达仍不回填。若请求被取消，如实记录，不算收到防护。

## 运行

```sh
timeout 150 env \
  MCIS_HOST_PYTHON=<existing service .venv/bin/python> \
  MCIS_CHROMIUM=/opt/google/chrome/google-chrome \
  MCIS_NODE_MODULES=<existing web/node_modules> \
  MCIS_BROWSER_EVIDENCE_DIR=<abs evidence dir> \
  /workspace/w17-pyplaywright-venv/bin/python tests_acceptance/w7-round-switch/run.py
```

服务与 Vite 只监听 127.0.0.1。Chrome 开沙箱，不使用 `--no-sandbox`。
