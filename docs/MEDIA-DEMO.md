# 合成图像／音频隔离演示指南

> **当前暂停：不得执行本指南中的 prepare、launch、应用初始化、TestClient 或归档测试；第1节依赖执行命令、第2–4节操作仅作历史参考，不是执行许可。**
>
> 当前产品固定头为 `53e59cac17542975eb697770cb3ac5c7345af129`。其 `service/mcis_service/main.py:40–42` 顶层导入 `haili5_seed`、`lily_mary`、`yangze22`；`seed_demo=False` 只跳过填充函数，不能阻止含案例常量的模块被 Python 加载。历史“仅合成”描述指请求/夹具素材，不能证明启动导入没有读取案例源码。依赖拆分与启动审核尚未解除本分支暂停。
>
> **不得打开或加入真实案件、种子正文、录音、图片资料或凭据；普通 git clone 不证明仓库已净化。** 不运行全仓或此前暂停节点、拒写探测，不绕过浏览器沙箱或权限限制。正式媒体归档恢复不开放。

本指南针对 `candidate/media-demo-launcher`，供同事核对已有机器草稿、原图和音频修订流程。它不是正式产品部署，也不是已完成的浏览器验收。

**仅使用脚本生成的合成材料。禁止真实案件、录音、凭据及正式数据库。** 默认生成示意PDF/PNG、虚构OCR草稿、1秒440Hz测试音和明确标注的虚构音频草稿，不执行OCR/ASR，不代表真实识别或人工听校。页图与PDF页码关系是声明，非自动验证。模型运行时固定关闭，正式媒体归档/恢复仍不支持。

## 当前交接：限定纯前端独立复核

父线程最新确认以下六项限定独验均通过。本次仅据该结论更新文档，未重新运行测试。每行属于不同固定提交的纯 Node 合成 DOM/Promise 范围，**不可累计，也不代表当前头全量通过**；不代替真实浏览器、HTTP、模型、原件或生产身份验收。

