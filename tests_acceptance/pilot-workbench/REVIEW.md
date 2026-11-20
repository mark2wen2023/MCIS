# 合成试用选案 → 取证（尚未挂载）

基线：2a5640137838d047605a9642b28e3872b7d8186f。
页面：service/mcis_service/local_review_pilot/workbench.html。

复用固定工作台 16eab999 的七阶段、明确案号、可返回选案、完成状态未评估原则；
没有搬入 Layout/EvidencePage，没有增加路由、权限、存储或业务请求。
独立 HTML 使用原生 DOM 和内联 JS，无构建依赖。不能按本记录启动服务。

实际接线合同来自当前 common/pilot_case_discovery.py：
GET /api/v1/pilot/cases → [{caseId, title}]；只显示服务器返回的 SYN- 合成案号，
格式与 local_review_pilot.PilotSessions 的授权案号规则一致。用户明确选择后，
GET /api/v1/cases/{case_id} → 案件对象；只使用经 caseId 核对的 title。
该详情形状来自 cases/basic_registration.py 的 get_case → cases.service.load_case。
不注册其未过滤 list_cases；未来工厂必须只挂允许的详情端点并安装同一 verified context。

所有请求仅 GET、相对同源路径、credentials:same-origin、cache:no-store、redirect:error，
不提供角色头、身份输入、URL 案号回退、凭据存储、自动登录或模拟案填充。
初始零请求；主动读取清单、显式选择才读取详情。服务端仍必须逐次确认会话与授权。
客户端校验不是授权。401/403 只显示会话或授权未确认，不猜测具体认证原因。
普通失败不显示零案；只有成功空清单才显示无可读授权案。
切案立即清除旧详情；请求代次抑制迟到成功/失败。刷新、隐藏、pagehide 清除案件缓存。
未观察到的服务端身份变化无法由静态页面实时感知；下一次读取仍由服务端判定。

图音接入区域只有明确说明，没有未接通按钮、保存成功或外链。
未运行证据、时间线、航迹、CPA、冲突、保管链、媒体/原件/报告请求。
后续必须完成媒体初始化、最终路由白名单、同源安全会话发放与隔离运行批准，
才可挂载；尚未证明两合成案首次导入→修订→刷新重开。

## 实跑

`node tests_acceptance/pilot-workbench/check.cjs`

9 组通过，退出 0：初始零请求与显式两步读取；A/B 乱序成功和失败；
切案等待/失败清旧；身份不符；空/畸形/重复/失败清单；会话失效清理；
刷新与重复读取乱序；隐藏/离开清理；文本输出与无假导航。
测试执行生产内联 JS，仅手写 DOM/受控内存 Promise；fetch 完全替身，禁止真实网络。
DOM 替身不证明真实浏览器事件、键盘焦点、可访问性、移动端布局或视觉。
未运行 TS/Vite（这是独立 HTML，没有该构建链），未运行浏览器、HTTP、后端、
DB/ORM、权限实测、模型或暂停测试。未读取业务材料、seed、凭据。
