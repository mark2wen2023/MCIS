# 图片当前核对记录显式重开：开发验证

基线 `0735c99c00c0565974ea8b8714ba94387faccbf8`，候选 `candidate/media-demo-lazy-factory`。

独立图片页现可用 `/image-review-lab?case=<编码案件ID>&run=<OCR-32位小写十六进制>` 重开当前记录。不是报告固定历史版本；不自动下载/预览原件、不保存、不发起模型任务。无参数保持手工流程；有查询参数时要求唯一合法 case/run，不接受额外参数（包括 revision），缺失/空白/重复/非法时清空输入且不读取，随后可人工明确填写。不改变现有权限或提供身份。

静态依据（未调用）：`image_review/app.py` 的 `read` → `authorize` → `records(case_id,run_id)` → `receipts` → 可选 `verify_task_binding` → `result`，返回外层 caseId/runId。`records` 同时按案件和运行过滤；运行由 `OCR-` + uuid4.hex 生成。案件格式复用 `evidence_intake/parser.py` 的 SAFE_ID；权限依旧由 `evidence_intake/router.py:authorize` 检查。前端先判请求仍属当前选择，再校验返回身份；旧成功/旧普通错误不更新新目标状态。原有输入代次、dirty、替换确认、原件按钮和保存逻辑未改。

仅执行以下离线检查：

```
node --test tests_acceptance/image-url-reopen/page.test.cjs
node --test tests_acceptance/image-loaded-context/page.test.cjs
```

新增 9 个命名场景通过（无效参数组含多种输入）；相邻 5 个既有归属/草稿场景通过。新增测试执行实际内联脚本，以手写 DOM 和受控内存 Promise 替换 json；真实 fetch、图像解码、原件加载均立即报错，未调用保存。检查读取中真实合成 oninput、取消替换、切案/切运行后迟到成功及普通错误、切走再返回。读取中修改的草稿从当前 DOM 重新定位检查。

旧头反例：从上述基线用 `git show <SHA>:service/mcis_service/image_review/review.html` 保存为临时源码文件，然后运行：

```
IMAGE_PAGE_SOURCE=/tmp/image-url-reopen-baseline.html node --test --test-name-pattern='explicit encoded' tests_acceptance/image-url-reopen/page.test.cjs
```

实际失败为读取数 `0 !== 1`；候选对应场景通过。反例失败是预期，不是候选失败。源码差异仅页面说明、detail load 和 URL 初始化，外部 preview.js 引用不变。

这是开发方限定合成验证，待独验。未运行真实浏览器、HTTP、应用、DB/ORM、权限、模型、图片或历史恢复测试。没有实际来源真实性/授权保证；启动与归档暂停未解除。不为独立 HTML 重跑无关 React 构建；没有接入工作台链接，也未改变音频页。无合并或部署。
