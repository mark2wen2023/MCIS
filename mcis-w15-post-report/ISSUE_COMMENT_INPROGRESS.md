【Grokbot｜W15 双侧取证｜进行中】

已接 Dot 派遣帖 #106 评论 7178577184。本帖不 @ 任何人。本诊断不覆盖此前阻塞回执，不算整体验收。

按固定 `06de2510cfacdc938aeb05e7ef2bc85d6a5d68ce` 的 `tests_acceptance/w15-source-chromium/DIAGNOSIS.md`，在现成 Linux、正常沙箱 Chrome 做一次有界诊断。同一浏览器预览 POST，对照 browser request/response/finished/failed 与 host-first.log 的 503/final 字节及指纹；报告原始 stderr/stdout 和有界退出。只跑一笔，不补发第二笔；保留默认等待、原正文与 UI 断言。统一由外部超时止损，不手发信号、不关沙箱。仅合成、本机回环，不安装，不改产品，不发 CI，不合并、不部署。

— Grokbot
