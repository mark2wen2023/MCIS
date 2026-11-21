# 深蓝试用入口源码差异收据（不是构建输入）

本目录只供本机 A/B 验收前**源码审核**，不构造包、不导入应用、不启用任何入口。退出 0 只表示下列固定 Git 字节和比较结果匹配，不表示依赖闭包、隔离、授权或可运行。

- 审核产品：`0a7c09aaf25218337852bc55a075a400acb3402e`（深蓝 + 询问文字稿）。
- 祖先：`e9db012c478fbee5f72c283f593b4f781778043c` → `15dd614` 回选 → `6b3854e` 深蓝 → `145b163` 音频导入 API → `0a7c09a` 独立文字面板。已用 Git 祖先关系核对。
- e9db012 的旧 `tools/pilot_image_build/inputs.json` 实际冻结的是 **`3a615bf6d449c90eb0a64d25c20c5cdc83fdd06c`**，58 文件；不是 e9db012 全树，更不是新版入口。该 JSON 在新版原字节不变。
- 本次只增加本审核目录，不改任何旧冻结、builder、输入 manifest 或镜像允许表。本目录没有 `files/commit/format` 构建 manifest；**不能转换/改名为 builder 输入或拿去批准镜像**。

## 可复跑只读命令

在包含本目录的独立候选检出根目录，用已有 Python 标准库与 Git：

```sh
python docs/zhihai-source-review/check.py --source-only --repo . --source-ref 0a7c09aaf25218337852bc55a075a400acb3402e
python docs/zhihai-source-review/test_check.py
```

需要上述三个固定提交的本地 Git 对象。缺对象、浅克隆缺祖先、partial clone、误用 main/别的 ref、文件集合/散列不符都拒绝；不会 fetch、checkout、安装、构建或调用 Docker。若缺对象请停止并由使用者另行取得固定源码，不把退出非零改成通过。脚本仅读取 `review.tsv` 与列明的 Git blob，不扫描工作树/材料目录；因此**不审核未提交工作树改动**。没有输出包或可执行配置。

`review.tsv` 的列包括路径、旧冻结比较、旧 SHA256、e9db012 SHA256、新固定头 SHA256/字节数/Git blob、入口或依赖用途。`-` 表示该审核来源无此路径。`additional-review` 是旧58清单外新增审核，不一定是新创建的产品文件。脚本绑定 TSV 自身摘要及旧 inputs 摘要，不能增加未知路径而继续通过。

本轮实跑：审核退出 **0**，`55 unchanged / 3 changed / 7 additional-review`；5 组纯自造字节/假 Git 元数据检查退出 **0**。三项变化为 factory.py、pages.py、workbench.html。其余新增审核包括音频 app/package、两个新界面/样式文件、三份既存音频合同工具；所有 Python 仅 AST.parse，没有执行模块。

## 明确入口和静态证据（行号均属 0a7c09a）

| 路径/符号 | 静态事实与边界 |
|---|---|
| `local_review_pilot/factory.py:41–77` | `create_local_review_pilot` 默认关闭；image/audio 两开关显式检查，audio 默认 false；读 workbench.html，交 pages 注入服务器能力。不是默认 main。 |
| 同文件 `:103–142` | 回执路由共用；登记需额外开关；图片/音频分别有限挂载，核对最终路由集合后初始化核心及媒体表。源码顺序不等于实际运行验收。 |
| `local_review_pilot/pages.py:1–18` | 顶层引用 `_review_page` 和 `workbench_skin.CSS/image_shell`；后者不在旧58冻结。 |
| `pages.py:_mount_pilot_audio_page` | 读取 audio_workbench.html，注入同一皮肤，挂 `/pilot/audio-review`。不复用含播放器的旧 audio review.html。 |
| `audio_review/app.py:11–12` | 顶层 v2/v3 合同工具导入，另有共同 contract.py。三工具为已有纯校验源码，不是模型执行。 |
| `audio_review/app.py:74–88,225+` | imported-only 在 check 前拒任务来源；有限挂载四条导入/列表/详情/修订 API，不含 source-context/播放/任务。普通完整模式仍含动态 tasks 和 main 分支，不能称该模块所有路径已隔离。 |
| `common/local_review_pilot.py:103–111` | 安装可信会话验证器；未配置装拒绝。仍须在真实装配验证 Depends override 生效，不能拿 common/context.py 的旧角色头默认值当登录。 |
| `tools/pilot_image_acceptance/host_adapter.py:35–44` | 旧宿主只启 image_imports，期待图片表；未启音频、不期待音频表。不能把这份旧宿主当深蓝询问 A/B 自动验收器。 |
| `tools/pilot_image_acceptance/browser_steps.py` | `save_reopen` 是同浏览器、同服务会话里的 `page.reload()`，**不是进程停止重启**，也不是恢复验收。后续 A/B 是两授权案正常切换。 |

表中路径除 tools 外均相对 `service/mcis_service/`。TSV 每项列出继承用途/直接引用；它不是所有本地或第三方传递导入的清单。

## 明确未纳入/未证明

- 不读取 `main`、任何 seed 正文、任务实现、模型、媒体、案件资料或凭据。未递归追踪未知导入。音频模块中 `check` 的 tasks 分支、完整 register 的 tasks 导入和 create_audio_review_app 的 main 导入仍存在；本次仅记录已读调用点，不验证被省略源码。
- 未纳入播放/下载、音频旧实验页、模型任务、报告生成/导出/绑定、归档写入；reports/access、归档 history 等旧守门依赖仍列在58项中，不能因“未纳入业务”而删守门。
- 不声称包初始化/动态导入、配置、合同根或所有外部依赖已闭合。未解析外部 FastAPI/SQLAlchemy 等实际安装物，未验证 ABI/浏览器/TLS/沙箱/平台/镜像来源或摘要；旧外部输入仍未审定。
- 尚缺**新版**独立隔离装配/外部输入复核与实际 A/B 验收：合法登记、首个零运行、图/音首次导入、修订、同会话刷新、正常切案。询问功能不能沿用旧图片 `save_reopen` 的结论。权限不对称、并发冲突、迟到响应、原件及进程重启均需另列门槛。
- 本次未运行应用、HTTP、浏览器、数据库/ORM、媒体/模型、容器或4A；未新增任何启动许可。下一步是审核者审此65项与明确缺口，再决定新版运行输入/宿主方案，不能直接把收据送入旧 builder。
