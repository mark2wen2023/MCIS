# 音频重读等待期间输入保留（开发侧，2026-11-18）
父1e7c33bd50e95bc178c9aaad2abbcc270600ab0b。新合成测试修前1失败：读取等待中修改文字，旧响应render重建行，将新草稿替换为synthetic。
最小修复：编辑事件递增版本；读取请求记录版本，收到响应时若编辑或案件/运行选择已变化，不render、不自动重读，保留输入并说明。未改权限/服务/归档、未宣称人工已读。不覆盖其他导入/任务打开路径的完整验收。

静态审阅新文件后执行：
```bash
node --test --test-name-pattern='^(edit during pending reread|unchanged reread)' tests_acceptance/audio-read-race/page.test.cjs
```
最终2通过0失败0跳过，验证迟到读取不清草稿及正常无变化重读仍工作。DOM和HTTP响应为合成替身，无浏览器/网络服务/真实音频/模型；不是独立验收。未运行暂停、写入拒绝或安全探测。下一项另行核查保存时切换上下文，不混入本修复。
