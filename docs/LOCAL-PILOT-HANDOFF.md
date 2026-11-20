# 粤海探析：云端交付 → 本机合成图片试用

这是候选源码交接，不是已运行的产品。当前只批准源码复核；不要执行旧 README 的全量启动、安装、归档或演示命令。普通 clone/fetch 不是资料净化：Git 对象可能含历史资料，本轮仅按下面白名单检出源码，不打开案件、seed、原件或凭据。

## 固定版本与边界

| 成果 / 分支 | 固定提交与入口 | 与本候选关系 / 验证边界 |
|---|---|---|
| 主候选 `candidate/local-review-pilot` | [6169caf97ab512587431ed65ca503ccb1b7886d6](https://github.com/mark2wen2023/MCIS/tree/6169caf97ab512587431ed65ca503ccb1b7886d6/tools/pilot_image_acceptance) | 包含专用工厂、受信会话、两案准备、真实登记/图片核对处理器接线、宿主/容器运行器和有界阶段回执；仅源码与合成替身验证，未实启。 |
| 固定打包源码 | [3a615bf6d449c90eb0a64d25c20c5cdc83fdd06c](https://github.com/mark2wen2023/MCIS/tree/3a615bf6d449c90eb0a64d25c20c5cdc83fdd06c) | `tools/pilot_image_build/inputs.json` 冻结此产品头的 58 文件；6169caf 更新包装输入。本说明提交不刷新这些哈希。回执中的 `productBaseline=0a7232c6a24adb52720d9d65438fc1b0cf537a29` 是仪表化前基线，不能当当前源码头。 |
| 独立媒体交付 `candidate/media-demo-lazy-factory` | [33e0cebfd096cbdfeb1e29967fbe48a232758eb2](https://github.com/mark2wen2023/MCIS/tree/33e0cebfd096cbdfeb1e29967fbe48a232758eb2/tools/evidence_ui_offline) | 此头已是主候选祖先；该分支仍保持原固定交付，双检出入口只验证其指定媒体/工作台头，不能宣称覆盖后来主候选。独立图音页合成脚本不是浏览器联调。 |
| 七步工作台 `candidate/ui-workbench-integrated` | [16eab9998ca9efe81b32ae9f82cf36511f0a3f01](https://github.com/mark2wen2023/MCIS/tree/16eab9998ca9efe81b32ae9f82cf36511f0a3f01/web) | 不在主候选祖先链中；React 七步导航、显式选案及缺项提示为独立成果。主候选使用窄试用 HTML，没有合并整个工作台及其后台请求。既有离线 SSR/逻辑、TS/Vite 证据，不是浏览器验收；本轮未重跑。 |
| 跨仓 A 初版 `candidate/shared-trajectory-cross-repo-fixtures` | [4181b86c8333bbde6037ba6d5385de1d187ec57b](https://github.com/mark2wen2023/MCIS/tree/4181b86c8333bbde6037ba6d5385de1d187ec57b) | 独立人工合成契约样例，保留 6–7 秒缺口反例，未并入图片试用。 |
| 跨仓 A 扩展 `candidate/shared-trajectory-cross-repo-expanded` | [2048c60fd6650c6f2c99a76a16be463a3895655d](https://github.com/mark2wen2023/MCIS/tree/2048c60fd6650c6f2c99a76a16be463a3895655d) | 独立两船/混案 JSON、哈希及纯契约检查；不是业务导出或 Chromium 消费验收，本轮未重跑。 |

不为交接合并这些分支；不改 main、mcis-3d 或共享轨迹合同。当前可核对主候选代码，不可直接把多分支当成一条已跑通流程。此前宽泛交接见独立 [交接文档分支](https://github.com/mark2wen2023/MCIS/blob/7d691f8ea6fead7ef1a172ad3e163470a7c2a7c6/docs/CANDIDATE-COLLEAGUE-HANDOFF.md)，本页优先说明本机图片试用准备。

## 第一步：不改原工作树的固定源码复核

在可信的现有 MCIS Git 仓库中操作；先将下面两个绝对路径换成自己的路径。新 worktree 目标必须不存在。以下不会切换原工作树；fetch 仅更新对象/FETCH_HEAD。若远端不是指定 MCIS、仓库浅克隆或对象缺失则停止，另准备完整无工作树的可信源码仓库，不自动补拉资料或放宽哈希。

```bash
repo=/absolute/path/to/MCIS
review=/absolute/path/to/new-pilot-source-review
code=6169caf97ab512587431ed65ca503ccb1b7886d6
product=3a615bf6d449c90eb0a64d25c20c5cdc83fdd06c
# 第一条核查命令：输出必须是 mark2wen2023/MCIS 的可信 origin。
git -C "$repo" remote get-url origin
# 人工核对上行后再继续；禁止改已有工作树或自动选用别的仓库。
git -C "$repo" fetch --no-tags origin refs/heads/candidate/local-review-pilot
test "$(git -C "$repo" rev-parse --is-shallow-repository)" = false || exit 2
for ref in "$code" "$product" fce90d30cb94deb1069dca90c78693316e03c5c7 5ab815fd4e4386bbd716d7f092a5ccb903368827; do
  git -C "$repo" cat-file -e "$ref^{commit}" || exit 2
done
git -C "$repo" merge-base --is-ancestor "$code" FETCH_HEAD || exit 2
test ! -e "$review" || exit 2
git -C "$repo" worktree add --detach --no-checkout "$review" "$code" || exit 2
git -C "$review" sparse-checkout init --no-cone || exit 2
git -C "$review" sparse-checkout set --no-cone  /tools/pilot_image_acceptance/ /tools/pilot_image_build/  /service/mcis_service/common/pilot_core_storage.py  /logs/pilot-stage-receipt-build.json  /tests_acceptance/pilot-stage-receipt/ /tests_acceptance/pilot-runtime-host/  /tests_acceptance/pilot-image-fixture/ /tests_acceptance/pilot-core-storage/  /tests_acceptance/pilot-creation-authority/ /tests_acceptance/pilot-image-build/ || exit 2
git -C "$review" checkout --detach "$code" || exit 2
test "$(git -C "$review" rev-parse HEAD)" = "$code" || exit 2
cd "$review" || exit 2
for suite in pilot-stage-receipt pilot-runtime-host pilot-image-fixture pilot-core-storage pilot-creation-authority pilot-image-build; do
  python3 -I "tests_acceptance/$suite/check.py" || exit 2
done
```

需要现成 Git、Python 3.12 标准库（云端实测 3.12.14），不安装依赖，不需要 Node、FastAPI、SQLAlchemy 或 Docker。脚本部分从固定 Git 对象抽 AST；不会导入应用、实例化 ORM 或执行准备器。稀疏检出不是操作系统隔离。文档后来提交不改变上面的代码版本；不要把分支当前 head 自动替换进冻结参数。

本轮在新的普通源码稀疏 worktree 实跑：阶段回执 6、宿主替身 4、合成夹具 5、窄存储 11、创建授权替身 6、构建工具 7 组，各退出 0。覆盖有界输出/非法记录/超时与清理未知、手写生命周期、源代码顺序、真实模型/触发器 AST 等；不与历史轮次相加，不等于真实鉴权、ORM、HTTP、浏览器、容器或 CI。

可继续仅提取固定允许源码（新目标，不已有目录）：

```bash
# 请换成自己独占的临时父目录下尚不存在的路径；不放业务资料。
source_target=/absolute/path/to/new-source-review-output
python3 -I tools/pilot_image_build/package.py --repo "$review" --ref "$product"  --target "$source_target" --source-review-only
```

通过标准：退出 0，`files=58, buildable=false, runtimeApproved=false`，没有 Dockerfile。云端已实跑该路径。去掉 `--source-review-only` 的默认路径目前应退出 **2**、报 `Runtime base not frozen/reviewed`，且不创建目标；云端也已确认。`blocked=[]` 只表示当前列出的源码阻断已修，不表示外部输入齐全或批准启动。

## 本机环境门槛：先盘点，不能直接 build/run

可在本机只读检查 `uname -m`、`docker version`、`docker info`、`docker buildx ls`、`docker buildx inspect <已选名称>`（不要加 `--bootstrap`）。记录客户端/Engine 版本、Engine OS/架构、builder 名称/driver/节点/实际支持平台；不要外发完整环境输出或凭据。云端未执行这些命令，也没有已验证 Docker 或托管 CI。

当前参考是 **Linux amd64** 路径，不代表已实跑。Apple Silicon 的 Mac 主机与 Linux Docker VM 是两层；通常 VM 为 arm64，不能据 Mac 可用就宣称 amd64 原生可用。若走 amd64 仿真，需单独核实 Python 原生库、Chromium sandbox、TLS/NSS、时序与资源限制；若做原生 arm64，需另行冻结该平台全部依赖及镜像，不复用 amd64 摘要。当前运行器没有用 `--platform` 替你完成平台验证。

`docker` driver 与 `docker-container` driver 的内容库不同：Engine 已 load 的基础镜像不保证后者可见。当前配方 `FROM sha256:<config ID>` 能否由所选 builder 离线解析，必须先核实。`--network=none` 只限制构建 RUN 的网络，不保证 FROM、frontend、builder 引导或镜像解析不联网；配方没有 RUN 也不是断网证明。未证明离线解析时停止，不能临时拉取、不明转存或改白名单绕过。

## 必须先审阅的外部输入（目前不存在可用锁定值）

现有 `inputs.json.external` 是 `unverified`，摘要/大小/镜像 ID 为 null；**不是现成输入或批准表**。所需独立目录只允许两个普通文件：

- `pilot-runtime-base.oci.tar`：完整离线基础镜像归档，确切字节数与整个 tar 的 SHA-256。
- `pilot-runtime-base.inventory.json`：完整盘点文件，确切字节数与其文件 SHA-256。

盘点至少应提供：可信来源及取得/复核方式；归档格式与版本；OS/架构/variant；平台索引（如有）及选定 manifest 的 digest；config digest/Engine image ID；各 layer digest 与解压 diff ID；对应文件清单/摘要；Python 解释器和全部依赖精确版本/平台/来源/摘要；Chromium、Playwright、动态库、OpenSSL、NSS certutil 的位置与版本/摘要；非 root 用户、所需 HOME/临时目录、sandbox/TLS 的前置；不存在业务/seed/模型/凭据、用户 site、editable/.pth 自动执行及非预期启动钩子的复核证据。只列一个 FastAPI 版本不够。

**三种摘要不能互换**：tar SHA 校验传递的归档字节；image config ID 校验配置对象（Engine `.Id`）；manifest/index digest 校验 OCI 内容引用关系与选定平台。若拿到的是 Docker save 格式而非 OCI layout，必须明确格式和 loader/builder 对应方式，不能只改扩展名。

验证顺序：可信来源/独占目录 → 文件集合/普通文件/无软硬链接/大小及 tar 与 inventory 字节哈希 → 独立审阅归档各 manifest/config/layer 的对应及实际内容盘点 → 平台与 builder 离线输入可见性 → 固定外部输入的新审阅提交 → 获得本机运行许可后才构建和检查最终镜像 → 另审最终镜像 ID 才可进入运行器允许表。现有打包器只校验已锁定归档/盘点的字节，不证明归档与盘点内容互相真实对应，不会加载镜像。当前镜像允许表仍为空，本轮未修改。

## 获得隔离运行许可后的首轮（本轮未执行）

必须先具备审核过的离线最终镜像、正确平台、可信本机执行器和明确批准。保留无业务/账号/旧库挂载、无外网和端口发布、非 root、只读根、新独占 tmpfs、完整 Chromium sandbox；容器内仅 HTTPS 127.0.0.1。不能挂 Docker socket、复用浏览器 profile、关闭 TLS/sandbox 校验或访问 4A。由源码运行器自行管理短期服务器会话；不打印/传 URL/写页面秘密，不默认 Investigator。

执行入口是 `tools/pilot_image_acceptance/container_runner.py`；**当前没有获批准的 image 参数，不能现在运行**。获准后的编排应依次确认：

1. 预检 → HTTPS 就绪；以原 create_case 授权业务逻辑准备两个人工合成案。
2. 案 A 初始零图片运行，四份合成材料通过原 preview/commit 获得同案登记回执；不可直接插表或假造 requestDigest。
3. 页面首次导入 → 修改一行并保存 → 刷新后同一运行/正文 → 正常已授权 A/B 切换。
4. 内程撤销会话、关闭浏览器/服务、清理自身目录；外程确认退出及容器移除。

唯一结果是有界单条 `mcis.synthetic-image-acceptance/1` 回执，阶段为 `preflight / https_ready / cases_zero_runs / four_receipts / first_import / save_reopen / authorized_switch / cleanup`。记录固定 `productBaseline`、`build`、`image` 和有限状态/退出码，不输出原日志、browser dict、路径、案号或 Cookie。`build` 是固定六源码的仪表化摘要，不是整个基础镜像的摘要。缺结果、非法/多条/超长记录、超时、未知退出或任一清理未确认，都不能通过；成功必须有效内程全阶段通过、正常容器退出并确认外层清理。

当前用例只计划正常授权切案，不覆盖不对称权限、真实并发冲突/迟到响应、原图渲染；音频、完整七步工作台、报告冻结持久绑定/权限交集/同一读取视图、保存到报告导出重开均不在本轮已装配验收内。图音源页/纯逻辑的历史绿色结果不能补足这些运行证据。下一步是准备并审阅上述外部输入与本机平台，不能再用一份空模板替代它们。


## 新增：本机 OCI 元数据预检（不批准镜像）

`tools/oci_metadata_review/check.py` 是独立标准库工具，不接入打包器或运行器。交付代码基线仍是上述 6169caf / 3a615bf；下面工具是后续独立增量，不在旧源码快照中。可从交付回信的**完整提交**取出这一个普通源码文件，不改现有工作树：

```bash
# repo 沿用上文；tool_ref 必须填本次交付回信的完整 40 位提交，不能填分支名。
tool_ref=填入本次交付完整提交
case "$tool_ref" in *[!0-9a-f]*|'') exit 2;; esac
test "${#tool_ref}" -eq 40 || exit 2
git -C "$repo" cat-file -e "$tool_ref^{commit}" || exit 2
# 新建的自有临时目录，只写工具源码；不向其中解包镜像。
review_tool_dir=$(mktemp -d) || exit 2
git -C "$repo" show "$tool_ref:tools/oci_metadata_review/check.py" > "$review_tool_dir/check.py" || exit 2
# 三项必须由获得授权的文件所有者/可信传递记录提供，不是示例凭据或现成镜像。
archive=/absolute/path/to/authorized-offline-archive.tar
expected_sha256=填入可信传递记录的64位tar摘要
expected_bytes=填入确切十进制字节数
python3 -I "$review_tool_dir/check.py" --archive "$archive" \
 --sha256 "$expected_sha256" --size "$expected_bytes" --platform linux/amd64
```

工具不联网，不调用 Git/Docker，不读取环境配置，不解包、不写文件、不执行镜像内容。调用者须保证授权输入在自己控制、无并发写入的可信目录中；工具以 `O_NOFOLLOW` 打开一个普通且单链接的文件描述符，前后核对 inode/大小/修改时间，不以这些检查冒充文件系统沙箱或恶意同 UID 写者隔离。父目录/解释器的可信性仍是前提。

支持面刻意很窄：**未压缩 USTAR、OCI Image Layout 1.0.0、单 manifest、单目标平台**。仅 `oci-layout`、`index.json` 和实际引用的 `blobs/sha256/<64小写hex>` 普通文件；不能附目录项。index 只能一个 OCI manifest 描述符且必须显式声明 platform；manifest/config 描述符采用 OCI v1 media type；layer 仅接受 `application/vnd.oci.image.layer.v1.tar+gzip` 描述符。允许 linux/amd64（默认）或显式 linux/arm64/v8，index 与 config 必须同时匹配。arm64 的结构通过不表示 ARM 运行已验。

拒绝 Docker-save、压缩外层 tar、PAX/GNU 扩展、嵌套/多平台 index、annotations/URL 等未支持的描述符扩展、额外/重复/穿越路径、目录/软硬链接/设备成员、错误头校验和/字节摘要/长度、未知平台和超限。上限：归档 8 GiB、成员 4096、每份 JSON 元数据 1 MiB；流式检查 blob，不将 layer 全部载入内存。config 中命令、环境、历史等任意内容不会回显或执行。

退出 0 只表示 `result=metadata_checked`：输出固定 schema `mcis.oci-metadata-review/1`、tar SHA/大小、目标平台、选定 manifest/config digest、layer/member 数量；`runtimeApproved / inventoryVerified / rootfsDiffIdsVerified / dependencyAbiVerified / provenanceVerified / builderVerified` 均为 false。退出 2 输出固定失败码，不输出输入路径/任意元数据/异常栈：`ARCHIVE_HASH/SIZE` 是传递字节不符，`BLOB_HASH` 是成员内容不符，`DESCRIPTOR_MISMATCH` 是引用长度/摘要不符，`PLATFORM_MISMATCH/CONFIG_PLATFORM/AMBIGUOUS_PLATFORM` 是平台不明，`MEMBER_* / TAR_* / UNSUPPORTED_* / *_LIMIT / INPUT_* / JSON_*` 分别指出路径格式、支持面、预算或输入问题。失败不能通过改媒体类型/删成员/自算新期望摘要而伪装原输入通过。

本轮仅新生成的微型全合成归档测试：`python3 -I tests_acceptance/oci-metadata-review/check.py`，9 组退出 0。CLI 正常/拒绝亦在临时文件上实测，不使用实际基础镜像。gzip blob 只核对压缩字节，**不验证 gzip 流或解压后 tar 内容，也不验证 diff ID**（仅检查 rootfs 声明的格式/数量）；不验证 ABI、依赖/Chromium/TLS 实际存在、镜像来源、inventory 与 rootfs 一致性、builder 可见性或运行权限。通过后仍须按上节独立审阅实际 rootfs 与依赖、来源及平台，冻结外部输入、批准最终镜像；当前允许表为空和默认构建拒绝保持不变。
