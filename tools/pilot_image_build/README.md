# 图片试用镜像输入组装：源码审查可执行，构建/运行仍阻断

固定产品输入：`5647d960a9fe7ed3976e9b19219f88ba29939680`。
本工具不安装、联网、构建、加载镜像、启动应用或读取工作区业务材料。
不改变 `container_runner.APPROVED_IMAGES`（仍空），也不授予运行许可。

## 实际交付与命令

`inputs.json` 固定 57 个显式路径、Git blob、大小和 SHA-256：限定应用 Python、
三份页面/脚本、合成准备工具，以及 case/evidence-item/common 三份 schema。
`imports.json` 记录 289 个实际 AST import 节点（含函数作用域和行号）。
包级 __init__ 已纳入；tools/local_review_pilot 无 __init__ 的位置保持原 namespace 语义。
manifest 的 SHA-256 固定在 `package.py` 中，不能通过临时修改清单跳过守门。
所有源文件从固定提交的 Git blob 读取，不从工作树复制、不展开整个仓库。

仅生成**不可构建**的源码审查上下文（本轮已实跑，退出0）：
```sh
python -I tools/pilot_image_build/package.py \
  --repo /path/to/MCIS \
  --ref 5647d960a9fe7ed3976e9b19219f88ba29939680 \
  --target /trusted/exclusive-parent/new-review-directory \
  --source-review-only
```
目标必须全新、父目录受调用者控制且无并发修改；不把目录检查当沙箱或恶意同UID隔离。
结果为 `source/`、`STATUS.json`、`NOT_BUILDABLE.txt`，**不生成 Dockerfile**，不要执行其中应用。
普通模式去掉 `--source-review-only`；当前明确退出2，目标不存在：
`MISSING_TRACK_RECEIPT_TABLE`。不得把源码审查退出0说成可构建或试用通过。

独立工具复验（仅标准库/手造目录和假Git响应）：
```sh
python -I tests_acceptance/pilot-image-build/check.py
```
7组检查通过：源码审查、手造外部字节的构建上下文生成、默认阻断、路径/摘要/重复/缺失、
符号链接、固定Git ref/文件模式、冻结清单。手造“archive”只测试摘要机制，没有加载或认证镜像。
另实跑固定Git对象的源码审查模式：57个输出逐一重算SHA-256一致，确认无Dockerfile，临时目录清理。
生产模式明确拒绝；未执行其他功能/权限/ORM/浏览器检查。

## 新确认的业务调用阻断（不能靠打包掩盖）

| 固定源码位置 | 必要行为 |
|---|---|
| `evidence_intake/router.py:166` `commit_input` | 首次登记调用 `evidence.next_id` |
| `evidence/service.py:154–155` `next_id` | 导入并调用 `track_history.service.reserved` |
| `track_history/service.py:20–25` `reserved` | 查询历史索引及真实 `LocalReceipt`，防止重用已保留证据编号 |
| `track_history/models.py:4` `LocalReceipt` | 表 `track_local_receipts`，具有原有只追加触发器 |
| `common/pilot_core_storage.py:8` / `host_adapter.py:37` | 六个基础表＋一个图片表，没有该表；宿主还严格要求七表集合 |

因此本候选的真实登记首次分配编号会碰到未初始化表。这里是源码推论，不是运行过的异常。
不能删 reserved、补空返回或假表。本轮不改产品，后续最小产品项须审查并同时补齐真实模型、
触发器、依赖检查及宿主准确表集合，再冻结新的产品ref/清单；不能仅清掉 blocked 字段。
这纠正了上一轮“只差镜像”的判断：现在同时有明确产品依赖阻断和外部镜像缺项。

## 有限导入闭包及遗漏边界

- 正常授权选案/单案→原create_case→preview/commit→receipt→图片import/list/read/review；
  app只注册原有允许路由，原角色/策略/历史/容器/审计/冲突守门没有改动。
- 新加入 track_history 的服务/模型及 working_records_archive.validation 是 `reserved` 的
  真实传递导入。它们不会因此注册归档路由，也不会初始化其中所有模型。
- `common.contracts` 只需要上述三份 schema；其 registry glob 在最小目录只看这三份，
  case/evidence-item 的相对 `$ref` 指向 common，common没有外部业务schema引用。
  没有用网络获取schema，也没有执行jsonschema或应用验证。
