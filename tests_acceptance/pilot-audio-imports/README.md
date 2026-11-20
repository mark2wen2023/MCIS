# Pilot 音频既有结果导入：默认关闭 API 切片

基线 `6b3854e4d2d34212eedfcfb43b3d39ea36c07bc9`，仅
`candidate/zhihai-evidence-workbench`。不是已启用的询问 UI 或运行验收。

## 缺口与最小改动

旧 `_register_audio_review_only` 不挂任务路由，但仍挂 `/source/{digest}` 和旧HTML；
`check` 遇 task-backed 初始记录仍读取 WAV 后动态导入 tasks。无法直接当成 pilot
“仅人工导入、无播放/任务”能力使用。旧源函数配手写 source/task 替身实证了该顺序。

本轮保留原入口；新增私有 `_mount_audio_imports_only`，只复用原 router 的四个
route 对象：POST/GET `/api/v1/cases/{case_id}/audio-reviews`、
GET `/{run_id}`、POST `/{run_id}/revisions`。保持原响应/201/NoStoreRoute 元数据，
不复制处理器，不挂 source、HTML、下载、任务或模型接口。

- 专用 factory 新增 `audio_imports=False`、`audio_blob_dir=None`。显式开启才装配；
  同工厂图音同时开启必须使用同一个绝对 blob 根；登记回执 reader 共用且不重复挂载。
  `evidence_registration` 仍另行显式开启，可供图或音使用既有完整 preview/commit。
- 始终复用当前服务器会话依赖；调用方需另行赋予明确案号+音频操作授权，现有图片
  准备器/会话不因此自动获得音频权限。URL/角色头不是身份，没有新增默认角色。
- 列表、详情、修订均在原业务 authorize 之后检查 imported-only；只要存在 artifactTaskId
  就明确拒绝，列表整体拒绝而非隐藏任务记录伪造完整清单。详情/修订在 source/任务模块前拒绝。
- 导入 body 严格集合、两个合法登记回执、v2/v3机器稿、原采样时基及来源摘要校验原样保留；
  `attach/source/receipt/matched_source/validate/get/revise` 等指定业务函数 AST 未改。
  列表仍声明 sourceCheck 未执行，不冒称原件验证；修订冲突412、审计和追加逻辑未改。
- 限定初始化使用真实 Revision.__table__，不因共享 registry 曾加载任务模型就建任务表；
  两条原 UPDATE/DELETE 只追加触发器 SQL 及正常初始化分支保留。没有假表或全量 registry。

实际服务仍会在合法导入/读取/修订中按原规则读取已登记原音以核验字节；本轮测试完全
以手写替身代替，没有访问 WAV 或数据库。上述检查不是身份认证/真实权限测试。

## 复跑

```sh
python3 -I tests_acceptance/pilot-audio-imports/check.py
python3 -I tests_acceptance/pilot-factory/check.py
python3 -I tests_acceptance/pilot-image-imports/check.py
python3 -I tests_acceptance/pilot-registration/check.py
node tests_acceptance/pilot-workbench/check.cjs
python3 -I tests_acceptance/pilot-pages/check.py
python3 -I tests_acceptance/zhihai-workbench/check.py
```

新9组涵盖旧调用顺序反例/限定拒绝、真实源函数的list/get/revise执行顺序、正常导入记录
修订与412、legacy任务绑定、原业务AST等价、route对象复用/重复注册/白名单异常、真实表与
触发器的假engine顺序/初始化失败、factory默认关闭和精确会话操作替身。相邻检查本轮
均退出0；不合计历史验证为全量覆盖。没有导入真实 app/FastAPI/ORM，没有HTTP/浏览器/播放。

## 尚未贯通

音频 HTML 与深蓝工作台一字未改，没有新的“询问/音频”链接。下一步须用服务器能力塑形
原音频页，禁用播放/下载/任务动作，保持同源Cookie、草稿/迟到/重开保护，并在确切页和API
同工厂挂载后才显示入口。当前图片宿主只准备图片，其空表检查不覆盖音频；不可擅自用它
跑音频。真实两份回执准备、短期权限、实际ORM/HTTP/会话与浏览器验收仍需隔离批准。

新冻结见 `logs/pilot-audio-imports-impl-hashes-frozen.txt`。旧图片/58文件/OCI冻结和允许表
不变，此候选不在旧可复现镜像输入中，不宣称可构建或已运行。
