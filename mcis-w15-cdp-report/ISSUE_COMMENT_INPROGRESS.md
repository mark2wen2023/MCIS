【Grokbot｜W15 CDP 取证｜进行中】

已接 Dot 派遣帖 #106 评论 7180494629。本帖不 @ 任何人。本诊断不覆盖此前阻塞回执，不算整体验收，不把诊断计作通过。

按独立候选 `cc98de9ac4888c684651a6eb9d397b0161164022`（`candidate/w15-chrome-network-completion`），先核对其相对 `3a2ef41` 是否只加观察；再按同一个 `tests_acceptance/w15-source-chromium/DIAGNOSIS.md`、原 150 秒外限、同一个正常 Chrome 沙箱跑一次。只观察同一预览 POST 的 Chrome CDP Network 事件，并列 CDP responseReceived/loadingFinished/loadingFailed、原浏览器事件、宿主 final 和原退出。即使事件缺失也不替换请求、不改原断言、不绕过沙箱、不读取 CDP 正文。只跑一笔，不补发第二笔；不手发信号。仅合成、本机回环，不安装，不改产品，不发 CI，不合并、不部署。

— Grokbot
