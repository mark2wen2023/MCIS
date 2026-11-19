# 同事合成核对用例：时间歧义与旧引用

仅自造文本和离线正常路径检查，**不是已经跑过的同事试用或可运行服务**。没有录音、船名、人员或媒体；未执行识别、听取、保存、导出或浏览器操作。启动/归档暂停仍有效，不要打开仓库案例或 seed。普通 clone 不证明材料净化。

## 固定基础与运行入口

本分支从案件流程 UI a8ff69efce06fa869d8893823b8f211d6a96d97b 派生，只加本目录和进度记录；没有合入媒体产品代码，未操作 mcis-3d。
检查从本地 Git 对象读取固定提交 3a19c75221dc770042708972bf7a1a36d681e121 的 service/mcis_service/reports/media_reference.py 与 media_reference_reader.py。先逐文件核 SHA-256，再按已有纯模块验收方式解析唯一相对依赖；不导入 MCIS 包/main/ORM，也不调用默认证据读取器。对象缺失即停止，不自动联网。稳定工作目录、可信本地 Git/Python/标准库是前提；这不是沙箱。

在仓库根目录，只执行：

    python -B tests_acceptance/synthetic-audio-review/check.py

查看仅本文件自造的完整夹具：

    python -B tests_acceptance/synthetic-audio-review/make_fixture.py

无需安装依赖或模型。不运行全仓测试。无权和缺证只在 notExecuted 中记录，检查器不分派执行。

## 用例步骤与期望

1. 短录音脚本：“听到提示后，过了一会儿才记录。”仅文字，未录制、未运行 ASR。
2. 第一次核对保留时间歧义。构造 revision 0/1 保存行形状，startMs/endMs 为 null、timeStatus=unknown、说话人未知、hearingStatus=pending、factVerified=false。
3. 建立固定 revision 1 引用素材，供未来旧报告引用。
4. 独立手造参考卡 SYN-REF-1 说明“约三秒”；第二次仅修改说明文字，不把间隔推成原音起止，不称听取核验。expectedRevision=1、revision=2。
5. 第二次引用及人工内容摘要不同；再次按旧摘要读取 revision 1，仍返回第一次文本和摘要。只读取 0、1 和指定证据，没有 latest。
6. 无权期望：不泄露或导出内容，须真实授权交集验收。缺证期望：不能建立引用、不回退。两项均未执行，不能称权限/拒绝测试通过。

## 字段、依据和限制

沿用固定媒体代码的 case_id/run_id/revision/doc 行形状、machineDraft.source、segmentId 和完整人工修订字段。人工行对应 audio_review/app.py 的 revise 保存构造，仅静态读取源码，未导入应用。currentSha256、registeredSha256、stateDigest、artifactSha256 含义分别保留。

夹具是最小投影输入，不是完整上传请求或完整音频草稿合同，不可直接发给服务。source/artifact/state 摘要是明确手造占位内容的散列，不是音频、模型或真实台账摘要；draftBytesSha256 是夹具自己的规范 JSON 摘要。operator/role/utc 是合成保存形状，不是生产认证或真实审计。参考卡与 reason 的关系仅为用例说明，产品尚未持久化此关系。

已有媒体 check.py/check_reader.py 覆盖旧修订精确读取；本轮不重复执行它们的全套场景。新增价值是可读的两次核对素材、暂停期望与单一正常入口。内存读取器明确是测试输入；实际投影和精确读取代码来自上述固定源码，不是假服务。

本轮开发执行 check.py，一个正常合成场景通过；尚未独验，不累计为全量覆盖。没有运行无权、缺证、篡改、故障或其他暂停场景。

真实串接仍缺：调用点授权交集、同一一致读取视图、真实保存与审计回执、reports/sources 接入精确版本、报告导出重开固定第一次，以及浏览器/回听验收。当前 UI 与媒体内部候选不是已跑通链。本轮无启动指令、不改变恢复/权限/正式报告接口。

## 浅克隆或无 Git 对象的离线入口（本轮收尾）

前一提交 a9ef436 的独立复核确认复用固定源码，但复核环境缺少 3a19c75 对象，**没有实际运行通过**。本轮仅开发侧验证，不替代独验。

默认命令不变，缺对象仍停止。使用者也可预先从固定提交准备两份文件到自己控制的目录；不得用当前工作树的同名文件冒充固定源码。以下准备命令只适用于已经拥有该固定 Git 对象的原 MCIS checkout，不联网：

    source_dir=$(mktemp -d)
    git show 3a19c75221dc770042708972bf7a1a36d681e121:service/mcis_service/reports/media_reference.py > "$source_dir/media_reference.py"
    git show 3a19c75221dc770042708972bf7a1a36d681e121:service/mcis_service/reports/media_reference_reader.py > "$source_dir/media_reference_reader.py"
    python -B tests_acceptance/synthetic-audio-review/check.py --source-dir "$source_dir"

如果任何准备命令失败，停止；不要把空文件作为准备成功。浅克隆用户可由持有固定对象的同事提供这两份源码，放在独立目录后执行最后一条命令（替换 source_dir）。检查器不自动获取、不联网、不在便携模式退回 Git。

固定 SHA-256：

- media_reference.py：d6eb37ec028a1dd01607af3421ed375d8cf87c1f1a09099b95c59bc30f49e959
- media_reference_reader.py：717f87364d5a7205195a81d72b620a420b854599425cecbfd55f5aafdf459c50

两份文件都逐字节通过摘要检查后，才解析/执行已检查的内存字节；不在校验后重新打开源码执行。目录中其他文件不会作为产品模块加载。这不是文件系统隔离或可信 Python 环境证明。仓库不提交产品源码副本。

