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
