# W19 现有页面关键词检索（真浏览器通过）

- 检索：未发现覆盖「现有实际页面：关键词查已审核知识卡并核对原出处」的等价真 Chrome 证据。`8183226` / GB-9 是模板变更/来源保护，`9d7d843` / GB-7 是发布/撤回工作流，均未重跑、未充数。`eeb7a2a` 与 `a3a593f` / `b085fc3` 已过真实 HTTP 关键词对照，但报告写明未验浏览器，本单不单独再跑那些 HTTP 对照，也不把它们当成真浏览器证据。
- 底版：`94d5e38c926fda232bb987b60fa9145e4bcf01a7`
- 候选 `candidate/w19-page-search-browser`：`d70a824fe13d2324ba4e94091fcb240708e00934`
- 只新增 `tests_acceptance/w19-page-search/` 三份验收文件，未改产品、权限、CI、契约或主线，未增控件、接口或模型。
- 现有正式知识库页 `#/knowledge` 已有「字面关键词」检索框、检索按钮，卡片可展开「正文、出处与适用限制」核对应出处。现有控件与真实本机服务已连通，因此用正常沙箱 Chrome 验收，未停在断点。
- 官方脚本 `timeout 150 … run.py` 退出码 **0**。时间 2026-11-28 01:50:46–01:50:52（Asia/Shanghai）。Google Chrome 156.0.8078.47，`chromiumSandbox: true`，没有 `--no-sandbox`。服务与 Vite 只听 127.0.0.1:18794 / 18795，临时 SQLite，`seed_demo=False`。
- 预置合成已审核、未审核和撤回各一张；浏览器验证期间只读，`verificationWrites=[]`。壳层对默认演示案号 `CASE-2026-DEMO-LILY-MARY` 发过只读 GET（演示种子未启用，案件信息不可用），与本次知识卡检索无关，未当作写入。
- 唯一词 `SYN-W19-PAGE-7k4m2p` 的实际请求 `GET /api/v1/knowledge/cards?status=Published&limit=20&offset=0&q=SYN-W19-PAGE-7k4m2p` 返回 total=1、卡 `KC-cde642f0c49c4b5ba1d2f5b52c2754f9`，出处 type=Synthetic、title=合成夹具-published、locator=段落1、excerpt=`SYN-W19-PAGE-SRC-PUB`；页面同步显示该已审核卡与出处，未混入待审或撤回卡。
- 缺词 `ZXQ-ABSENT-W19-PAGE-8n3q` 的实际请求返回 total=0、items=[]；页面显示「没有符合条件的知识卡。库为空时不伪造样本或模型推荐。」，已人工批准发布 0 条，不残留上一张卡。
- 此项不等于 W19 整包，也不等于 W12 或 W7。未验 Firefox/WebKit、headed、真案、外部模型或生产身份。
