# 图片人工导入垂直 API 切片（未运行）

基线 `159a3dda557b3998c5b2c2d23c243cb81641ca13`。
仅专用试用工厂显式 `image_imports=True` 且提供绝对 `Path` 型 `image_blob_dir`
时挂载，仍要求 enabled=True / 服务器会话 / HTTPS回环 / 新库。
绝对路径检查不是隔离或可信性证明；目录必须由受信启动器独占准备，不能指向业务挂载。
默认三路由及正常应用入口不变，不装配全量 main、registry、launcher。

## 已接源码

原三条 GET 外增加且最终核对白名单：
- GET /api/v1/cases/{case_id}/evidence-intakes/{digest}：原 receipt_input，保留 NoStoreRoute。
- POST /api/v1/cases/{case_id}/image-reviews：原 register，四份同案回执导入。
- GET /api/v1/cases/{case_id}/image-reviews：原列表，新增限定来源拒绝。
- GET /api/v1/cases/{case_id}/image-reviews/{run_id}：原详情，新增限定来源拒绝。
- POST /api/v1/cases/{case_id}/image-reviews/{run_id}/reviews：原人工修订，新增限定来源拒绝。

所有这些原处理器使用 CtxDep，经同一 app 的 verified case dependency override。
许可集合仍须分别有 evidence.receipt.read / image.import / image.list / image.read /
image.revise；不由有 case.read 推导其它权限。没有静态图片页、下载、任务、音频、报告
或归档写入路由。工作台没有新增图音按钮，当前还不是 UI 完整试用闭环。

`_mount_image_imports_only` 是实际工厂调用的私有挂载函数，服务器 state 标记仅由装配
设置。列表/详情/修订在原 authorize 之后检查初始记录：必须 mode=imported-existing-output，
且不能出现 artifactTaskId（含 null）；未知 mode 也拒绝。列表含一个不支持项就整次报
409 OCR_IMPORTED_SOURCE_ONLY，不返回部分清单或伪造空清单。详情/修订在读取回执字节和
动态 tasks 导入之前拒绝；不是查假任务表，也不是把缺表 SQL 异常伪装为安全拒绝。
原人工 register 严格只收 bindings 和 acknowledgeArchiveBlocked，不能从请求插入任务字段。

正常模式无此标记，原 receipts → verify_task_binding 顺序不变。
初始候选解析、来源 SHA 比对、配额、逐案记录查询、412 OCR_REVISION、append/audit
均未减条件。AST 去掉三处新增守门后与旧版函数逐个相等（初始化单独验证）。
原件历史查询、AccessPolicy、回执/保管链绑定仍在原函数，不修改其实现。
容器下载路径未挂载，不通过替代端点交付原件字节，也未移除原下载保护。

## 存储与尚未完成

先调用原专用六表初始化；再调用真实图片初始化，限定 `tables=[Record.__table__]`。
即使同进程其它代码曾注册 Task，也不在这里创建 task 表；保留原两条 OCR trigger SQL。
正常图片初始化仍采用原全 metadata 路径，原完整/限定注册行为保持。
DDL 分段执行，不承诺事务原子性；失败不得服务请求，应丢弃临时库，不自动重试。

同案已登记回执、四份文件与审计/保管链记录仍需合法生成。本工厂没有登记 preview/commit
接口，也没有自动合成记录或绕过校验的填充；下一轮需获准的可信合成夹具准备，或者经过
独立审查再挂现有必要登记路由。缺少这些材料时原接口照常拒绝，不保证现在就能导入。
还需真实 ORM、SQL trigger、FastAPI dependency override/NoStoreRoute、Cookie/TLS、
授权与原件完整性隔离验收；当前均未运行，旧暂停不解除。
下一轮运行前置仍按 pilot-factory/REVIEW.md：无业务挂载/外网业务访问、私有HTTPS回环、
新临时库和文件根、短期可信会话；发生偏离或失败停止、撤销会话、清理临时环境。

## 实跑证据

```
python -I tests_acceptance/pilot-image-imports/check.py
python -I tests_acceptance/pilot-factory/check.py
python -I tests_acceptance/pilot-core-storage/check.py
node tests_acceptance/pilot-workbench/check.cjs
```

分别7组新图片AST/手写替身、5组工厂、9组存储及9组UI通过，退出0；不合计为全链覆盖。
新检查覆盖：旧头列表反例、三入口拒绝早于字节/任务加载/写入，人工详情/修订及冲突顺序，
正常模式任务验证，未知来源拒绝，真实初始化函数的显式表与相同trigger SQL、DDL异常，
真实私有挂载函数+从生产装饰器提取的路由集合在工厂组成8条白名单。
工厂接线测试仍是手写 FastAPI/Depends/Router/DB，不是真实依赖解析、权限或ORM测试。
未导入应用、SQLAlchemy、FastAPI；没有网络、服务、浏览器、模型、真实资料或seed读取。
