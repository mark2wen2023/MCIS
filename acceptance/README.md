# W9 正式环境页只读检索（同案观察、切案不串）

只验收现有正式产品壳 `#/env` 页面，不改产品、不另造页面、不重跑 `3d0e46e` 隔离页保存恢复。

固定产品 SHA：`94d5e38c926fda232bb987b60fa9145e4bcf01a7`。用已有 Linux、正常沙箱 Chrome、真实回环服务和临时 SQLite。工装在浏览前通过标准服务预置两件合成案件与观察；浏览阶段零写入。桌面与 390 各只跑同一条读链，报告需分段记录。

```sh
timeout --signal=TERM --kill-after=10s 150s env \
  MCIS_HOST_PYTHON=/existing/service/.venv/bin/python \
  MCIS_CHROMIUM=/existing/google-chrome \
  MCIS_NODE_MODULES=/existing/web/node_modules \
  MCIS_BROWSER_EVIDENCE_DIR=/new/w9-env-page-read-evidence \
  /existing/playwright-venv/bin/python tests_acceptance/w9-env-page-read/run.py
```

此项不等于 W9 整包。不安装依赖、不关沙箱、不用真案或外部模型。