| 固定提交 | 限定范围与记录 |
|---|---|
| [25fc8e7](https://github.com/mark2wen2023/MCIS/commit/25fc8e78b4d877bd060cfa889a9c66a15632ca50) | 音频播放迟到提示；[开发命令与边界](https://github.com/mark2wen2023/MCIS/blob/25fc8e78b4d877bd060cfa889a9c66a15632ca50/tests_acceptance/audio-playback-late-status/DEVELOPER.md) |
| [9bc2f3d](https://github.com/mark2wen2023/MCIS/commit/9bc2f3d95db37798cebd0d334d83673e432102ce) | 两片段播放串行、不排队；[记录](https://github.com/mark2wen2023/MCIS/blob/9bc2f3d95db37798cebd0d334d83673e432102ce/tests_acceptance/audio-playback-serialization/DEVELOPER.md) |
| [d1f2593](https://github.com/mark2wen2023/MCIS/commit/d1f2593f98364bc54ee12ec02f8a3b1ccfdd0327) | 输入事件、dirty及模拟离页处理；[记录](https://github.com/mark2wen2023/MCIS/blob/d1f2593f98364bc54ee12ec02f8a3b1ccfdd0327/tests_acceptance/audio-draft-lifecycle/DEVELOPER.md) |
| [baabeed](https://github.com/mark2wen2023/MCIS/commit/baabeed48bf59c322f77dfdc91ed262500843ab8) | 音频运行来源声明、缺失未知；[记录](https://github.com/mark2wen2023/MCIS/blob/baabeed48bf59c322f77dfdc91ed262500843ab8/tests_acceptance/audio-source-declaration/DEVELOPER.md) |
| [4ec789e](https://github.com/mark2wen2023/MCIS/commit/4ec789e288dffad7284944ea9e1b9206e4c6f042) | 音频已载入与目标运行提示、保留草稿；[记录](https://github.com/mark2wen2023/MCIS/blob/4ec789e288dffad7284944ea9e1b9206e4c6f042/tests_acceptance/audio-loaded-context/DEVELOPER.md) |
| [53e59ca](https://github.com/mark2wen2023/MCIS/commit/53e59cac17542975eb697770cb3ac5c7345af129) | 图片来源、草稿、下载归属提示；[记录](https://github.com/mark2wen2023/MCIS/blob/53e59cac17542975eb697770cb3ac5c7345af129/tests_acceptance/image-loaded-context/DEVELOPER.md) |

链接的 DEVELOPER 文件保留当时开发执行记录及当时待独验状态，不能冒充独立报告；此表补充后来收到的独验结论，不追加未提供的计数。来源声明不证明真实性或与笔录匹配；模拟提示不证明原生离页弹窗、实际声音、解码或下载。历史网页/服务测试不得因这些前端结果自动恢复执行。

## 1. 新检出与依赖

在获准访问该仓库的机器上，用正常Git认证检出；不要把令牌写入命令或文件：

```bash
git clone --single-branch --branch candidate/media-demo-launcher https://github.com/mark2wen2023/MCIS.git MCIS-media-demo
cd MCIS-media-demo
git rev-parse HEAD
git status --short
# 固定本指南已核对的完整提交；不要以可移动分支名代替版本记录。
git switch --detach 53e59cac17542975eb697770cb3ac5c7345af129
git rev-parse HEAD
```

应确认最后输出严格等于 `53e59cac17542975eb697770cb3ac5c7345af129`，且工作树干净；不符或有本地修改时停止核查，不强制覆盖。此为当前交接的产品固定版本，包含下列来源与上下文提示修复；不代表整个版本完成全量验收。本次后续文档提交不改变运行时代码。旧 `69e6145c7c62540a128083c85235df882ca3f4de` 的准备/服务记录保留在§6，不能证明当前头，也不构成重跑许可。

原指南固定的 `03a76a54dc178727585d859d7bd8db98a14b78c7` 及更早验证仍作为§6历史证据保留，不能将其测试数计入新头全量验收。分支以后可能前移，不能把可移动分支头当作这里的精确被测版本。

以下命令面向 Linux/macOS 的 Bash，在仓库根目录执行。Windows流程未验证。需要 Python（本次复核使用3.12.14）、venv及 `service/requirements.txt` 中的服务依赖。此演示不需要前端npm构建、.NET SDK、PaddleOCR、SenseVoice或模型下载。

**历史命令，当前不执行。** 以下仅保留原环境创建与依赖安装步骤，不是安装许可：

```bash
python3 -m venv service/.venv
service/.venv/bin/python -m pip install -r service/requirements.txt
```

**本轮未执行上述安装命令。** requirements使用版本下限而非锁文件，不能保证重新安装得到已验版本；网络、安装或权限失败时停止，不更换来源绕过。已有合适虚拟环境可直接选用，不必重新安装。

**历史命令，当前不执行。** 以下仅保留原解释器、源码路径设置及依赖导入检查：

```bash
set -e
export MCIS_DEMO_PY="$PWD/service/.venv/bin/python"
# 若使用已有获准虚拟环境，只将上行替换为它的实际python路径。
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH=.:service
"$MCIS_DEMO_PY" -c 'import sys, fastapi, uvicorn, sqlalchemy, httpx, reportlab; print(sys.version.split()[0]); print("dependency imports OK")'
```

依赖导入检查仅初筛，完整准备步骤还会使用其他仓库依赖。缺件就停止，不把导入检查称完整环境验收。

## 2. 全新合成材料与明确清单（暂停执行）

以下为原准备命令留档，当前暂停，不执行：

```bash
MCIS_DEMO_PARENT=$(mktemp -d "${TMPDIR:-/tmp}/mcis-demo-parent.XXXXXX")
"$MCIS_DEMO_PY" -m tools.media_review_demo.prepare --parent "$MCIS_DEMO_PARENT" > "$MCIS_DEMO_PARENT/preparation.json"
MCIS_DEMO_ROOT=$("$MCIS_DEMO_PY" -c 'import json,sys; print(json.load(open(sys.argv[1]))["dataDir"])' "$MCIS_DEMO_PARENT/preparation.json")
MCIS_DEMO_MANIFEST="$MCIS_DEMO_ROOT/demo-manifest.json"
printf 'root=%s\nmanifest=%s\n' "$MCIS_DEMO_ROOT" "$MCIS_DEMO_MANIFEST"
"$MCIS_DEMO_PY" -m tools.media_review_demo.launch --root "$MCIS_DEMO_ROOT" --manifest "$MCIS_DEMO_MANIFEST"
```

准备器在新父目录内另建 `mcis-media-demo-*`，使用其中的 `demo.db`，`seed_demo=False`。它通过现有接口登记六项合成材料，保存一个图片运行、一个音频运行，不复用默认数据库。`preparation.json` 是本次输出副本；启动器必须使用真正的 `demo-manifest.json`，不要互换。

预检成功会打印 `caseId`、`imageRunId`、`audioRunId` 与两个页面URL。保存本次实际输出；不要照抄别人的运行ID。换终端后，重新设置解释器/PYTHONPATH，并把根目录和manifest变量设置为自己刚生成的路径。

预检核对清单和登记关联，不证明原件字节当前完整、用户身份可信或页面能使用。失败、403、结果未知或 `incomplete-do-not-retry-in-place` 时停止并保留目录，不修改清单为prepared、不就地重试、不盲删。临时目录不是备份，系统清理后不能保证继续查看。

## 3. 仅本机启动和停止（暂停执行）

以下为原启动命令留档，当前暂停，不执行。未来获准时仍须确认8766端口未被其他服务占用，不杀未知进程或对外监听：

```bash
"$MCIS_DEMO_PY" -m tools.media_review_demo.launch --root "$MCIS_DEMO_ROOT" --manifest "$MCIS_DEMO_MANIFEST" --serve
```

**`--serve` 不是只读预检。** `checked_app` 先结束 `check_manifest` 的只读数据库连接，再调用隔离工厂；工厂调用 `create_app`，其中 `Database.create_all()` 可创建缺失表及触发器等数据库模式元数据，并创建所需目录。关闭种子和模型不等于禁止这些写入。代码依据：[启动器](../tools/media_review_demo/launch.py)、[演示工厂](../service/mcis_service/media_review_demo.py)、[应用初始化](../service/mcis_service/main.py)及[数据库初始化](../service/mcis_service/db.py)。

**预检到启动并非同一原子操作，也不保证文件在这段时间不变。** 只使用自己控制的新临时目录及其中数据库；不要使用共享、他人可修改、正式或需要保全的目录，不要在预检与启动之间改动清单/文件或让其他进程并行写入。无法确认目录归属与使用状态时停止，不能以预检通过替代一致性保证。

等待 `Application startup complete` 和 `Uvicorn running on http://127.0.0.1:8766`。启动器固定单worker、关闭reload、模型和种子；没有允许开启模型的参数。不要用README主产品的 `run_dev.sh` 替代本启动器。

正常结束时在启动终端按 **Ctrl+C**，等待 `Application shutdown complete` 和 `Finished server process`。不需要删除数据；未知状态不要自动清理或重启。不要暴露端口、配置公网转发或关闭浏览器沙箱。

以下普通HTTP入口检查亦暂停，仅保留历史命令（不代表浏览器验收）：

```bash
"$MCIS_DEMO_PY" - <<'PY'
from urllib.request import urlopen
for path in ('/image-review-lab', '/audio-review-lab'):
    with urlopen('http://127.0.0.1:8766' + path, timeout=5) as response:
        print(path, response.status, response.headers.get_content_type())
PY
```

另一终端须先设置自己的 `MCIS_DEMO_PY`。入口200只说明HTML返回，不证明脚本、授权下载、回听或修订成功。

## 4. 页面核对步骤（暂停，待启动隔离及正常浏览器验收）

在与服务同一机器的正常受支持浏览器打开：

- `http://127.0.0.1:8766/image-review-lab`：填写输出的案件ID和图片运行ID，点击“读取”；使用“授权载入页图”查看示意图，选择文字框，核对并追加一条明确标记为合成的人工修订，再读取确认历史保留。
- `http://127.0.0.1:8766/audio-review-lab`：填写案件ID和音频运行ID，读取并授权载入原音；预期为测试音而非语音。核对一条合成修订并重读。未知时间/说话人保持未知，不把草稿改写成真实事故陈述。

不要点击启动本地OCR/ASR；模型未配置。不要将接口测试的人工修订称为真人已听校。页面的完整交互、声音输出和修订回显本轮均未验证。

## 5. 身份、权限和停止条件

当前工程使用未认证的本地角色机制：没有角色头时按既有规则取 Investigator。准备脚本不再发送 LeadInvestigator；其操作者文字只是合成标签，不是身份凭证。**这不是可信登录、SSO或生产授权方案。** 页面和准备器仍经过原接口权限检查；没有更改权限矩阵、依赖覆盖或赋予新增权限。

任何403、授权障碍、未知结果或工具安全阻拦都应停止记录，不注入角色头、改案件策略、换工具或关闭沙箱继续。本指南不授权重试此前暂停的测试、写入拒绝探测或受限操作。不要运行全仓测试以“验证演示”。

## 6. 本指南的核验范围

**以下近期实跑均为开发方记录，不是独立复验。** 同事对指南、参数和远端提交的只读复核，不等于独立重跑服务、浏览器或模型。

### 历史 69e6145 的准备及回环启动验证（不代表当前头）

2026-11-18，精确头 `69e6145c7c62540a128083c85235df882ca3f4de`，全新本地Git工作树、全新自有临时父目录；**复用已有获准虚拟环境，不是全新安装验收，也没有重新从网络clone**。本指南§2的准备器和预检命令、§3的`--serve`参数实际执行成功。准备器、启动器、隔离工厂和requirements相对原指南固定头没有差异；主要后续变动在页面和验证材料。

| 本轮步骤 | 开发方实际结果 |
|---|---|
| 现有依赖 | Python 3.12.14；FastAPI 0.162.7、Uvicorn 0.54.0、SQLAlchemy 2.1.8、Pydantic 2.14.3、httpx 0.28.1、ReportLab 5.1.0；未安装软件或下载模型 |
| 合成准备 | prepared，六项登记材料及图音运行；模型未执行、归档关闭 |
| 明确root/manifest预检 | 成功；sourceBytesVerified=false、browserVerified=false仍保留 |
| 启动 | 固定127.0.0.1:8766，取得Application startup complete日志 |
| 真实TCP GET | 两个页面200 text/html；本次图音运行读取均200 application/json，案件及revision=0匹配；无角色头 |
| 停止 | 验证脚本仅向自己创建并持有句柄的服务进程发送SIGINT；wait取得退出码0并回收，日志含Application shutdown complete及Finished server process |
| 未验 | 没有真实终端按键Ctrl+C操作、浏览器、播放声音、页面点击保存、模型、原件下载字节复核或崩溃恢复 |

停止验证使用与正常Ctrl+C相同的SIGINT信号，但不等同于验证所有终端环境的按键行为。不要据此终止未知进程。服务已停止，未留下运行服务或对外监听。本轮只有现有Starlette/httpx弃用警告，没有调整依赖。没有运行pytest、暂停节点或写入拒绝探测；本轮GET不与此前TestClient/DOM替身测试相加。

上述结论仅是旧头 69e6145 的历史开发记录，不能用于当前头或解除暂停。未来须先解决启动隔离并获准执行，再在正常受支持且保留沙箱的浏览器环境验收§4；不能称完整演示闭环、干净安装或生产验收。

### 更早回环验证（历史版本，不代表当前头）

2026-11-18，基于精确运行时代码 `e3b913ff6585650cbe91a5998a65cc3522ef46a8` 创建全新独立Git工作树，复用已有服务虚拟环境，未安装依赖或模型：

| 步骤 | 上述回环服务验证的实际结果 |
|---|---|
| 新源码检出 | 本地Git worktree检出成功；未重做网络clone |
| Python依赖导入 | Python3.12.14，所列导入成功；非全新安装验收 |
| 全新合成准备 | 成功，prepared；不开模型、不使用真实材料 |
| root/manifest预检 | 成功，仍明确sourceBytesVerified=false |
| 回环服务 | 127.0.0.1:8766启动成功 |
| 两个HTML入口 | 不附加角色头，均200 text/html |
| 停止 | 终端Ctrl+C未确认退出；补发SIGINT后进程为defunct（已退出待父进程回收），未取得完整关闭日志 |
| 浏览器/回听/人工审核 | 未执行；不能称演示闭环 |

准备和启动出现已有Starlette/httpx弃用警告，命令仍成功；本轮没有安装替代库或修改依赖。此前Chromium尝试因环境SUID沙箱配置错误中止，本轮未重试、未修权限或关闭沙箱。须由环境管理方提供受支持且保留沙箱的浏览器环境后再验收。

上述回环服务验证没有运行pytest；更早新增普通合成接口测试1项通过属于先前开发证据，不与下面的新回归计数相加。历史说明参见 [移除高权限头记录](../research/media_demo_no_role_header/RESULT.md) 和 [此前演示尝试](../research/media_demo_no_role_header/DEMO-ATTEMPT.md)。


### 后续定向合成回归（开发方，2026-11-18）

精确被测版本：`1450bb2829a6c2ca0db9b83861c16aa8201ed0a2`。随后 `03a76a54dc178727585d859d7bd8db98a14b78c7` 仅保存[命令与验证记录](../tests_acceptance/media-demo-current/DEVELOPER-VERIFICATION.md)，未改运行时。静态审阅节点及其fixture/helper后，以下三个指定节点实际 **3 passed in 2.06s**，无失败/跳过：

- `test_media_demo_no_role_header.py::test_synthetic_prepare_and_readback_without_role_header`
- `test_media_demo_launch.py::test_prepared_manifest_metadata_and_disabled_app`
- `test_media_review_demo.py::test_same_app_edits_audit_and_reopen_preserve_both_histories`

这些文件位于 `service/tests/`。仅覆盖合成准备、不附加角色头的接口读取及下载摘要头、显式清单预检、模型关闭、同应用图音修订/审计以及重新构造应用后重读；原始机器草稿保留。使用临时库和TestClient进程内ASGI调用，**不是浏览器、实际网络服务重跑或真人回听**，也不是进程崩溃恢复、全套原件字节完整性或独立验收。

该回归未运行同文件其他节点、导出拒绝、写入拒绝探测、暂停测试、真实资料或模型，未重新启动服务/浏览器。本次指南同步仅只读核对代码差异和已有结果，没有再跑测试。干净安装、完整客户端联动、真实浏览器显示/声音/人工审核及正式媒体归档恢复的缺项均保持；旧头69e6145的SIGINT关闭历史证据见上节，不追溯改写本历史结果。
