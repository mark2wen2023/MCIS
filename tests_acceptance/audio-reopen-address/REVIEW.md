# 音频当前运行地址同步 — 开发检查

基线 `1231cae6b02afa6e353d57019e977bff3130dca5`，候选 `candidate/media-demo-lazy-factory`。本轮仅音频，图片页未改。

成功导入、详情读取及保存通过原有身份/提交快照/当前选择校验并被 UI 接纳后，且没有未保存草稿或页面累计未知保存，使用同源相对 query 的 `history.replaceState(null, '', search)` 更新当前地址。地址只有 case/run；不传身份、凭据、摘要或 revision，不 push、不跳转、不发额外请求。原无参数手工导入和读取仍可使用；成功后 location.search 变为合法的重开参数。刷新读取的是当前核对运行，不是固定报告历史版本。

History 不可用或抛错用独立状态区提示“刷新地址未更新”，不抛给保存 catch、不把已确认保存记作未知。未保存草稿、未知、错误响应、身份不符或迟到结果不改 URL。不清除未知记录、不自动重试；后续读取成功也不能证明先前未知请求结果。原件、binding、权限、保存响应验证均未修改。

实跑：

```
node --test tests_acceptance/audio-reopen-address/page.test.cjs
node --test tests_acceptance/audio-url-reopen/page.test.cjs
node --test tests_acceptance/audio-loaded-context/page.test.cjs
```

新增19个命名场景通过；相邻URL重开7项、归属/草稿4项分别通过。手写 DOM/History 与内存 Promise 执行实际内联 JS，真实 fetch 禁止。合成保存/导入响应并非真实后端写入、权限或故障测试。使用新 VM 和更新的 location.search 模拟重开，不是浏览器端到端验收。

旧头反例：`git show 1231cae6b02afa6e353d57019e977bff3130dca5:service/mcis_service/audio_review/review.html` 保存为 `/tmp/audio-address-baseline.html` 后：

```
AUDIO_PAGE_SOURCE=/tmp/audio-address-baseline.html node --test --test-name-pattern='manual new import' tests_acceptance/audio-reopen-address/page.test.cjs
```

预期失败，实际地址写入数组为空而非目标query；候选对应场景通过。没有运行无关React构建。没有浏览器、真实HTTP/服务/ORM/数据库/权限/模型/原件验收。History的真实浏览器限制、刷新效果及隔离装配仍待验；启动暂停不解除。未接工作台、未合并或部署。
