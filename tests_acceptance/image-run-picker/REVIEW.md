# 图片已保存运行选择 — 开发限定验证

基线 `f276dbf8ed6dcee817fda904954ed813baa3629d`；候选 `candidate/media-demo-lazy-factory`。仅图片页面及本项检查，音频未改。

源码依据：`image_review/app.py:list_runs` 在 authorize 后按 case_id、revision=0 查询，返回 runId/caseId/utc/sourceCheck（not-performed-by-list）。运行ID为 OCR- + uuid4.hex。`read` 另按case/run取详情、检查receipts及必要task binding；后端全部保持不变，未实际调用。

显式列表才请求；合法案号、同案运行、合法OCR ID、非空utc字符串、正确sourceCheck及无重复全部满足才生成按钮。任何坏项整批拒绝。utc仅原样文字展示，无时间真实性声明。用textContent展示；列表仍未核验来源。等待/空/失败分别提示，不把空列表当未知提交的未成功证明。

按钮通过现有 reset 草稿确认后调用同一 loadRun 详情实现：取消不改变当前选择、草稿或地址；确认后才切换目标、清除预览并读取。保持edit/selection代次、响应case/run校验及成功后的地址同步。列表阶段不改URL，未接纳详情不改URL、不丢草稿。切案/切运行清除列表，重新查询使旧按钮失效，迟到成功/错误不覆盖当前上下文。未改下载、身份、权限、工作台、API或工厂。

实跑：

```
python tests_acceptance/image-run-picker/check.py
python tests_acceptance/media-review-capability/check.py
node --test tests_acceptance/image-loaded-context/page.test.cjs
```

新12个命名场景分别对完整/限定HTML通过：显式列表与打开、无效案号零请求、畸形/混案/重复列表、等待/空/失败、旧按钮/迟到失效、取消与一次确认、详情错误/跨案/错运行/迟到/编辑保留草稿和地址。执行生产内联JS，DOM/Promise/History为手写替身，真实fetch/图像解码/原件读取禁止。能力检查及既有重开/地址检查通过，另5个图片归属/草稿场景通过，不能累计为全面验收。

旧头反例：将 `git show f276dbf8ed6dcee817fda904954ed813baa3629d:service/mcis_service/image_review/review.html` 存为 `/tmp/image-picker-baseline.html`：

```
IMAGE_PAGE_SOURCE=/tmp/image-picker-baseline.html node --test --test-name-pattern='explicit list creates' tests_acceptance/image-run-picker/page.test.cjs
```

实际预期失败：可选条目不存在（undefined而非2）。候选通过。没有浏览器、HTTP、服务、DB/ORM、权限/模型、原件或暂停测试，没有无关构建。隔离启动、同源与身份条件仍未闭合；未合并部署。