可把本目录 check.py 和 make_fixture.py 一起复制到无 Git 的临时目录，用绝对路径 --source-dir 指向上述两文件目录运行。本轮开发侧已在 TemporaryDirectory 中分别验证：默认入口（临时 cwd，脚本仍从原仓定位对象）；便携入口（复制两个用例脚本，无 .git/checkout）。两条均通过。临时目录自动清理，无二进制/源码副本入库。

新增直接断言 r2.revision=2、r2.humanText 等于第二次完整正文且不等于 r1；保留第一次内容、摘要、旧引用重读及精确 0→1→指定证据读取顺序。没有新增缺证/权限/故障测试，没有运行服务或后端。

## 同文字、不同文件内时间的正常样例

原有两次未知时间、不同文字的场景保持不变。新增 timed_fixture；可单独查看自造素材：

    python -B tests_acceptance/synthetic-audio-review/make_fixture.py --timed

check.py 的默认与 --source-dir 入口现在均执行两个正常场景。新增样例：同案、同证据、同运行、同片段，两次正文完全相同；revision 1 声明 1000–2500ms，revision 2 声明 4000–5500ms。手造时基 96000 帧 / 8000Hz = 12 秒。timeStatus=operator_declared、hearingStatus=transcription_checked 仅代表此合成行的操作者声明，不代表真的听过录音；factVerified=false、说话人未知。无实际音频字节。

字段依据：固定 reader 的 AUDIO 字段包含 startMs/endMs/timeStatus；audio_review/app.py 的 revise 保存构造使用 operator_declared。此处只运行纯读取器，不运行 app 或 Save。片段范围按手造帧数/采样率检查，不把“约三秒”等外部间隔推成原音位置。

直接断言早晚修订号、完全相同正文、精确查询顺序、不同引用摘要，以及追加 revision 2 后 revision 1 仍匹配原摘要。另有固定 revision=1 的纯内存控制输入，只替换 startMs/endMs，其他字段包括 utc/reason/expectedRevision 完全相同；新算人工修订摘要及引用摘要均不同。这才是时间字段输入敏感性的证据，而非只由修订号差异推断。没有调用摘要不匹配错误路径，没有修改存储、源文件或执行权限/故障测试。

重要限制：现有 projection.target 只返回 segmentId，projection 不返回 startMs/endMs。摘要包含时间不等于取回旧时间、更不等于定位或回听。下一验收项仍需真实调用点先满足既有授权交集和一致读取视图，再仅按旧修订取回旧片段范围；缺失/未知不自动定位，文件内相对毫秒与事故时刻必须分开。该项本轮未实现或运行。

本轮开发：原场景和新场景在默认本地 Git 对象路径通过；复制到无 Git 的临时目录、显式两份已核哈希源码路径也通过。未独验；不累计历史次数，不称真实报告导出重开、ORM、HTTP、媒体回听或端到端验收。

## 可带走听辨的非人声 PCM 素材（独立于引用绑定）

新增标准库生成器 make_wav.py。单声道、16-bit little-endian PCM、8000 Hz、96000 帧，精确 12 秒。整数周期方波，峰值 2048/32768，其他帧静音；无随机数、时钟、网络、语音或模型。不是上述合成文字的录音，不测试转写。

| 文件内位置（半开区间） | 内容 | 验收用途 |
| --- | --- | --- |
| 0.25–0.50 秒 | 200 Hz 低提示 | 两个引用范围之外的前提示 |
| 1.20–1.80 秒 | 400 Hz 提示 | 应落在第一次范围 1.00–2.50 秒内 |
| 4.20–4.80 秒 | 800 Hz 较高提示 | 应落在第二次范围 4.00–5.50 秒内 |
| 8.00–8.25 秒 | 200 Hz 低提示 | 两个引用范围之外的后提示 |

从仓库根目录，选择自己控制的现有父目录，并指定**尚不存在**的输出子目录：

    python -B tests_acceptance/synthetic-audio-review/make_wav.py --output-dir /your/temporary/parent/new-wav-output

将绝对路径替换为本机新目录。生成器不复用或覆盖目录，不自动重试；产生 synthetic-markers.wav 和 manifest.json。失败时检查并保留现状，另行人工处理，不盲重跑。不会自动打开播放器。不要把生成文件提交仓库。

离线字节检查：

    python -B tests_acceptance/synthetic-audio-review/check_wav.py

检查器在自动清理的全新临时子目录生成两次，验证完整 WAV 字节一致、帧数/声道/位宽/采样率、96000 个采样及静音、提示位置与现有手造范围匹配。不是解码后实际发声或浏览器回听。固定输出 WAV SHA-256：48e65e6aa7493adecacf16a5a2bd09e0966303658ec2bf6c980cc239fb4c266f。

本轮开发：上述离线检查通过，另在临时目录实际调用带 --output-dir 的 CLI，摘要一致。未独验，没有播放。

同事后续人工步骤（本轮未执行）：先核 manifest/摘要；用本机获准播放器低音量打开生成的 WAV，确认完整 12 秒的四处提示；人工选择 1.00–2.50 秒应仅听较低的内部提示，选择 4.00–5.50 秒应仅听较高的内部提示，不应包含界外提示。记录播放器、实际选择位置与观察，不把主观听辨当采样级定位证据；若工具不能精确选段，记录未验而非猜测通过。不要据此启动暂停的 MCIS 服务或浏览器流程。

关键：旧用例 source/artifact/state 摘要仍是占位声明，**不是新 WAV 的身份**。本轮不改它们、不登记媒体、不创建报告关联；新 manifest 摘要只描述生成文件。引用片段定位仍待按既有授权交集和精确修订接入，未知不自动定位，文件内时间不是事故时刻。禁止把本素材检查称为报告导出重开或真实页面回听验收。
