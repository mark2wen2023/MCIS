# 合成图片试用素材与编排源码——当前禁止实跑

基线 `5ab815fd4e4386bbd716d7f092a5ccb903368827`。没有启动器、环境隔离实现、会话
发放器或已批准浏览器驱动；**不是一条现在可运行的端到端命令**。本轮只运行纯字节/AST检查。
没有改产品工厂、路由、默认配置或权限。

## 已写的实际代码

- `fixtures.py`：标准库内存生成两份明确虚构案件；小型一页矩形PDF、8×8蓝色PNG、
  手写原始JSON、满足现有图片候选解析器的JSON。无I/O、时钟、随机、模型或既有资料。
  候选三项来源SHA来自生成字节；文字是手造声明，不是矩形中识别出的文字。没有语音或OCR验收。
- `prepare.py::bind_existing_case_creator`：显式受信建案授权提供器缺失则在导入前拒绝；
  有提供器时用现有 `_register_basic_cases` 收集原 create_case 函数，私有router永不挂载。
  原schema、角色、重复检查、put_doc与audit不改。这里没有自行构造Ctx或新建数据库行。
  本次新增内部提供器见下节；仍须由可信宿主确认配置来源。case.read、任意Ctx或普通会话
  不能视为创建许可。现有试用权限映射没有case.create，不能拿该映射冒充已提供这个能力。
- `prepare_registered_case_a(host=...)`：在宿主批准的资源作用域中创建两案、真实单案重读、
  核对两案零运行；对A的四材料依序真实preview/commit、比对SHA/元数据/案号/证据ID、
  按服务器requestDigest重读回执；再次核对两案零运行，然后才进入页面验收 continuation。
  不自行计算可信requestDigest、不直接插库、不先建图片运行、不自动重试或吞未知提交。
- `browser_steps.py`：未执行的页面序列，使用宿主已认证页面；选A→同案图片入口→填四回执→
  首次导入→改一行并保存→reload核对同一run和文字→工作台A/B切换核对案号与链接。
  选择的是正常授权切案控制，不执行尚未获准的权限拒绝探针；不是迟到网络故障注入。
  没有browser.launch、Cookie注入、角色头或新登录。没有把回听/原图显示混入文字验收。

## 阻断及宿主必须实现的精确接口

不提供一个仅凭布尔参数就声称安全的预检。当前环境没有被证明满足下列条件，CLI立即
以非零退出且不启动任何资源。不得执行prepare.py或browser_steps.py来试探边界。
下一轮只有获得明确许可、受审的可信宿主后才可绑定：

1. `approved_scope()` 异步上下文：核实获准的私有临时容器/主机；不挂业务checkout、原案、
   用户目录、seed、密钥或模型；无外网业务访问。冻结源码/依赖/schema，确认非editable。
   全新独占临时库/素材根，禁止旧库和迁移。拒绝不能证明的环境，而非把venv当隔离。
2. 作用域内构造现有专用工厂，enabled/image_imports/evidence_registration显式开启；
   仅127.0.0.1 HTTPS，明确origin与可信证书。不改浏览器安全设置，不信任转发头。
   可信短期临时会话在服务器确认授权，秘密不写URL、页面或日志，无硬编码口令。
3. `context_for_creation(case_id,'case.create')`：新建合成案的独立服务端授权边界，返回
   真实Ctx给原create_case；该能力是当前首个缺失项，不可以默认Investigator补齐。
   `create_case(body)` 应绑定上述原处理器适配器；不是任意插行回调。
4. `request(method,path,body)`：只访问同一已核实origin/工厂；不接受外部URL、不转发角色头、
   不重试，返回真实(status,JSON)。仅需case.read/image.list/evidence.preview/
   evidence.register/evidence.receipt.read；不能把某一许可推导成其它许可。
5. `review_in_same_origin_page(prepared)`：在同一资源作用域内使用browser_steps提供的序列；
   会话须具备明确两案读取与A图片导入/修订权限。实际浏览器及身份验收需要另行批准。
6. 作用域退出（包括建案、登记、页面或超时异常）必须停止自己的监听/进程、撤销临时会话、
   清理自己拥有的目录；不能删除外部路径。编排不实现或声称已验证这项宿主职责。

案A“4份合法回执且0运行”只在真实服务确认每一项后成立；当前未准备任何案件/回执。
缺配置、异常响应、身份不符或非空列表即停止；提交未知不得自动重试。
脚本不证明生产身份、多用户一致性、来源真实性、恢复或报告持久绑定。

