# 阶段演示工具独立验收

## 裁定

本次冻结范围通过：**11 passed / 26.89 秒**，包含全新目录的真实三服务流程、失败/中断清理和实际浏览器。13个冻结文件SHA执行前后一致。没有修改生产逻辑；三个页面的版本文字以本次冻结及实际DOM为准，不沿用旧截图。

## 独立检查

- 从全新输出目录执行真实HTTP流程。重新计算manifest中所有产物SHA/长度；源与恢复API文档完全相等，W10 GET/list/同body commit均明确ARCHIVE_HISTORY_ONLY，不能仅任意409当通过。知识目标库四张在线表均空，仅一条独立历史。
- 向父进程设置MCIS_DATA_DIR、MCIS_DB_URL、MCIS_CORE、MCIS_PORT=8765、种子和无效代理环境；仍只在自有新目录和三个不同随机loopback端口执行，指定禁止触碰目录内容原样，未生成数据库。没有接管已有8765服务。
- 已有目录、普通文件、指向有效文件的符号链接、悬空符号链接全部拒绝且原内容不变。
- PYTHONOPTIMIZE环境以及直接python -O运行器均拒绝，在创建输出/服务之前停止；浏览器优化模式和不属于当前运行器的manifest亦拒绝，未创建检查输出目录。
- 同exec内Popen启动--hold，等待真实验证passed后SIGINT+wait，检查三个自有PID/启动时刻已不在运行，manifest running=false，成功产物保留。
- 在三个服务均启动后注入独立测试异常，运行器失败返回1、manifest failed且running=false，所有自有子进程停止，日志和产物目录保留。不是把失败写成passed。
- 单个执行环境内新起runner --hold，再独立调用随包真实browser checker，不接管其它已有服务。它实际浏览源和恢复界面、独立知识历史，下载原始知识JSON与源文件逐字节一致。生成本轮截图。
- 独立browser_wrapper在实际lobby页面核对两处新版本文案，在report/interview截图前核对真实可见DOM：**无W10时1.2.0工作记录扩展；含W10时须1.3.0**。两个实例共6个页面检查、8处文案，另保存新lobby截图。不是仅源文件字符串测试。
- 浏览器后的数据库变化精确核对：source及knowledge-history全部行不变；case-restored原业务行不变，原audit/custody逐行前缀不变，两表各仅追加1条Stage Browser Readonly的custody.access（Custody SQL kind=Access），对应自增序号各+1。这是授权下载历史CSV的访问留痕，不是“完全无写入”。

## 发现与修正

代码审查发现大量assert在优化Python下被删除，可能跳过成功判据。开发方在运行器和浏览器入口加入not __debug__拒绝。修复早于原运行时红测执行，因此这里只声明“审查发现、修后真实拒绝验证”，不虚构修前失败日志。

独立测试初稿将浏览器浏览/下载误写成全DB不变；合法Access链追加触发该断言。已改为严格的仅一次Access及对应audit追加、其它全部不变，而非忽略数据库差异。随后修正测试对custody原行结构的假设：JSON行使用action，kind存于SQL列，二者均验证。上述是验收脚本错误，不列为产品数据异常。

## 使用边界

这是已备齐依赖的Linux本地演示，不是部署、认证、所有模块验收或项目完成。模拟审核由脚本执行，Confirmed/Published不是实际专家核验。报告为现有模板，无LLM、真实AIS、真实事故资料或Unity/W11验证。演示输入和还原由HTTP脚本完成，不宣称所有UI表单提交闭环已测试。

正常SIGINT退出清理已实测；强制终止执行环境、SIGKILL、主机崩溃仍可能留下stale running:true，manifest本身不授权连接。浏览器PID/启动时刻/命令行/socket核验拒绝不可确认状态，不放宽跨PID namespace。没有穷举所有资源耗尽和OS故障点；未将该防护称为对抗恶意操作系统的安全边界。

本次未新增产品阻断项。报告及测试不发布本地运行数据库、绝对内部路径、原始环境日志或私有协调产物。

## 复现

```sh
MCIS_BROWSER_BIN="$CHROMIUM_BIN" service/.venv/bin/pytest -q tests_acceptance/STAGEDEMO/test_runner.py
sha256sum -c tests_acceptance/STAGEDEMO/verified-impl-sha256.txt
```

需要现有service/.venv、web/node_modules、系统python的Playwright、Node及已安装Chromium。工具不会安装依赖。所有测试目录均为新的临时输出，运行器保留产物；测试自身没有删除用户既有目录。