- `config.PROJECT_ROOT` 仍由固定源路径算出 `/opt/pilot/source`；Settings未实例化，
  `seed_demo=True` 的默认不被此路径消费。不能据此改变普通应用默认或声称默认零种子。
- 清单不含 main、models_registry、模型任务、种子、原件或报告生成。
  未复制的17处局部导入在 imports.json 各有排除依据：全量注册/建库/下载/报告与归档入口不调用；
  图片task绑定前必须维持已有 imported-only 拒绝。排除说明不等于形式化不可达证明。
- imported-only read/review 之外的任意调用、反射、插件、第三方动态加载以及镜像标准库/二进制
  不是这份本地 AST 表证明的范围。只有固定源码及固定专用流程的审查候选，不称所有路径闭合。

## 外部输入：准确需要什么，当前缺什么

当前 `inputs.json.external` 为 `unverified`，所有未知摘要/大小明确为 null，没有伪锁文件。
需要一个已离线准备并审定的运行基础镜像，不是当前任意venv，也不能COPY整个checkout。
该输入目录必须只包含以下两个普通文件（拒绝软链、硬链接、额外项；核对精确大小/SHA-256）：

1. `pilot-runtime-base.oci.tar`：离线基础镜像归档；必须核实格式与目标离线构建器兼容。
   审计记录将归档SHA-256与实际镜像完整 `sha256:<64hex>` ID对应起来。
2. `pilot-runtime-base.inventory.json`：完整层/文件清单及来源审计记录，精确版本、路径、文件类型、
   链接目标、字节摘要、Python平台/ABI、传递依赖、共享库、浏览器版本、许可证及归档→镜像ID绑定。
   必须证明没有业务数据/seed/模型/凭据/profile、额外执行钩子或未列代码。

固定能力路径：`/opt/pilot/bin/python`（3.11+）；`/opt/pilot/chromium/chrome`；
`/usr/bin/openssl`、`/usr/bin/certutil`。Python直接外部根为 fastapi、sqlalchemy、jsonschema、
referencing、uvicorn、playwright，及它们实际版本所需的全部传递包、标准库SQLite/SSL/zlib、
浏览器与系统共享库。这里不猜版本；匹配的真实文件与官方/可信来源尚未取得或核验。
禁止editable/.pth/sitecustomize/用户site；镜像用户65532:65532、固定两项Env、无卷/端口/入口，
符合现有控制器要求。TLS临时NSS信任和Chromium sandbox必须在受支持隔离平台保持开启，不能绕过。

打包器仅校验这两个文件的精确字节；**不会**将校验和相等当作镜像内容或清单一致性证明，
也不加载/解包/执行归档。只有独立核对上述绑定后，才可在受审源码增量填写锁值/status；
修改manifest必须同步审查固定代码摘要。当前缺少两份真实输入及其可信映射，不能构建。

`package.py::recipe(base)` 是实际可执行Dockerfile生成器：固定 FROM 镜像ID，
只 COPY 已校验 source 树及已校验 entry.py，设置非root、固定环境、私有解释器；没有RUN/安装。
当产品阻断和外部锁都解决，普通模式才输出 Dockerfile 与仅允许这些输入的 .dockerignore。
不会把基础归档复制进构建上下文。不自动执行build/load；未来须用无外网且已装入同一固定base的
受审构建器，不能把 `--network=none`（仅RUN网络）误当禁止解析/拉取FROM的保证。
成品镜像仍需独立核对再加入运行器批准表；打包/构建均不自动批准运行。

## 后续真实验收记录边界

首次运行批准后仅记录固定枚举阶段（preflight / ready / cases / receipts / zero-runs /
import / revision / reopen / switch / cleanup）、passed/failed/unknown、退出码及清理结果。
禁止导出日志正文、原始响应或未知截图；当前runtime还未实现此分阶段结果协议，需在实跑前补齐。
既有driver只检查A/B获授权案正常切换，不包含不对称权限、真实冲突、迟到响应或原图渲染。
本轮没有构建或运行镜像，未运行HTTP、ORM、服务、浏览器、模型或4A；没有读取业务材料。
