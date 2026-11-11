# 当前生产核心与再生成 seed 的浏览器复测

2026-11-12（UTC+8），以当前源码及重新生成的 seed 实际运行已归档 `tools/provenance/browser_smoke.py`。

- **35/35 检查通过**；JavaScript/console 错误、警告及 HTTP 错误均为空。
- 报告 YANGZE/海力、有限节选定位、跨案证据校验与建议创建、报告跳转、W12/W5/W6 页面交互均通过。
- 使用当前真实核心 DLL SHA256：`f94197777acc45d7ff4e84f265ded9d43c32e773c17cac462d952574d77ac9cf`。
- seed SHA256：`988e9abd3b39959864f42912d8d3454dacd7821156fd8b21268631f30f4693e3`。
- 逐项结果与临时写入路径见 `logs/current-core-browser-result.json`。

服务仅监听本地回环，写入仅临时数据库；未重跑 W6 原 19 项套件。截图仅本地，未复制入本轮仓库归档、未上传或重试上传。未修改实现。仅云端 Linux 桌面 headless 验证，不代表移动端、用户电脑或全项目验收。
