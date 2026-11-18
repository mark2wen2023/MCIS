# 合成图像／音频隔离演示指南

本指南针对 `candidate/media-demo-launcher`，供同事核对已有机器草稿、原图和音频修订流程。它不是正式产品部署，也不是已完成的浏览器验收。

**仅使用脚本生成的合成材料。禁止真实案件、录音、凭据及正式数据库。** 默认生成示意PDF/PNG、虚构OCR草稿、1秒440Hz测试音和明确标注的虚构音频草稿，不执行OCR/ASR，不代表真实识别或人工听校。页图与PDF页码关系是声明，非自动验证。模型运行时固定关闭，正式媒体归档/恢复仍不支持。

## 1. 新检出与依赖

在获准访问该仓库的机器上，用正常Git认证检出；不要把令牌写入命令或文件：

```bash
git clone --single-branch --branch candidate/media-demo-launcher https://github.com/mark2wen2023/MCIS.git MCIS-media-demo
cd MCIS-media-demo
git rev-parse HEAD
git status --short
```

以下命令面向 Linux/macOS 的 Bash，在仓库根目录执行。Windows流程未验证。需要 Python（本次复核使用3.12.14）、venv及 `service/requirements.txt` 中的服务依赖。此演示不需要前端npm构建、.NET SDK、PaddleOCR、SenseVoice或模型下载。

如没有已批准且满足要求的环境，可在正常允许的网络下按仓库既有流程创建环境：

```bash
python3 -m venv service/.venv
service/.venv/bin/python -m pip install -r service/requirements.txt
```

**本轮未执行上述安装命令。** requirements使用版本下限而非锁文件，不能保证重新安装得到已验版本；网络、安装或权限失败时停止，不更换来源绕过。已有合适虚拟环境可直接选用，不必重新安装。

在同一终端设置所选解释器及源码路径：

```bash
set -e
export MCIS_DEMO_PY="$PWD/service/.venv/bin/python"
# 若使用已有获准虚拟环境，只将上行替换为它的实际python路径。
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH=.:service
"$MCIS_DEMO_PY" -c 'import sys, fastapi, uvicorn, sqlalchemy, httpx, reportlab; print(sys.version.split()[0]); print("dependency imports OK")'
```

依赖导入检查仅初筛，完整准备步骤还会使用其他仓库依赖。缺件就停止，不把导入检查称完整环境验收。

## 2. 全新合成材料与明确清单

仍在同一终端、仓库根目录执行：

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

## 3. 仅本机启动和停止

确认8766端口未被其他服务占用；不要杀掉未知进程或改成对外监听。执行：

```bash
"$MCIS_DEMO_PY" -m tools.media_review_demo.launch --root "$MCIS_DEMO_ROOT" --manifest "$MCIS_DEMO_MANIFEST" --serve
```

等待 `Application startup complete` 和 `Uvicorn running on http://127.0.0.1:8766`。启动器固定单worker、关闭reload、模型和种子；没有允许开启模型的参数。不要用README主产品的 `run_dev.sh` 替代本启动器。

正常结束时在启动终端按 **Ctrl+C**，等待 `Application shutdown complete` 和 `Finished server process`。不需要删除数据；未知状态不要自动清理或重启。不要暴露端口、配置公网转发或关闭浏览器沙箱。

可在另一终端做普通HTTP入口检查（不代表浏览器验收）：

```bash
"$MCIS_DEMO_PY" - <<'PY'
from urllib.request import urlopen
for path in ('/image-review-lab', '/audio-review-lab'):
    with urlopen('http://127.0.0.1:8766' + path, timeout=5) as response:
        print(path, response.status, response.headers.get_content_type())
PY
```

另一终端须先设置自己的 `MCIS_DEMO_PY`。入口200只说明HTML返回，不证明脚本、授权下载、回听或修订成功。

## 4. 页面核对步骤（待正常浏览器环境验收）

在与服务同一机器的正常受支持浏览器打开：

- `http://127.0.0.1:8766/image-review-lab`：填写输出的案件ID和图片运行ID，点击“读取”；使用“授权载入页图”查看示意图，选择文字框，核对并追加一条明确标记为合成的人工修订，再读取确认历史保留。
- `http://127.0.0.1:8766/audio-review-lab`：填写案件ID和音频运行ID，读取并授权载入原音；预期为测试音而非语音。核对一条合成修订并重读。未知时间/说话人保持未知，不把草稿改写成真实事故陈述。

不要点击启动本地OCR/ASR；模型未配置。不要将接口测试的人工修订称为真人已听校。页面的完整交互、声音输出和修订回显本轮均未验证。

## 5. 身份、权限和停止条件

当前工程使用未认证的本地角色机制：没有角色头时按既有规则取 Investigator。准备脚本不再发送 LeadInvestigator；其操作者文字只是合成标签，不是身份凭证。**这不是可信登录、SSO或生产授权方案。** 页面和准备器仍经过原接口权限检查；没有更改权限矩阵、依赖覆盖或赋予新增权限。

任何403、授权障碍、未知结果或工具安全阻拦都应停止记录，不注入角色头、改案件策略、换工具或关闭沙箱继续。本指南不授权重试此前暂停的测试、写入拒绝探测或受限操作。不要运行全仓测试以“验证演示”。

## 6. 本指南的核验范围

2026-11-18，基于精确运行时代码 `e3b913ff6585650cbe91a5998a65cc3522ef46a8` 创建全新独立Git工作树，复用已有服务虚拟环境，未安装依赖或模型：

| 步骤 | 本轮实际结果 |
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

既有新增普通合成接口测试1项通过属于先前开发证据，不是本轮浏览器结果。本轮未运行pytest或暂停测试。说明参见 [移除高权限头记录](../research/media_demo_no_role_header/RESULT.md) 和 [此前演示尝试](../research/media_demo_no_role_header/DEMO-ATTEMPT.md)。
