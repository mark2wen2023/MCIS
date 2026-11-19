# 音频已保存运行选择 — 开发限定验证

基线 `dc336265fd67464f6826444a4d96d3cb8be9042a`；候选 `candidate/media-demo-lazy-factory`。本轮只完成音频，图片仍为原文本列表，未新增工作台链接或工厂。

静态合同依据：`audio_review/app.py:listing` 经 authorize 后按 case_id 和 revision=0 查询，返回 caseId/runId/utc/sourceCheck；sourceCheck 固定 not-performed-by-list。运行由 AR- + uuid4.hex 生成。详情 get 另执行 authorize、rows(case_id,run_id)、check 后返回。没有实际调用后端。

用户显式点击列表后才读取。案号须符合现有 SAFE_ID；响应必须是同案、合法运行ID、非空字符串utc、正确sourceCheck，重复运行或任何坏项整批拒绝。UTC仅原样显示，不增加时间真实性或格式认证。渲染只用textContent。等待、空与失败分别提示，列表不是来源核验或未知提交结论。列表阶段不加载详情、不写地址。

条目“打开”先沿现有 canReplace 确认，取消不改变目标/草稿；确认后使用同一 loadRun 详情实现，仍检查响应身份、输入/选择代次。加载详情成功才沿既有地址同步；错误或未知不改变URL。选择变化及重新列表会清除选项并使旧回调失效；旧列表成功或错误均不回填。原有无参手动读取、任务成功后读取、原件与保存逻辑保留。

实跑：

```
python tests_acceptance/audio-run-picker/check.py
python tests_acceptance/media-review-capability/check.py
node --test tests_acceptance/audio-loaded-context/page.test.cjs
```

新12个命名场景分别对完整和限定HTML通过，是真实内联JS+手写DOM/Promise/History，不是浏览器或HTTP。包含显式列表/详情打开、无效案号零请求、混案/重复/畸形整体拒绝、等待/空/失败、切案迟到、旧按钮失效、取消及一次确认、未接纳详情保留当前DOM草稿/地址。真实fetch禁止，未测试权限拒绝或模型。

能力检查及其既有重开/地址回归通过；另4个相邻音频归属/草稿场景通过。不把不同模式或历史轮次计作全量覆盖。旧头反例：将固定基线音频review.html用git show存为 `/tmp/audio-picker-baseline.html`，执行：

```
AUDIO_PAGE_SOURCE=/tmp/audio-picker-baseline.html node --test --test-name-pattern='explicit list creates' tests_acceptance/audio-run-picker/page.test.cjs
```

实际预期失败：无可选条目，undefined而非2。新头通过。无服务/HTTP/浏览器/DB/ORM/权限/原件/模型实测，无关构建未重复；隔离启动、同源与身份仍未闭合，未合并部署。
