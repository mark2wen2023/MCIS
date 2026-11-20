# 显式服务器验证的案件上下文候选（待独验，未接线）

基线媒体交付 `33e0cebfd096cbdfeb1e29967fbe48a232758eb2`；参考工作台 `16eab9998ca9efe81b32ae9f82cf36511f0a3f01`。新分支 `candidate/verified-case-context`，不改变两旧分支及其默认入口。

## 实际源码依据与改动

- `common/context.py:get_ctx` 明示未认证，从 X-MCIS-Role/Operator 构造身份并默认 Investigator。所审 common 与路由链没有可信登录验证器，不假定网关存在。
- `cases/basic_registration.py:get_case` 使用 CtxDep 后读库；list_cases 直接全案列表，create_case 的caseId来自body。本轮不开放这两条或综合 overview，不能靠客户端挑案构成成员授权。
- `image_review/app.py` 的 register/list_runs/read/review；`audio_review/app.py` 的 attach/listing/get/revise/source_context 均使用 CtxDep。其独立 `_register_*_review_only` 仍不装配本候选；动态 task-backed binding 检查仍在原 handler，不移除。
- `evidence_intake/router.py:authorize/load_receipt/receipt_evidence/download` 保留原角色、个案策略、受限证据、原件字节、历史与容器保护；下载仍记录 Access/审计。下载要求操作者不超过200字符，新主体同样有长度/控制字符边界。

新增 `common/verified_case_context.py` 的 `_install_verified_case_context` 仅供未来明确构造的受限 app 在启动前调用，设置该实例的 `dependency_overrides[get_ctx]`，不覆盖已有 override。没有任何现有入口调用它；默认应用没有因此变得可信。

`_make_verified_case_dependency` 闭包显式接受异步验证器：`verifier(opaque_bearer, case_id, operation) -> CaseGrant | None`。未配置503；缺/重复/无效凭据401；未知范围、结果不匹配403；验证器异常503且不输出异常正文。不读取角色/操作者头或客户端状态。具体凭据有效性、签发者/受众、到期/撤销、主体识别、个案成员和操作权限须由真正的服务器验证器实现；本候选没有实际可用凭据或生产身份提供方。

返回的 CaseGrant 必须包含稳定 subject、现有角色、精确case_id/operation；匹配对象本身不证明可信，**只有受信装配的验证器可生成**。subject 原样作为 Ctx.operator 供既有审计/登记身份绑定使用，不偷偷换回客户端别名。角色映射、旧登记身份兼容仍需真实提供方决策；不提供自动迁移/回退。

## 覆盖表（仅显式安装后的 CtxDep 边界）

固定服务器路由模板 + HTTP方法决定操作，path_params中的caseId只是待验证目标，不是授权：

| 路由 | 操作 |
|---|---|
| GET `/api/v1/cases/{case_id}` | case.read |
| POST `.../evidence-intakes:preview` / `:commit` | evidence.preview / evidence.register |
| GET `.../evidence-intakes/{digest}` 或 `.../evidence/{evidence_id}/intake` | evidence.receipt.read |
| POST `.../evidence-intakes/{digest}:download` | evidence.original.access（不是零写读取） |
| GET/POST `.../image-reviews` | image.list / image.import |
| GET `.../image-reviews/{run_id}` / POST `.../{run_id}/reviews` | image.read / image.revise |
| GET/POST `.../audio-reviews` | audio.list / audio.import |
| GET `.../audio-reviews/{run_id}` / POST `.../{run_id}/revisions` | audio.read / audio.revise |
| GET `.../audio-reviews/source/{digest}` | audio.source.read（会读取原音并核对） |

上述15模板仅增加身份/目标案/操作前置门控，不替代处理器内授权/事务、身份绑定、修订冲突或审计。权限取两者交集，不是全局放行；原件访问不因media.read获准，需单独original.access。资源级更细策略仍由原处理器及将来身份源确定。

**未覆盖/不得开放**：案件列表/创建、overview、普通证据列表、其他工作台业务、报告/归档/任务等未列入模板的 Ctx 路由均拒绝；静态HTML/preview.js和任何不使用CtxDep的路由不受该override保护。不得据此挂全量main或声称全站已保护；独立装配前必须审查整个实际注册集合及依赖解析。当前没有同源/UI入口、没有身份携带实现或按钮。

## 限定验证

```sh
python tests_acceptance/verified-case-context/check.py
```

6组通过，标准库解析候选 AST，剥离 imports 并注入手写 Request/Ctx/problem 与 verifier，未导入FastAPI或应用/ORM。检查默认拒绝、凭据缺失/重复、错案/错操作/角色/主体/异常、逐个15路由验证顺序、实例隔离/拒重复覆盖及真实源码 CtxDep/路由模板匹配。替身 dispatcher 只有取得ctx后才记录handler；拒绝路径无该标记。不是HTTP、FastAPI依赖执行、真实权限或存储验收，不能据此证明任何运行时调用未发生。未读取实际凭据、案件、原音或种子。

## 下一步与阻断

1. 独立静态复核本接入点，确定可信验证器的提供者、凭据生命周期、稳定审计主体/角色映射、按案发现与建案授权方案。没有提供方就保持默认拒绝。
2. 获得允许的干净隔离运行环境后，核查实际FastAPI依赖覆盖与每个路由无绕过，再作同源受限工厂及身份传递；不得启用全量main/模型/归档或复用未经核验的浏览器角色头。
3. 两个全合成案的首次登记导入→保存→刷新重开才是后续全链路验收，还需验证切案草稿、迟到响应、拒绝前无受保护读写和原审计。凭据核查与业务事务并非同一事务，撤销/授权变更的跨请求竞态尚未解决；不承诺服务端并发一致性或冻结报告持久绑定。

未启动应用/HTTP/浏览器/DB/ORM/模型，未执行暂停的权限实测，无合并或部署。
