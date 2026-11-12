# W19.1 独立浏览器验收

执行：`W191_PLAYWRIGHT=<环境提供的playwright模块路径> W191_CHROMIUM=<环境提供的Chromium可执行文件> bash tests_acceptance/W191/browser-run.sh`。工程 Playwright fallback 已获主任务许可。服务/Vite/浏览器在一个命令会话启动清理，服务仅绑定127.0.0.1，临时SQLite与截图均位于mktemp目录，不入库。冻结实现未改。

结果：B01–B06 通过；B07、B08失败，测试进程退出1。

- B01：三类Case/Challenge/Method人工创建；Investigator没有审批控件，Public看不到候选/内部审计；Lead必须给理由并完成三项复选才能发布。
- B02：HTML/script/img字符串仅文本，无执行节点；外部不显示内部审批理由；字面检索键盘Enter提交；390×844无横向溢出，截图人工检查可读。
- B03：首席撤回，Public列表数量3→2且标题消失。
- B04：真实服务完成POST后延迟响应，双击同步按钮仅发送1个POST；写入期间禁用按钮；切到Public后迟到响应不展示候选/内部控件。
- B05：真实服务完成POST后浏览器中止响应，显示未知结果且禁写，不重发；切Candidate看见已提交卡，读取独立审计，勾选明确核查声明后解锁。
- B06：上述过程无未捕获pageerror。
- B07（失败）：填合成示例，标签设`duplicate,duplicate`，保存得到真实HTTP422；等500ms后`role=alert`不存在。界面既没有持久失败说明，也没保留明确失败结果。自动列表刷新清空写入错误。
- B08（失败）：真实服务完成POST后暂扣响应，在同一浏览器任务内把hash从knowledge改到cases，再改回knowledge，两次分发hashchange，然后释放旧响应；返回的workspace显示旧写入成功notice并切到Candidate。应废弃旧导航上下文结果。

限制：B08为工程化同任务导航事件压力测试，并非声称鼠标手速可以稳定触发。网络延迟/丢响应通过Playwright路由注入，业务请求仍交真实后端提交；未宣称真实生产认证、实际跨设备撤回副本、屏幕阅读器或完整移动设备认证。截图只在临时目录，未提交。直接HTTP详情/分页/其余角色矩阵由另一独立验收覆盖。
