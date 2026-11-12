# 航迹历史回执隔离：独立验收

## 裁定与计数

本冻结范围通过。独立 TRACKHISTORY 48 项 + 原 W19.2 OpenAPI 路径一致性 1 项，共 **49 passed / 31.75 秒**；另外重跑已发布知识归档独立 70 项，**70 passed**。真实浏览器通过，另有明确模拟的两类409 UI检查。最终冻结33文件SHA前后匹配，未修改实现。开发方370项不计入独立结果。

## 原缺陷与修复验证

已在旧发布服务独立新空库重现：恢复合成W10包后原digest GET、船舶列表GET、原actor同body POST commit均200/replayed:true。保留原始私有复现/日志，不发布环境路径。新1.3三库往返后这些入口及旧source/report、通用evidence原件入口均409 ARCHIVE_HISTORY_ONLY，不返回活跃回执、不改变DB/blob。

旧reader兼容不是仅代码推断：早期1.0包仅改版本1.3实验有原包成功对照；最终又将**实际新导出的1.3完整包**交给未修改的已发布旧服务，generic、restricted preview、restricted commit均422且全表/blob不变。只证明这个已核旧服务，不代表Unity/任意第三方。

## 已独立执行的矩阵

- 全部合成、seed_demo=False，HTTP创建案件/船舶/明确UTC CSV；三空库恢复与重导出，逐字节比较CSV/report/track文件、原审计/保管链前缀和完整track-intake索引。目标无track_local_receipts。
- 旧版本1.0/1.1/1.2降级 × 三入口拒绝且零副作用；无W10的基本1.0包在generic及restricted仍正常。
- 真正运行旧服务生成旧本地DB、generic恢复DB、含报告的旧1.2 restricted恢复DB，然后用新服务create_all升级。旧回执来源统一未验，不是从新库删标记冒充升级。可严格导出1.3再空库恢复历史CSV；保存旧source.mcase原字节。
- 实际HFACS CLI保存 + W10 + 报告同包三库组合，HFACS文档/归档完整，旧HFACS请求409，报告正文一致，W10仍历史隔离。
- 原船新内容TRACK_EXISTS、不覆盖；新船新输入成功且本地同body可重放。两个真正spawn进程共享SQLite/blob，Event同步同输入竞争得到一次新提交和一次重放；不同输入竞争得到200/409，只有一份marker和2点、审计链有效。
- marker插入、restore索引插入、文件rename、最终commit故障回滚全部表/文件，随后重试成功。历史读取commit故障无返回原字节、无Access残留。
- local及archive孤立证据删除后两个ID不复用，旧digest仍拒绝、坏状态不导出；源CSV/report损坏拒绝且无Access副作用。
- 全12类别当前Deny下新history列表、详情、两个原件及未知digest均403。旧无proof且ais/evidence允许、testimony拒绝时五旧入口先403，不泄露ORIGIN状态；原先权限排序疑点经实测不成立。
- 重算manifest之后的缺index、改actor/digest、重复index、改source path/pointCount、缺custody原链均拒绝，无恢复副作用。
- 受控导出/commit交错：真实导出锁内read后Event暂停，commit确认到达共享锁acquire再放行；旧导出是无W10完整1.0，随后commit成功，新导出完整1.3，无死锁。不用sleep猜序，不是任意生产多worker承诺。

## 浏览器实际范围

新增真实旧服务1.2恢复库升级浏览器：实际UNSUPPORTED提示出现时报告正文仍显示；篡改source.mcase后仅显示完整性/通用核验错误，不显示兼容提示；恢复字节后挂起真实provenance请求，在正文已加载时通过真实API撤销audit权限，放行请求收到403，父正文清空。原包恢复前后字节一致，页面无JS错误。该流程无API doubles。

真实服务由纯合成HTTP源库导出后恢复到目标库，Vite/Chromium访问真实target：旧列表返回历史拒绝但无保存成功标识；独立历史列表、CSV和report下载内容精确校验；切角色清除历史显示。

随后仅对新船的保存请求分别显式模拟 ARCHIVE_HISTORY_ONLY 与 TRACK_ORIGIN_UNVERIFIED 两种409（预览仍真实），验证UI保持未知写锁、不能把历史当保存成功。这两项是受控响应UI检查，不宣称后端真的发起了那两次保存。真实HTTP拒绝已由API矩阵独立验证。

## 明确兼容限制及未覆盖

- 旧1.2受限恢复库升级后：报告正文仍200，严格再导出1.3及新目标历史读取成功；但原库report provenance需解析旧source.mcase，其旧W10顶层版本已不支持，因此返回精确409 ARCHIVE_HISTORY_UNSUPPORTED，UI说明旧来源版本暂不支持而保留当前报告正文。本片没有自动迁移旧provenance读取，不能声称所有旧历史功能已恢复或旧包已完整校验有效。原包保全，不伪造null。真实原包字节损坏仍409 ARCHIVE_HISTORY_INTEGRITY；非对应迁移reason的422也仍为INTEGRITY，不能由兼容码吞掉。
- 旧真正本地无proof同样不再声称活跃回执；不得据此认定旧保存失败或诱导重复提交。普通原件访问仍按既有权限，不冒称新全权限历史接口。
- proof只表明本地升级后提交路径，不是认证；导入永不携带活跃权限，数据库管理员仍可伪造自报身份/状态。
- 未穷举所有恶意字段、容量阈值、所有并发调度、symlink/所有OS崩溃点。新1.3预算机制未单独做64MiB实际材料超限测试；已有原归档预算验收不冒称本次新测。未新增跨case专门攻击、所有UI迟响应/损坏下载组合。
- 无真实事故资料、外部模型调用、部署或核心算法变更。不是整个项目完成或全repo回归。

## 验收脚本调整

最终补修记录：上一冻结中旧W10来源版本拒绝被包装为INTEGRITY，属于容易误导为损坏的错误分类。开发方窄修仅识别精确迁移reason为UNSUPPORTED，独立原断言按已批准合同更新，并新增真实损坏/其它422不能吞掉的回归；新33文件全部复跑通过。无最终新增产品阻断项。浏览器初稿使用不存在的#/tracks路由、过严label精确匹配及同URL导航应重置面板的错误假设，分别改为真实#/track、标签选择和显式reload；保留本地失败日志，不归类产品缺陷。Python Playwright使用已有系统环境，服务用仓库venv，不安装依赖。

## 复现

```sh
MCIS_OLD_ROOT="$UNCHANGED_D44_ROOT" MCIS_DOTNET="$DOTNET_BIN" DOTNET_CLI_HOME="$SDK_HOME" PYTHONPATH=service service/.venv/bin/pytest -q tests_acceptance/TRACKHISTORY/test_roundtrip.py tests_acceptance/TRACKHISTORY/test_guards.py service/tests/test_knowledge_w192.py::test_route_contract_without_real_seeds
MCIS_BROWSER_BIN="$CHROMIUM_BIN" python tests_acceptance/TRACKHISTORY/browser_real.py
MCIS_OLD_ROOT="$UNCHANGED_D44_ROOT" MCIS_BROWSER_BIN="$CHROMIUM_BIN" python tests_acceptance/TRACKHISTORY/browser_provenance.py
sha256sum -c tests_acceptance/TRACKHISTORY/verified-impl-sha256.txt
```

旧服务路径必须指向未修改的已发布d44实现。legacy_fixture/old_reader_probe在隔离子进程使用该代码，只创建临时合成库。浏览器仅loopback临时服务，退出清理自身进程。
