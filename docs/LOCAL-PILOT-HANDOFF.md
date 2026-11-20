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
