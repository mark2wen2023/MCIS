# W12 同案换版接线核查

静态核查固定针 03a8e786 / 底版 94d5e38。无现成同案换版 API；分析仍为离线 seedSha256。首个断点：`service/mcis_service/analysis/router.py` @ 03a8e786，SHA-256 `b3e91f7606b20da2c4ec1f07de396df0d041603dfbea694431a963f6e41bb4be`。实施说明与验收条件：`tests_acceptance/w12-track-version-wiring/`。本轮未跑 HTTP 或浏览器。不是 W12 整包。
