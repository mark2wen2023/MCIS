# 音频保存迟到响应上下文保护（开发侧，2026-11-18）
父acbfbd6c4b2aedd3b8d8089cfbecbc1e92b464be。修前新合成用例1失败：保存期间切案，成功响应仍将state.revision从0改1。
仅在音频保存请求捕获案件、运行及选择代次；收到响应后选择变化（含离开再回到原值）则不更新state/history、不清输入、不自动重试。明确原请求可能已保存，需核查结果。正常同上下文的既有完整成功响应校验保持。不取消服务端请求或假称事务未提交，不改权限。

新文件和相关普通节点静态审阅后执行：
```bash
node --test --test-name-pattern='^(late save after|selection away and back|unchanged selection)' tests_acceptance/audio-save-context/page.test.cjs
node --test --test-name-pattern='^(edit during pending reread|unchanged reread)' tests_acceptance/audio-read-race/page.test.cjs
node --test --test-name-pattern='^(successful last draft save|saving one segment|edit during successful pending save)' tests_acceptance/audio-saved-draft-state/page.test.cjs
```
分别4、2、3通过，各无失败/跳过；后两组为同音频页相邻回归，不与历史运行数相加。4新节点覆盖切案、切运行、切走再切回、正常成功。保留原反例。

全部是实际页面脚本配合合成DOM/HTTP响应替身，没有真实浏览器/服务/原件/模型，不是独立验收或权限测试。未运行暂停节点、写入拒绝探测或安全测试。未验证整页所有其他异步操作（例如导入/任务打开）或图片页类似竞态；不宣称全局竞态解决。草稿仍仅内存，正式归档恢复仍关闭，不合并部署。
