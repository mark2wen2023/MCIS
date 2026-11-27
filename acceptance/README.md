# W19 现有页面检索验收（关键词查已审核知识卡→核对原出处）

独立验收候选，底版为 `94d5e38c926fda232bb987b60fa9145e4bcf01a7`。
该提交已含正式知识库页上的字面关键词检索与出处展示，以及真实 `GET /api/v1/knowledge/cards` 服务。
本目录只新增验收工装，不改产品、权限、主线、CI、合同，不增控件、接口或模型。
不是 W19 整包，也不是 W12 或 W7 整包。
不重复 `8183226` 模板变更、`9d7d843` 发布/撤回工作流，也不单独再跑 `a3a593f` / `b085fc3` 的真实 HTTP 关键词对照（那些不是真浏览器证据）。

## 范围

用正式「知识库」页与真实本机服务（临时 SQLite、`seed_demo=False`），经官方写入接口预先放入合成已审核、未审核和撤回记录；浏览器验证期间只读：

- 检索唯一词，定位准确的已审核卡片与原始出处；
- 另一个缺词显示空，且不残留上一轮的旧卡；
- 两种页面结果能和同次实际请求对应。

没有入口、只能模拟或需要越过既有边界时，应停在首个源码断点，不造成功。

## 运行

在候选工作树根目录，现成服务 Python 启动宿主，现成 Playwright venv 跑浏览器。外层有界 150 秒：

```sh
timeout 150 env \
  MCIS_HOST_PYTHON=<existing service .venv/bin/python> \
  MCIS_CHROMIUM=/opt/google/chrome/google-chrome \
  MCIS_NODE_MODULES=<existing web/node_modules> \
  MCIS_BROWSER_EVIDENCE_DIR=<abs evidence dir> \
  /workspace/w17-pyplaywright-venv/bin/python tests_acceptance/w19-page-search/run.py
```

服务与 Vite 只监听 127.0.0.1。Chrome 开沙箱，不使用 `--no-sandbox`。
