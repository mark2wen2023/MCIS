# 同事交接：代码评审候选、内部引用与静态预览

2026-11-19；仅供代码审查，不是生产版本、部署许可或启动许可。本次仅补充两条前端候选的远端与源码核对，不重复功能测试。前次 b5ed49a 文档交付已在新建普通源码检验目录复跑下文三条获准离线检查；两次均未运行应用、后端或浏览器。远端头在整理时核对如下；分支可移动，复核必须固定完整 SHA，不把后续头当作同一被测版本。普通 clone 不证明仓库资料净化；不得打开或加入真实案件、种子正文、媒体或凭据。

## 固定版本及关系

| 分支 | 固定头 | 含义 |
|---|---|---|
| integration/ui-review-series | `749eaff1af3f0cf1ddc12c0f84ff6ca2c916b451` | 可拉取做代码评审；在已独验 3edb1a55 上新增报告动作同步防重复，新增修复已获限定独验，边界见下文。 |
| candidate/case-workspace-flow | `a8ff69efce06fa869d8893823b8f211d6a96d97b` | 基于 749eaff 的七阶段导航与报告显式选案守门；无有效报告案号时全局侧栏入口仍保留原路径。不是下列三 PR 组合。 |
| integration/pr99-pr100-pr101-browser-pending | `78516e800bd00a94fddf4ecd796f46699dde3618` | 独验记录头；固定功能头 `242b814bc44ba1c27d1226f9ee673abbb4a25a47`，#99/#100/#101 只读提示组合，仍待浏览器验收。 |
| candidate/media-demo-launcher | `76d6c22c474172a28f7b2da9ae45021e8d573b82` | 隔离图音复核、来源声明、草稿和异步反馈；正式媒体归档恢复未开放。 |
| candidate/media-report-exact-reference | `3a19c75221dc770042708972bf7a1a36d681e121` | 基于图音头的内部精确修订投影/读取器及逐项证据派生；未接报告生成、展示、导出或重开，只供内部代码评审。 |
| candidate/audio-reference-range | `da8cda69bfb421177c702587c45426a2cc5ce5e1` | 内部精确旧录音范围、生成 RA 句子解析及合成组合验收；包含空目录预检 `7a2d0e4ab8d96b1b4a72da2e03563908989897d0`，未接真实报告链。 |
| candidate/synthetic-audio-review-scenario | `c10b2cd787f4b70d404893be9b9bfeb4f7de4361` | 独立合成素材与固定非人声 WAV 生成器；不是登记、转写或报告产品功能。 |
| candidate/audio-blank-range | `191fd1ea3c36ac9c3d3458a41fe24c004357956a` | 音频页回听及保存前共用 times() 拒绝纯空白，保留两个空串为未知、显式 0 有效；未验证真实保存或播放器。 |
| candidate/ui-offline-report-preview | `0bdbf26fde52b2908e7b8881ddc5ebe978c9f146` | 文档头；预览构建固定 `87dfd2584294893319751e29ec240ca7d7e54c81`，不是完整应用。 |
| research/source-declaration-comparison | `2e9593657cf1ab1dafbf7ee815d9ef0a06f9bd8d` | 另行独立的纯函数研究，未接入上述 UI、图音、离线预览或任何页面、服务。 |

UI 与图音两头互不包含，彼此均非祖先，共同基线为 `94d5e38c926fda232bb987b60fa9145e4bcf01a7`；尚未组合，不能将两者证据当作组合验证。内部引用 3a19c75 继承图音 76d6c22，但图音分支未包含此增量，也未与综合 UI 组合。离线预览继承 3edb1a55，不含 UI 后续 749eaff 防重复修复；综合 UI 亦未纳入预览增量；图音、来源比较及启动隔离候选也未混入综合 UI。本交接文档分支仍基于历史 UI 文档头，仅记录当前版本，不代表已合入当前 UI 修复或其他候选。UI 明确不含 `be1c887421ecc06a77330a1f118808562af20ae4`。

音频新增三条候选**不是一个已集成版本**：da8cda6 继承内部引用 3a19c75，但没有合入 191fd1e 的页面修复或 c10b2cd 的素材分支；其 WAV 测试只读取固定生成器 Git 对象，不代表产品整合。各候选也不自动纳入综合 UI。不要把独立测试结果拼成已可运行的录音→报告闭环。

