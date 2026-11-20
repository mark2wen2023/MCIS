# 最小合成试用工厂：选案 / 详情 / 工作台

基线 023bd3d873e8d85665bae3deda739058d24a09c2。
入口 `service/mcis_service/local_review_pilot/factory.py:create_local_review_pilot`。
**源码已装配，未实例化真实 FastAPI，未运行服务。不是启动许可。**

显式 enabled=True、真实 PilotSessions 实例、新临时 Database 和精确 HTTPS
127.0.0.1 origin 缺一即拒绝。配置验证先于 FastAPI 构造和 DDL。
不读取环境配置，不提供登录、口令、Cookie 发放、命令行或自动启动。
固定 HTML 不含身份/案件数据，可公开读取；它的数据请求必须各自经同源 Cookie
和服务器会话验证，不能由公开页面本身取得授权。

最终路由白名单严格只有：
- GET /pilot：固定工作台 HTML，无缓存、禁止被 frame 嵌入。
- GET /api/v1/pilot/cases：复用真实授权发现注册，从许可集合逐案查，不全案扫描。
- GET /api/v1/cases/{case_id}：直接 Depends 已验证上下文，复用 cases.service.load_case
  的真实逐案读取，no_autoflush，核对响应案号及标题，无默认案/角色头回退。

关闭 docs/redoc/openapi 和自动斜杠重定向；路由集合核对后才调用专用六表初始化。
既有默认 app、Database.create_all、main、registry、launcher 均未接触。
未插入案件/策略/回执；下一轮受信合成夹具供应尚需获准，不能拿旧库填充。
Database.session 的原提交行为不改变，不能把此路径叫绝对零副作用。
此处沿用已有 Cookie 的 HTTPS / Host / Sec-Fetch-Site 条件，不降低为明文 HTTP，
不信任代理转发头。可信引导发放 __Host-MCIS-Pilot 的机制仍需单独验证。

## 为何本次不挂图音

image_review/app.py:106,126 与 audio_review/app.py:78 仍动态导入 tasks.verify_task_binding。
实际依赖 Task 模型及转换器，且媒体 Storage 独立于六表 Base；不能只不挂任务 router
就宣称依赖已闭合，也不能用缺任务表 SQL 错误代替明确的原任务来源拒绝。
本工厂没有媒体、登记、原音、报告、归档写入或任务路由，没有删除其历史/容器/
审计/回执/修订/绑定判断。工作台继续仅有关闭的图音说明，无工作台到媒体链接。
后续先闭合真实任务来源只读核验或明确拒绝边界，再初始化媒体表与只追加触发器，
才可扩最终路由白名单。不存在可用的首次导入/保存/刷新闭环。

## 本轮实跑（仅离线）

```
python -I tests_acceptance/pilot-factory/check.py
python -I tests_acceptance/pilot-core-storage/check.py
node tests_acceptance/pilot-workbench/check.cjs
```

分别5组工厂AST/手写依赖、9组存储AST/假metadata引擎、9组生产内联JS/假DOM通过。
工厂测试抽取真实函数去掉 imports，注入假 FastAPI/Depends/HTMLResponse/Path/DB，
保留真实会话、授权依赖与案件发现函数逻辑；没有触发 Python 应用/SQLAlchemy 导入。
手写 dispatch 显式先执行 dependency 再 handler，不是 FastAPI 依赖解析的运行证明。
未测真实路由创建、Pydantic 注解、SQLite、HTTP、TLS、Cookie、身份、浏览器或权限。
不累计成端到端或完整系统覆盖。

## 下一轮隔离实跑前置（本轮未执行）

1. 明确批准的私有本机或临时容器；不挂业务仓库资料、用户目录、原案、seed、凭据或模型。
   冻结仅所需源码和可信依赖，核实无 editable/.pth/启动钩子；不能把 venv 当沙箱。
2. 独立全新、独占临时库与临时文件根；禁止旧库/迁移/恢复。六表 DDL、trigger catalog
   格式及初始化失败停止先验收；任何失败丢弃临时目录，禁止自动重试。
3. 禁止外网业务访问；仅 127.0.0.1 HTTPS，可信证书和明确 origin。可信引导端提供短期
   服务端会话和合成 A/B 最小许可；秘密不进页面/URL/日志，不使用4A或真实凭据。
4. 先仅验三路由、关闭的 docs/任务/媒体边界和两个合成案读取；身份/权限实测需单独批准，
   当前仍暂停。确认 Cookie 实际发送与失效处理，不改浏览器安全设置。
5. 首次图音导入→保存冲突→刷新重开必须等媒体依赖和白名单闭合后另验，不能在本工厂上
   宣称完成。异常、身份不明、路径/挂载/依赖偏离即停止，不放宽保护。
6. 退出停止监听与子进程、撤销临时会话，按批准流程清理临时库/目录；保留仅非敏感验证记录。
