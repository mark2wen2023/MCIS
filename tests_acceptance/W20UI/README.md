# W20.2 独立UI验收

浏览器30项断言独立编写；`fixture_server.py`与启停脚本基于实现方提供的本地测试夹具整理，使用真实 FastAPI/SQLite/W20 路由和明确命名的 HTTP 假模型。仅合成笔录、仅127.0.0.1，不是真实LLM评测。

## 运行

先安装服务依赖至 `service/.venv`，安装前端依赖，并准备Playwright及其Chromium。仓库根目录执行（需允许本机socket/Chromium）：

```sh
bash tests_acceptance/W20UI/run.sh > logs/w20ui-independent-browser.log 2>&1
service/.venv/bin/pytest -q -p no:cacheprovider service/tests/test_contracts.py
sha256sum -c logs/w20ui-impl-hashes-frozen.txt
```

环境参数：
- `MCIS_PLAYWRIGHT_MODULE`：可选，Playwright模块名或已安装模块路径；默认 `playwright`，按Node模块解析规则查找。
- `MCIS_BROWSER_BIN`：可选，已安装Chromium可执行文件；默认使用Playwright管理的浏览器。
- `MCIS_PYTHON`：可选，服务Python解释器；默认仓库 `service/.venv/bin/python`。
- `MCIS_W20UI_ARTIFACT_DIR`：可选，截图输出目录；默认本轮临时目录中的 `artifacts`。截图只保留本地，不提交PNG。

根目录由脚本位置解析，无需固定工作区路径。每轮生成独立系统临时目录，存放控制文件、临时数据库、服务日志及默认截图；所有监听端口动态分配，退出trap关闭本轮服务。不部署、不外发、不写生产数据；故障调查后可自行删除本轮临时目录。

## 范围与证据

- 真实后端 + 本机HTTP假模型：生成、确认、驳回、SOURCE_CHANGED、ALREADY_REVIEWED、真实403、模型HTTP失败、W5刷新、迟到请求与防双击。
- Playwright响应故障注入：未配置/非法配置的登记响应、已提交但丢失响应、跨案队列、不匹配成功响应、长文本HTML、多条候选逐条勾选。注入不等于真实模型/实际配置部署验收。
- AgentService身份通过开发模块初始化，用户角色选择器本来不列服务账号；后端权限检查仍通过真实HTTP。

文本证据：`logs/w20ui-independent-browser.log`、`logs/w20ui-independent-contracts.log`及前后冻结哈希。桌面/移动截图仅本地已查看，未提交；desktop展示故障注入双候选，mobile展示极长转义文本。

未覆盖真实LLM质量/时延、实际屏幕阅读器与触摸设备、浏览器矩阵、生产身份认证、整页重载或多标签的全局幂等保证。CUA连接失败后使用获准的工程Playwright fallback。