## 本轮唯一允许且已实跑的命令

```
python -I tests_acceptance/pilot-image-fixture/check.py
```

5组通过，退出0：手造字节走固定原纯解析器的AST版本；PNG CRC/像素与PDF xref偏移；
案件schema字段形状；未执行编排的调用顺序/零运行检查/无直接数据库调用；未执行浏览器
序列的源码检查。完整case JSON Schema执行、PDF/PNG真实解码/渲染未验。
首次AST断言误把说明中的“sessions”当数据库调用，已改为检查AST属性调用后复跑通过。
未导入FastAPI/SQLAlchemy/应用，未执行建案、准备、ORM、HTTP、浏览器、权限或模型测试。
检查读取的Git对象仅是明确的契约schema和纯解析源码；没有读取真实案例/seed或凭据。


## 本轮内部建案适配（待批准源码，未运行）

基线 `afd1e49b7d8a0f7933c452445d54ab7b3f6293c1`。
`authority.py` 的 `CreationConfig` 必须来自宿主核验的服务器配置：显式主体、创建角色、
最长十分钟的进程单调时钟截止点，以及两份 `cases()` 精确正文摘要绑定的
`(caseId, case.create, bodySHA256)` 授权集合。它验证配置形状与范围，不认证配置签发者。
不接受浏览器参数、角色头或普通 case.read 权限作为创建授权，无默认身份、密码或凭据。
一份 authority 仅领取一次、仅绑定一个适配器；每案仅发送一次。处理器异常关闭整个创建作用域，
不能据此推断未提交或自动重试。此约束仅在该进程对象内成立，重启/重新构造配置不具持久防重保证。

`host_adapter.py::owned_creation_scope` 提供实际可供未来宿主调用的上下文管理器源码：
先要求外部 `approved_host.isolated_workspace()`，再领取授权；宿主检查成功后，在其专属目录
新建自有临时子目录/新 SQLite 路径，用现有专用 factory 初始化真实表及保护；核对确切七表
且全部零行后才给出 `(creation_adapter, app, root)`。适配器构造服务器 `Ctx/Request`，
调用原 `bind_existing_case_creator`，不调用 get_ctx 或注入浏览器头，不挂公开 POST /cases。
成功/异常退出都关闭适配器、dispose 引擎、清理自己新建的临时子目录。真实数据库、SQLAlchemy
和清理行为本轮均未运行；本轮验证的是 AST 与手写资源替身。

**没有提供隔离执行器，仍禁止运行。** `isolated_workspace()` 不是布尔声明：受审宿主须实际
检查并强制源码/依赖/schema 白名单、无旧库/业务/seed/用户秘密/模型挂载、网络限制、目录独占，
不能证实就不得 yield。该接口是信任边界，不会检测恶意 Python 调用者伪造宿主对象；venv 或空目录
不能代替这些条件。当前没有可引用的此类平台实施证据，因此缺省宿主在应用/ORM导入前阻断。

未来宿主还须完成以下具体接线（本轮未实现、不得自行执行）：
1. 在同一明确批准作用域提供经核验的 CreationConfig 和真实短期 PilotSessions；
   建案权限仅适配器拥有，不扩展浏览器授权。不要打印、落盘或把秘密放入 URL/HTML。
2. 将 `host.create_case` 绑定 `creation_adapter.create_case`，把同源请求传输绑定此同一个 app，
   保持 `prepare_registered_case_a` 的两案零运行、四份真实登记与回读断言，不直接插库。
3. 仅 HTTPS 127.0.0.1 私有监听；认证 bootstrap、TLS、浏览器和监听生命周期必须在
   owned scope 退出前停止并撤销会话，外层宿主再收回隔离资源。适配器本身不创建监听或会话。
4. 用户批准后才运行真实 ORM/HTTP/浏览器链；未知提交直接停止，不把替身结果称合法登记。

本轮可复验且唯一执行的检查命令：
```sh
python -I tests_acceptance/pilot-creation-authority/check.py
```
6 项标准库检查：固定两案/身份、正文与有效期、异常不重试、上下文限制、手写资源顺序与清理、
真实宿主适配源码 AST 顺序。没有导入应用、FastAPI、ORM，没有创建库、临时资源或真实请求。