## 两条前端候选不能混用验收结论

- **工作台 a8ff69e**：`web/src/caseFlow/model.ts` 定义接报、取证、询问、分析、报告、建议、沉淀七阶段；仅按当前显式案号与路由导航，完成状态未评估，沉淀仍为后续入口。`Layout.tsx` 的报告路径在缺失、空白或重复案号时不挂载报告 Outlet、不开始新案件元数据读取；ReportPage 也保持显式选案守门，不回退默认案号。侧栏只对按案入口引导选案，知识库等真正全局入口仍按原路径、不携案号。有效明确案号仍保留既有报告与历史链接语义；不是案号存在或访问权证明。
- 该精确头实际包含 #99 的 `web/src/interview/SourceDisclosure.tsx`（InterviewView 调用）和 #101 的 `web/src/environment/OriginGuidance.tsx`（EnvironmentPage 调用），但树中**没有** `web/src/caseMetadata/GapSummary.tsx`。不能因已有 #99/#101 组件，就声称工作台包含或验证了 #100。本轮只核对固定源码，不重跑这些功能。
- 工作台的既有限定证据是实际组件 SSR/路由纯逻辑，以及受控无网 hooks harness 的无效案号 no-read/no-Outlet、有效→无效→另一案、全局侧栏路径和旧元数据迟到抑制；相邻回归与 TypeScript/Vite 结果见[导航记录](https://github.com/mark2wen2023/MCIS/blob/a8ff69efce06fa869d8893823b8f211d6a96d97b/tests_acceptance/case-workspace-flow/REVIEW.md)和[报告选案及侧栏修正记录](https://github.com/mark2wen2023/MCIS/blob/a8ff69efce06fa869d8893823b8f211d6a96d97b/tests_acceptance/case-workspace-flow/REPORT-EXPLICIT-CASE.md)。它们不证明真实 React reconciliation/并发、浏览器点击、视觉、HTTP 或权限；本轮没有重新执行。
- **三 PR 组合 78516e8**：功能仍是 242b814；246c116 仅补开发记录，78516e8 仅补[限定独立复核记录](https://github.com/mark2wen2023/MCIS/blob/78516e800bd00a94fddf4ecd796f46699dde3618/tests_acceptance/pr99-pr100-pr101-combined/INDEPENDENT-VERIFICATION.md)。六项合成 SSR/纯逻辑及 TS/Vite 的独验只属于该固定功能版本，不能转移给工作台或累计成全量验收。
- **#100 的清单只在本次这条三 PR 组合中验**：`GapSummary` 展示已保存的名称、海域、首席调查员、调查机构、概要五项文字填写情况，不统计未保存草稿、不判断事实或全案完整，不是工作台的功能覆盖，也不是工作台试用的前置门槛。严格解析器对异常快照的整页错误和 helper 的逐字段结果分层，见组合独验记录；不能将直接 helper 调用当正常页面路径。

原 `integration/ui-review-series` 的 749eaff 继续作为独立固定候选保留，不以工作台或三 PR 组合替换。两条新增表项不是同一个版本，未将其产品修改合并到本交接分支；也不改变图音/内部引用/静态预览之间的独立关系。无新增试用或启动许可，DO NOT MERGE / 不部署。

## 前次离线交接复验与浅克隆入口

- da8cda6：前次 b5ed49a 文档交付在新建 Git 目录通过下列双分支 depth=1 fetch、完整 SHA 比对和白名单源码展开，复跑占位组合、实际生成 WAV 组合及目录预检。均是**开发方交接复验**，不是本轮新增独立验收，不累计历史计数。30ac3e8 的生成快照解析此前已获限定独验；不能将其结论扩为真实报告绑定。
- 7a2d0e4：仅检查显式空目录与固定样例/成员路径，输出未来数据库和素材位置。startupAllowed/isolationVerified 始终 false，不建库、不证明沙箱、不批准启动；本轮复跑普通输入校验，不运行权限或拒写探测。
- c10b2cd：本轮仅使用固定对象中的生成器；源码 SHA-256 为 `d5a9285e64898077888f92615082e33278fd405ddabadad4e339a82fcec0cd23`。生成 WAV 摘要为 `48e65e6aa7493adecacf16a5a2bd09e0966303658ec2bf6c980cc239fb4c266f`，头部为 8000Hz、单声道、16-bit、96000帧。生成输出自动清理，不提交二进制。实际字节只替代夹具中原音摘要/时基；机器产物、登记、人工修订及句级关联仍是手造声明。
- 191fd1e：固定[开发记录](https://github.com/mark2wen2023/MCIS/blob/191fd1ea3c36ac9c3d3458a41fe24c004357956a/tests_acceptance/audio-blank-range/DEVELOPER.md)记载 15 个纯解析、11 个合成 DOM、8 个等待场景的同轮结果。本轮不重跑该分支，不把它称为实际 Save、HTTP 或回听验收。

以下为**源码检查命令，不是启动命令**。需已有 Python 3、jsonschema、Git（/usr/bin/git，支持 GIT_NO_LAZY_FETCH）及正常获准的 GitHub 访问；本轮复用现成依赖，未验证全新安装。在新临时目录初始化 Git，不整仓 checkout，不执行其它脚本。Git 获取对象仍不等于资料净化或物理隔离，禁止打开对象中的原案/种子/媒体；这里只展开明列的非案例源码。遇网络/权限阻碍停止，不换渠道。

普通组合 check.py 不需要 c10b2cd 对象；**实际 WAV check_wav.py 必须具有该固定对象**。浅克隆/单分支默认 fetch 未必包含它，因此显式获取两条分支。下面完整流程已实跑；任一远端 SHA 不同，`set -e` 会停止，应重新核查而非自动采用新头。浅 fetch 不保证取得历史 7a2d0e4，本流程不依赖该历史对象。

```sh
set -eu
review_root=$(mktemp -d /tmp/mcis-handoff-source-XXXXXX)
cd "$review_root"
git init -q
git remote add origin https://github.com/mark2wen2023/MCIS.git
git fetch --no-tags --depth=1 origin \
  refs/heads/candidate/audio-reference-range:refs/remotes/origin/candidate/audio-reference-range \
  refs/heads/candidate/synthetic-audio-review-scenario:refs/remotes/origin/candidate/synthetic-audio-review-scenario
reference_sha=da8cda69bfb421177c702587c45426a2cc5ce5e1
generator_sha=c10b2cd787f4b70d404893be9b9bfeb4f7de4361
test "$(git rev-parse refs/remotes/origin/candidate/audio-reference-range)" = "$reference_sha"
test "$(git rev-parse refs/remotes/origin/candidate/synthetic-audio-review-scenario)" = "$generator_sha"
git cat-file -e "$reference_sha^{commit}"
git cat-file -e "$generator_sha^{commit}"
git cat-file -e "$generator_sha:tests_acceptance/synthetic-audio-review/make_wav.py"
git restore --source="$reference_sha" --worktree -- \
  service/mcis_service/reports/generation_snapshot.py \
  service/mcis_service/reports/media_reference.py \
  service/mcis_service/reports/media_reference_reader.py \
  service/mcis_service/reports/audio_reference_range.py \
  contracts/schemas/report.schema.json \
  tests_acceptance/media-report-reference/check.py \
  tests_acceptance/audio-reference-range/check.py \
  tests_acceptance/report-generation-snapshot/check.py \
  tests_acceptance/report-audio-snapshot-combination/check.py \
  tests_acceptance/report-audio-snapshot-combination/check_wav.py \
  tools/report_audio_preflight/check.py \
  tests_acceptance/report-audio-preflight/check.py
python -B tests_acceptance/report-audio-snapshot-combination/check.py
python -B tests_acceptance/report-audio-snapshot-combination/check_wav.py
python -B tests_acceptance/report-audio-preflight/check.py
printf 'Source-only verification directory: %s\n' "$review_root"
```

上述提取的部分测试文件只被检查器按名称取出既有夹具/纯加载函数，**不要直接运行白名单中所有测试文件**。本轮未运行任何其它旧测试。实际生成的 WAV 处于另一个自动清理目录；末尾打印的源码检查目录保留，含 Git 对象，不是批准运行的应用包。相关固定说明：[组合与 WAV](https://github.com/mark2wen2023/MCIS/blob/da8cda69bfb421177c702587c45426a2cc5ce5e1/tests_acceptance/report-audio-snapshot-combination/README.md)、[空目录预检](https://github.com/mark2wen2023/MCIS/blob/7a2d0e4ab8d96b1b4a72da2e03563908989897d0/tests_acceptance/report-audio-preflight/README.md)、[合成素材](https://github.com/mark2wen2023/MCIS/blob/c10b2cd787f4b70d404893be9b9bfeb4f7de4361/tests_acceptance/synthetic-audio-review/README.md)。

离线通过仅证明手造旧句/旧摘要返回 1000–2500ms，新句返回 4000–5500ms，新版加入后旧结果仍保留，未知时间为 null；不是取回/回听原音或验证权限。真正待联调的是：服务器冻结报告句锚点的**持久可信绑定**、报告与媒体授权交集及同一读取视图；实际播放器应记录 seek 和暂停时刻，不可只听到提示就通过。该 8kHz 非人声 WAV 不适用要求 **16kHz 单声道 16-bit PCM** 的 SenseVoice 验收，后者另需获准语音，本轮不运行模型。文件内时间不等于事故时钟。启动、保存、归档与恢复限制均不解除。

## 已有证据，按版本解释

- **当前 UI 749eaff**：[固定增量记录](https://github.com/mark2wen2023/MCIS/blob/749eaff1af3f0cf1ddc12c0f84ff6ca2c916b451/tests_acceptance/report-action-single-flight/REVIEW.md)。父线程已完成该固定头限定独验：旧头反例明确为实际派发 2 对预期 1；新 3 场景、相邻 12 场景、两份 TypeScript 配置及 Vite 通过。GISIS 防重计数仅静态检查，未做浏览器、HTTP 或后端幂等验收。仅当前页面防重复，不是未知结果安全重试；本轮未重跑测试。
- **UI 已独验基线 3edb1a55**：父线程确认 24 个综合脚本、提交阶段专项 3 组及 TypeScript/Vite 已独验通过。三个修正的旧生命周期脚本在原头和候选均有完成标记，保留业务断言。见[固定记录](https://github.com/mark2wen2023/MCIS/tree/3edb1a55bc60fdaa13980e84597da2f357663231/tests_acceptance/ui-effect-harness)与[提交阶段专项](https://github.com/mark2wen2023/MCIS/tree/3edb1a55bc60fdaa13980e84597da2f357663231/tests_acceptance/ui-commit-phase)。记录中的“待独验”为当时状态，此处补充后来确认；本轮没有重跑。真实 React 并发、浏览器、视觉及当前组合后端未验，不将不同计数相加为全量覆盖。
- **历史 UI 661d73f / 49fc5b0**：`661d73ff62a981af5ed64751c606b8e5129d42c0` 为旧代码组合，`49fc5b06ebedd2229b028c12f810180c8aef4649` 为其文档后续头，不再是当前综合分支头。[历史记录](https://github.com/mark2wen2023/MCIS/blob/49fc5b06ebedd2229b028c12f810180c8aef4649/tests_acceptance/ui-review-series/DEVELOPER.md)保留，不能替代当前固定版本证据。
- **离线报告 87dfd25 / 0bdbf26**：`87dfd2584294893319751e29ec240ca7d7e54c81` 的三页已独立重建及静态检查通过；`0bdbf26fde52b2908e7b8881ddc5ebe978c9f146` 仅补交接与 ZIP 校验。手造中文草稿、双语修改、英文缺失复用实际 ReportView；章节原文折叠区与合成 GISIS 快照已有输出检查。无页面脚本、业务请求或可操作业务控件；浏览器/视觉未验，不证明点击、保存、身份、HTTP 或生成报告。见[固定预览与制品说明](https://github.com/mark2wen2023/MCIS/blob/0bdbf26fde52b2908e7b8881ddc5ebe978c9f146/web/preview/report/README.md)，不构成后端启动许可。
- **图音**：已明确独验的六项固定版本为 25fc8e7（播放迟到）、9bc2f3d（串行不排队）、d1f2593（input/dirty/模拟离页）、baabeed（来源声明）、4ec789e（音频已载入/目标归属）、53e59ca（图片来源/草稿/下载归属）。均为纯 Node 合成 DOM/Promise 的限定范围，固定链接见[指南证据表](https://github.com/mark2wen2023/MCIS/blob/76d6c22c474172a28f7b2da9ae45021e8d573b82/docs/MEDIA-DEMO.md)。后续等待、保存反馈及 unknown 提醒变化不能据这六项推定独验。76d6c22 的累计提醒[记录](https://github.com/mark2wen2023/MCIS/blob/76d6c22c474172a28f7b2da9ae45021e8d573b82/tests_acceptance/media-unknown-guidance/ACCUMULATION.md)保留的是开发方执行记录；父线程随后确认 76d6c22 的 8 个新增及 2 个既有生命周期场景已获限定独验。不同固定版本的结果不能累计，此结论不是全量、真实浏览器或后端验收。
- **来源比较 2e95936**：父线程最新确认新增 7 组聚合与原 13 组纯函数分别独验通过；不累计为系统覆盖。要求同一案件、笔录及声明快照，保留逐 pair 结果；缺失/null、乱序、多角色、显式调用者 ABA 等为合成输入。没有网络、文件、数据库等服务访问或关联写入；Node 测试本身仍需加载测试/模块源码。声明一致不证明原件真实性、当前字节、人工批准、可信身份或服务端完整历史。见[固定说明](https://github.com/mark2wen2023/MCIS/blob/2e9593657cf1ab1dafbf7ee815d9ef0a06f9bd8d/research/source-declarations/README.md)。其中“待独验”属于提交时记录，此处补充后来确认，不冒充本轮重跑。

- **内部引用 3a19c75**：[固定记录](https://github.com/mark2wen2023/MCIS/blob/3a19c75221dc770042708972bf7a1a36d681e121/tests_acceptance/media-report-reference/REVIEW.md)。父线程确认各固定提交分别完成限定独验：3fd3112 的 3 组纯内存、c04dc2c 的 2 组查询桩、3a19c75 的 3 组 AST/桩，分别检查精确修订、内容摘要和逐项证据派生。不合计为全量覆盖；没有真实 ORM、授权、一致事务或报告闭环验收。本轮未重跑，固定记录中的待独验为当时状态。摘要区分人工正文与来源声明，不构成原件核验或存储防篡改。

不同提交、测试轮次与历史测试数不得相加为“全量通过”。旧 558/560、历史 HTTP/LibreOffice 或模型实验均不构成本候选的新验收或重跑许可。

## 尚不能生产的原因

1. 旧头报告页与建议页的 render 写 ref 已在 3edb1a55 纳入针对性修正：相关状态发布移到提交阶段，读取闭包不再经 render 写 ref 更新。不能再称旧问题未修，但合成生命周期仍不证明真实 React 中断/丢弃渲染、并发或浏览器行为。A→B→A、服务端版本/CAS、持久操作回执与多用户一致性仍未解决。
2. 图音来源只是运行记录的声明，页图/PDF 页码关系不是自动证明。unknown 提醒仅页面内累计，可能跨案件/运行、同记录合并多次不明提交，不是逐次操作回执；刷新、相同内容或后续成功均不能证明此前请求未提交，也不保证重试安全。
3. 真实浏览器、视觉/无障碍、原生离页提示、图音实际回听/解码/人工审核、当前组合完整 HTTP、可信生产身份、全新依赖安装、完整 CI、归档恢复均未完成验收。历史 LibreOfficeDev 不是 Word，也不是当前头视觉验收。开发构建存在既有大 chunk 提示。

## 当前暂停及后续门槛

**不得执行旧指南的 prepare、launch、应用初始化、TestClient 或归档测试。** `seed_demo=False` 仅跳过填充，当前图音启动路径仍顶层导入含案例常量的种子模块。历史“合成请求”不能证明启动未加载这些源码。依赖拆分候选及启动审核尚未解除上述暂停。综合 UI 的后端启动/归档验证同样不因前端合成通过而获准。

正式媒体归档/恢复继续关闭，现有防丢保护不得放宽。不得运行暂停节点、拒写/权限探测、模型或真实数据；不得绕过浏览器沙箱、权限或工具阻拦。本文件不提供可立即启动的命令，不修改权限，不允许合并或部署。

试用闭环的通关条件（尚未满足，不是执行许可）：

1. 先获得可核实、受支持的隔离运行环境与正常浏览器沙箱，只提供手造素材；不挂载原仓库资料/用户目录。健康候选 `170ce9095c815cb8999777a83749fef0b9fdb794` 仅有 wheel/安装文件静态核对，venv 不是沙箱，未证明可启动。
2. 证明报告权限与媒体完整来源访问的**授权交集**，并在调用方**同一一致读取视图**内取得精确修订、证据派生及所需来源核对；缺失、变化或未知不得回退 latest。现有报告权限不能直接替代媒体权限，内部读取器不授予权限。
3. 在单一已审组合及获准隔离环境，用合成图音完成核对→保存→精确引用→导出→重开，逐项核对同案、证据、运行、修订、人工内容摘要和源摘要；旧版、来源变化及未知结果保持明确，不静默替换。真实浏览器和后端需分别留证，报告文件导出不等于整案备份，正式归档恢复继续单独阻断。

本次交接完成后暂停工程开发，等待真实联调条件或下一次授权计划检查；不把这些分支称作一条可运行链。

## 启动隔离与来源策略候选补充（限定独验，不可启动）

整理时远端核对：

| 候选分支 | 完整固定提交 | 已获限定独验的范围 |
|---|---|---|
| fix/seed-annotation-lazy-compat | `2a6048f032b262318bd51c9a4e5b9da35b97e850` | 自造 namespace/loader 的惰性缓存、别名共享、映射覆盖和删除、未知/虚构 ID 查询不调用真实加载器；包装模块的 AST 静态检查。没有执行实际包装模块或种子。 |
| fix/instance-source-read-policy | `6d5069b9d320dcaddab28b95f8ed265bfc567b67` | 自造来源策略组合、禁用时零 callback、实例策略独立、读取故障区分、旧适配器形状；Settings 类 AST 提取后的旧位置参数构造及静态接线检查。没有真实路由、报告生成或启动验收。 |

父线程确认两项已完成限定独验；链接中的开发记录仍保留当时“待独验”状态，不是本次重新执行。分别参见[启动隔离记录](https://github.com/mark2wen2023/MCIS/blob/2a6048f032b262318bd51c9a4e5b9da35b97e850/tests_acceptance/seed-lazy-compat/REVIEW.md)及[来源策略记录](https://github.com/mark2wen2023/MCIS/blob/6d5069b9d320dcaddab28b95f8ed265bfc567b67/tests_acceptance/source-read-policy/REVIEW.md)。不累计各轮测试数，不扩大独验结论到实际模块或完整应用。

**祖先关系须准确解释：** 6d5069b 已继承 2a6048f；不是两条互不包含的代码链，也不应重复叠加。但它们尚未纳入本文件固定的综合 UI 749eaff 或图音 76d6c22 候选，更没有经过完整启动/请求验收。文档分支也未合入这些修复。不要自行把各分支的局部通过当成组合可运行证明。

**不得使用旧提交 8ec4421bb8db2a4078e2c9d4c0f3378a14e85bc6。** 该提交误删 LILY_MARY_BAND_EVIDENCE 并留下裸标识符，是模块加载的阻断性错误。f59c61a 已恢复定义，2a6048f 包含修复；早先辅助测试通过并未覆盖实际包装模块，也不能证明旧提交可用。另一个旧头 2b20981 的 Settings 位置参数错绑定已由 6d5069b 修正，需使用完整固定修正头。

**seed_demo 默认仍为 True。** 两个来源读取开关默认 False，只限制候选中的分析种子/公开报告摘录读取路径，不等于禁止演示填充、零种子读取或安全启动。新开关仅支持显式可信构造配置，无请求开启接口或环境变量解析；不得用它们替代权限检查。现有 load_seed 直接调用需策略参数，分析路由的直接 Python 调用需 Request，禁用时自定义 whatif 适配器会被跳过；兼容差异保留。已有报告读取代码未改，不代表已做真实回归。

剩余阻碍：完整导入闭包和第三方启动钩子、实际包装模块加载、启用种子的行为、反射/reload/并发、真实应用多实例及共享数据缓存/适配器影响、HTTP 与模板输出、COLREG 后过滤提示、旧客户端与实际权限均未完成验证。显式映射访问、COLREG Seed 注释等其他路径仍可能按需加载材料。本轮只补文档，不执行或授权任何后台启动、prepare、TestClient、报告生成或归档测试。**启动与归档暂停不解除，不合并、不部署。**
