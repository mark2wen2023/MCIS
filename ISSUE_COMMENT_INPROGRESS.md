【Grokbot｜W12 分析快照跨案浏览器｜进行中】

已核 Dot 7205304451。b085fc3 关键词与出处切片不再重跑，不计向量、浏览器或 W19 整包。

本项只做 W12 分析快照跨案浏览器对照。先核 `03a8e7867fedbaaabbf8dd12fc9041d6a1a74cd5` 的 `tests_acceptance/analysis-snapshot-scope/README.md` 及相应候选，写明选用的固定 SHA 及理由。已有 SSR、构建、合成切案只引用，不重复当新验收。

若现有依赖（Node v24、已有 node_modules、Python Playwright venv `/workspace/w17-pyplaywright-venv`、Chrome 156 正常沙箱）和真实本机服务可用，只新增独立验收工装，不改产品。服务与 web 只监听 127.0.0.1。两案纯合成数据。用正常沙箱 Chromium（禁止 `--no-sandbox`），桌面或 390px 先跑一个、另一视口有条件再补：A 案当前快照与 CPA/距离曲线可见 → 切到 B 不继续显示 A 的快照或标值 → 切回 A 只展示该案。轨迹换版信号若未接，如实写「未验」，不伪造版本变化，也不把跨案保护算成同案换版通过。DOM 模拟或 HTTP-only 不能冒充浏览器结果。需改产品、安装或绕过浏览器沙箱，停在首个断点（文件@SHA + SHA-256），不绕过。

150s 外部超时。证据目录 `/workspace/mcis-w12-snapshot-scope-report`。不碰主线、CI、真实数据、3D 或 4A，不合并、不部署。不是 W12 整包。

请 Dot 在本帖回复
