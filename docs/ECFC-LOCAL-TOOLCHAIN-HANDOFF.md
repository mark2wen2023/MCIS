# ECFC 单案合成试点：本机工具链交接

本候选仅增加本文，不启用产品。固定产品源码为 `d9187fef1f979866ac4d8ce2064d1ac92f34bb36`；已有登记/选择工装为 `9fff9bc416c300422c6b1e378c4b3d682e6ceb45`，后者的图是测试上下文，不能冒充正式保存图。本文件不提供安装器，也不自动访问网络。

## 1. 准备普通本机环境

在现有 MCIS 克隆中 fetch 本候选后，以其准确提交创建独立 worktree；不要切换或覆盖正在使用的工作树。以下操作仅在新 worktree 根执行。已有 Bash、Python 3、正常可用的 .NET SDK 8.0.428 是前提。Apple Silicon 必须使用原生 Darwin arm64 终端与 osx-arm64 SDK，不混用 Rosetta/x64；Linux 以下只覆盖 glibc，musl 不适用。

SDK 由同事依本机政策另行准备到专用目录；不全局安装，不改变系统安全设置。仅使用微软 HTTPS：

- 清单：<https://builds.dotnet.microsoft.com/dotnet/checksums/8.0.34-sha.txt>
- 归档前缀：`https://builds.dotnet.microsoft.com/dotnet/Sdk/8.0.428/`

下列值来自该官方清单；下载后须同时匹配清单条目和完整归档 SHA-512，再解包。Mac 可用 `shasum -a 512`，Linux 可用 `sha512sum`。下载/验证失败即停止，不换镜像、协议或版本。

| 平台 | 归档文件 | SHA-512 |
|---|---|---|
| Apple Silicon | dotnet-sdk-8.0.428-osx-arm64.tar.gz | `c2930ce6363417165142e5610992df1430b1cf93f4b5ac31027da611a6bc089a73e7062eed0200be3e4a32db893a92c86fc27816a53521e5b041aafba0aa1215` |
| Linux x64 glibc | dotnet-sdk-8.0.428-linux-x64.tar.gz | `33212bb99a2bf003973d41106c7e8fe94208a12958ff601d4a476be379403c85a7dc9183a6ec64dfb44ded7102965be09f35add1758e68e9251bae7891d7b7bf` |
| Linux arm64 glibc | dotnet-sdk-8.0.428-linux-arm64.tar.gz | `bcc10091e404baaec01d538be8bd7125a33a8338594a6a795b1036128ace747a450d3f1482f16210b6a7ee937b911488676109156ec2c905ce31030badb1b0f2` |

## 2. 最短检查到真实 CLI 冒烟

把第一行改为已核 SDK 的绝对路径，整段在 Bash 中执行。不安装依赖，不启动 App/HTTP/浏览器，不读数据库。`nuget locals` 只列目录，不清缓存。目录输出可能含用户名，转交结果时不附原路径。

```bash
export MCIS_DOTNET=/absolute/task-sdk/dotnet
set -euo pipefail
test -x "$MCIS_DOTNET"
git diff --exit-code d9187fef1f979866ac4d8ce2064d1ac92f34bb36 -- tools/mcis-ecfc unity/Assets/_Project/Scripts
test "$("$MCIS_DOTNET" --version)" = 8.0.428
export DOTNET_CLI_TELEMETRY_OPTOUT=1 DOTNET_NOLOGO=1
"$MCIS_DOTNET" nuget locals all --list
ECFC_TASK_DIR=$(mktemp -d)
export ECFC_TASK_DIR
mkdir "$ECFC_TASK_DIR/empty-feed"
export RestoreSources="$ECFC_TASK_DIR/empty-feed" NuGetAudit=false
printf '%s' '{"action":"validate","draft":{"scope":"Synthetic local smoke","nodes":[],"edges":[]}}' |
  tools/mcis-ecfc/mcis-ecfc.sh > "$ECFC_TASK_DIR/smoke.json"
python3 - <<'PY'
import hashlib, json, os
from pathlib import Path
root = Path.cwd()
result = json.loads((Path(os.environ['ECFC_TASK_DIR']) / 'smoke.json').read_text())
assert result['ok'] is True
assert result['result']['coreVersion'] == 'mcis-ecfc-draft/1'
assert result['result']['nodes'] == [] and result['result']['edges'] == []
out = root / 'tools/mcis-ecfc/out'
manifest = json.loads((out / 'build-manifest.json').read_text())
assert manifest['sdk'] == '8.0.428'
assert manifest['contract'] == 'mcis-ecfc-build/1'
assert hashlib.sha256((root / 'tools/mcis-ecfc/build.py').read_bytes()).hexdigest() == manifest['recipeSha256']
for path, digest in manifest['inputs'].items():
    assert hashlib.sha256((root / path).read_bytes()).hexdigest() == digest
assert manifest['artifacts']
for name, digest in manifest['artifacts'].items():
    assert hashlib.sha256((out / name).read_bytes()).hexdigest() == digest
print('PASS: actual empty synthetic CLI; SDK, source and artifact manifest match')
PY
```

