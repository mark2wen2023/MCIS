# W3 现有笔录定位入口的键盘可用性（真浏览器门槛）

独立验收候选，底版为 `d4452bb6c8aac41f2ce99c157b02a7e501f4f4ba`，并沿用 `8af8f3e` 已登记的同一份固定合成笔录准备方式。
只新增本目录验收工装。不改产品、权限、契约、数据、主线或 CI。不重跑 `8af8f3e` 的时间匹配或已通过的证据来源内容测试。不是 W3 整包。

## 范围

用正式询问笔录比对页与真实本机服务（临时 SQLite、`seed_demo=False`），经官方写入接口准备与 `8af8f3e` 相同的一份合成登记笔录。再用正常沙箱 Chrome，**只通过键盘**从现有「定位问答」入口走到已定位问答，核：

1. 入口可用键盘到达；
2. 定位后 `document.activeElement` 与视觉焦点落在原问答（第 2 轮，原文回答仍在）；
3. 继续 Tab 仍能把焦点移到当前页上的可操作控件，且不离开本页、不触发写入。

若没有可键盘到达的入口，记录首次断点后结束，不改产品。

## 运行

```sh
timeout 150 /workspace/w17-pyplaywright-venv/bin/python -B tests_acceptance/w3-transcript-keyboard/run.py \
  --node-modules /workspace/mcis-w15-layout-cand/web/node_modules \
  --host-python /workspace/mcis-w17-871db66/service/.venv/bin/python \
  --browser /opt/google/chrome/google-chrome \
  --evidence /workspace/mcis-w3-transcript-keyboard-report
```

服务与页面只监听 127.0.0.1。Chrome 开沙箱，不使用 `--no-sandbox`。
