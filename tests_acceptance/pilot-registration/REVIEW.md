# 试用图片登记输入：复用真实 preview/commit（未执行）

基线 cb3f2fd895c3785cef611d522059ad263554d92d。
本次只修改专用 factory：新增 `evidence_registration=False`，仅当显式 True 且
image_imports=True（另有 enabled=True、服务器会话、HTTPS回环、新库/绝对素材根）才注册：

- POST /api/v1/cases/{case_id}/evidence-intakes:preview → 原 preview_input
- POST /api/v1/cases/{case_id}/evidence-intakes:commit → 原 commit_input

通过已有 NoStoreRoute 路由类挂载，不引入整个 intake router；最终白名单为12条。
默认不开登记时图片模式仍10条，不开图片仍3条。无登记UI、下载、任务、全案列表或新身份。
同一 verified context override 要求服务器逐案 `evidence.preview` / `evidence.register`
许可；case.read、image.import 或其中一个登记操作不代表拥有另一个操作。
没有硬编码会话、客户端角色默认、简化登记或直接插库路径。
原登记函数完整保留：authorize→有界JSON/base64→元数据/确认字段→同身份预览摘要重算→
同案历史/回执查询→证据schema→证据行→Register保管链及audit→独占文件写入。
重复请求核对旧回执后返回；摘要变化报INTAKE_STALE；清理/提交异常保留原行为。
没有改变事务或声称文件与数据库原子提交，不自动重试。

## 真实依赖核对（仅静态）

- authorize：CaseRow、AccessPolicyRow；原角色、Restricted和完整读取策略检查保留。
- load_receipt：EvidenceRow、CustodyEventRow、ArchiveImportHistoryRow；历史命中先
  require_content 再 ARCHIVE_HISTORY_ONLY；原文件字节/登记/保管链绑定核验保留。
- commit：EvidenceRow + CustodyEventRow；evidence.service.append_custody 调用 audit.append，
  因此 AuditEventRow 仍必要。六表初始化及只追加trigger不变，图片表初始化不变。
- contracts.validate('evidence-item') 调用 common/contracts.py 的schema registry：首次请求
  会读取 PROJECT_ROOT/contracts/schemas 下的schema集合。受控运行包必须冻结并提供这些
  schema及jsonschema/referencing依赖，不得指向业务checkout、不得以空schema替代。
- 素材根来自受信构造参数；绝对路径检查不是隔离证明。原独占写入/路径检查仍执行。

这只开放合成试用专用装配，不证明上传字节本身一定是合成。准备会话必须仅交给受信
离线合成夹具执行者，环境无真实材料；不得以SYN案号/文件名冒充真实性证明或把此开关
用于真实案件。普通入口与其它候选不变。

## 获准后案 A 的准备与验收顺序（本轮未执行）

0. 私有本机临时环境，无业务挂载、无外网业务访问；新库、新素材根、固定schema。
   4A之外受信引导发放短期服务器Cookie会话，逐案逐操作许可，不放页面/URL/日志。
   合成案 A 必须由获准的既有合法建案流程存在；本工厂不造案件行，也未挂建案接口。
1. GET 同案详情核实 A；显式 GET A/image-reviews 必须返回成功空列表。
   读取失败、身份不符、非空或未知均停止，不把失败当零运行。
2. 对纯手造 PDF、PNG、原始OCR JSON、候选JSON逐份调用真实 preview。
   按原字段提交 profile/fileName/contentBase64 和全部元数据，Restricted；提取时间为明确
   合成声明，不拿运行时间代填。候选的三项来源SHA来自这批实际合成字节。
3. 受信准备者核对预览的caseId、fileName、sourceSha256及元数据，然后仅对该份原请求
   添加 confirmed:true 和本次服务器返回的 requestDigest 调用真实 commit。
   不把sourceSha256当requestDigest，不自行计算/填造回执，不绕过校验或自动重试未知结果。
4. 每次成功回执核对同案/证据ID/摘要，再从现有GET receipt按requestDigest重读核对。
   只有四份均成功确认，才按 pdf/image/raw/candidate 汇集四个requestDigest。
5. 再GET A/image-reviews，必须仍成功为[]。这才是“已合法登记但零核对运行”的起点。
   此准备阶段不得POST image-reviews；禁止直接插回执或为了验收先建图片运行。
6. 撤销准备会话，另由受信引导提供仅试用所需授权；之后的图片导入/保存/刷新重开才进入
   下一阶段。服务器仍逐次检查各操作。任何异常立即停止，未知结果人工核对；退出停服务、
   撤销会话并按批准流程清理临时库/目录。

上述状态尚未建立/验证；未执行准备器、真实登记或任何HTTP/ORM。尚待明确运行许可、
可信合成案与素材准备、Cookie/TLS/真实ORM及回执一致性验收，不能宣称闭环跑通。

## 本轮实跑

```
python -I tests_acceptance/pilot-registration/check.py
python -I tests_acceptance/pilot-factory/check.py
python -I tests_acceptance/pilot-image-imports/check.py
```

分别4组新增、5组相邻工厂、7组图片API AST/手写替身通过，退出0；不合计为全链覆盖。
新检查：开关/12条精确路由、真实函数定义的对象引用、默认不执行处理器/准备、非法配置
早停、同服务器会话的逐案逐操作/撤销检查、原commit校验顺序静态核对。
原preview/commit仅从固定源码编译定义（假注解/默认依赖），从未调用其函数体；
原登记文件未修改。不是实际FastAPI依赖解析、权限实测、文件或数据库写入测试。
没有运行应用、HTTP、浏览器、DB/ORM、模型或读取真实材料、seed、凭据。
