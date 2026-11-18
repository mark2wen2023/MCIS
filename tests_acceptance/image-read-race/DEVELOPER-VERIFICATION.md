# 图片迟到重读保护（开发侧，2026-11-18）
父bd040c9f4ac0732991e80ef897207f2679e4d82d。新普通合成首节点修前1失败：等待读取时输入new draft，返回render把行重建为synthetic。
仅图片页记录编辑代次、案件/运行选择代次。读取响应到达后，编辑或选择已变化则不render、不自动重读，保留输入；包含切走再切回。正常无变化读取保持。没有权限/接口/归档改动。

静态审阅合成DOM/HTTP测试后仅执行：
```bash
node --test --test-name-pattern='^(edit during pending image reread|image reread ignores|unchanged image reread)' tests_acceptance/image-read-race/page.test.cjs
```
最终5通过0失败0跳过：新输入、切案、切运行、切回及正常重读。不是浏览器、网络后端、真实图片解码或OCR验收。未运行暂停节点/写入拒绝/安全探测、真实资料或模型。没有修改浏览器安全设置。保存竞态另项处理；导入/任务等其他异步入口未全面验。草稿仍仅内存，正式归档恢复关闭。未独验、未合并部署。