原 launcher/build.py 未改；构建输出只落新 worktree 的忽略目录 `tools/mcis-ecfc/out`，临时 JSON 落本任务目录。项目无外部 PackageReference；空本地 feed 防止构建获取额外包，若缺包即停止。不要提交 SDK、构建产物、缓存或输出。结束后只清理自己创建的任务目录和独立 worktree，不对用户既有目录执行递归清理。

任何 mutex、签名、平台或权限错误均停止；不造 first-use 哨兵、不提权、不关闭 sandbox。`--version` 成功不代表 NuGet 初始化、编译或核心成功。

## 3. 正式预览／保存／重开：下一门，尚无本次可执行整合入口

上述成功后仍不能称单边试点通过。当前 `tests_acceptance/ECFCNEW/test_integrity.py` 导入 `main.create_app` 并使用 TestClient；它不是本次允许的无应用、无种子直接调用入口，**不要直接运行整套 ECFCNEW**。也不要把 9fff9bc 的内存图手写进业务表。

下一步需单独审查一个临时 SQLite 直接调用工装，沿现有正式函数执行：

1. 全新临时库和原件目录，明确合成 case/policy/身份；不读取本机默认库。正式登记固定 communication.txt 后取得真实回执，不能插造证据或回执行。
2. `ecfc_drafts/router.py:377 preview_sync` → `:282 save_sync` → `:327 get_draft`；核心由原 `run_core` 调用。使用默认策略原本允许的明示合成 LeadInvestigator，不修改策略；保留普通 Investigator 拒绝。保存前需明确现有归档限制。
3. 核对保存、独立 DB session 重开后的同案 revision/digest/边 ID/端点、EcfcAuditRow 和 EcfcRequestRow。图仅 Draft/ToBeVerified，不是事实。
4. 获准服务端单条关联准备完成后，再测明确打开调用原 `_read_original_for_access`，成功提交恰好一次 Access；无关系零读取、撤销/换版/无权限不交付，读取后 pin 失败不得谎称未物理读取。

目前缺的是该受审工装与正式保存图到单条原件关联的实现，不是允许用客户端 pin 替代。T+100 仅游标，T+109 是通联原文时刻；不提供 Seek、时间顺序或因果结论。不保存报告、不导出、不改归档或生产身份。

## 已验与交回内容

云执行器 Linux x64/glibc 2.41：官方归档与 SHA-512 验证成功，SDK `--version` 为 8.0.428；原 launcher 构建初始化报 `NuGet-Migrations` mutex IOException，退出1。没有 DLL/manifest、没有核心/正式保存验收。Apple Silicon/Linux arm64 未实测。本文 shell/Python 仅做语法及固定哈希文字核对，不算执行本机步骤。

同事交回：固定 Git SHA、OS/arch/libc、SDK版本及归档校验结果、`nuget locals` 退出码、CLI退出码及上述 PASS 是否出现、manifest 摘要。失败只交不含本机用户名/路径的首个错误类别。正式数据库与单边验收未运行须单列，不能用工具链成功替代。
