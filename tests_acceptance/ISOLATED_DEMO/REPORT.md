# 隔离终端演示：独立验收

独立审查者未修改产品，新增 `test_isolated_demo_independent.py` 12项。
独立12/12通过，零跳7.31秒；与主5项最终合跑17/17通过，零跳11.33秒。
一项既有Starlette/httpx弃用警告。未发现本切片剩余阻断项。

命令：
```sh
MCIS_PREFLIGHT_REAL_CORE=/tmp/mcis-preflight-core.sh \
PYTHONPATH=isolated-demo/service mcis-work/service/.venv/bin/pytest -q \
isolated-demo/service/tests/test_isolated_demo.py \
isolated-demo/service/tests/test_isolated_demo_independent.py --disable-warnings
```

## 实际执行

检查了既有核心包装器，调用已存在的.NET runtime和mcis-core.dll。本套真实核心用例没有替换core_run或返回模拟结果。

- 独立真实子进程选择第2份虚构来源，来源ID EV-002、sourcesImported=1、无冲突候选；不是误选第1份。
- 实际stdin交互q退出，缺失核心仍可退出、无保存；错误输入与EOF退出码2，无成功提示或traceback。
- JSON模式缺少明确choice时拒绝，不进入交互或启动演示。
- 禁止Python socket.bind/socket.connect及legacy create_app时，真实W2双源演示仍通过并返回5°差异。
- 捕获可信host实际新建token，确认返回摘要不包含token，摘要仅有预定字段。
- 准备失败、KeyboardInterrupt均检查临时目录确已移除；注入清理异常时CLI退出码2，不返回temporaryDataCleaned或成功清理声明，内部错误细节不泄露。
- 环境指向既有MCIS_DB_URL/MCIS_DATA_DIR时，既有文件逐字不变，显式临时设置不受旧环境数据库/种子/核心/端口设置影响。
- 主测试另跑真实子进程双源5°和交互单源流程，代码路径均包含保护目录→选择→保存→读取。

## 静态核查与边界

演示直接调用现有create_case/commit_input服务函数进行可信host虚构fixture准备，没有创建或挂载旧FastAPI app，也没有使用旧角色HTTP头对外认证。session由可信host在临时同库生成，仅交给固定ASGI客户端。临时数据库不是用户既有数据库。DB引擎在退出前dispose，正常退出、普通异常和捕获的KeyboardInterrupt后清理目录；不承诺SIGKILL、断电或宿主崩溃后清理。

这里是终端菜单和内存ASGI的真实运行路径，不是浏览器UI、网络服务、IdP或生产登录。可信core_command由host提供；没有安装或下载核心。Python socket禁止测试不是对核心子进程的OS级网络审计，不能扩写成整个运行时已通过网络隔离认证。用户会话管理、真实案件上传、浏览器身份交付仍未完成。

数据都是内置虚构45°/50°CSV，不是实际事故数据或LLM解析结果；5°冲突候选包含未校准来源提示，不等于证据互证或人工事实批准。摘要明确unreviewed/not_assessed/not_verified/not_attested。临时保存结果退出后被清理，不是可长期交付的案件档案。

未推送、未合并、未部署。

## 产品冻结

`service/mcis_service/identity/demo.py`
SHA-256 `214ed14d075f59e90d22a53b9f548a6bd6bbae0b320573f19f9db6beba3c1fa5`。
