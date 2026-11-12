# W20.1 本地文本提取运行说明

这是一个真实模型适配接口，不是把规则引擎重命名为智能体；当前只有人员/作业提取已实现。模型由操作者另行准备，本仓库不下载、不安装模型，也不保存任何密钥。

1. 在受控机器上自行启动可信的 OpenAI-compatible 推理服务器，监听 `127.0.0.1`，提供 `/v1/chat/completions`。
2. 启动 MCIS 服务前设置 `MCIS_AGENT_BASE_URL=http://127.0.0.1:8000/v1` 与 `MCIS_AGENT_MODEL=<实际模型名称>`。不配置时默认禁用。此版本不支持外部 API。
3. 先用虚构笔录测试。调查员明确调用 `POST /api/v1/cases/{caseId}/agents/people_ops/interviews/{recordId}:extract`。不可把生产资料拿来测试未经批准的模型服务。模型只能看到脱敏问答，不能调用工具。
4. `GET .../agents/drafts?status=PendingReview` 查看引用及 payload。必须检查逐字出处与解释，不要把引文相符当作结论正确。
5. 调查员 `POST .../agents/drafts/{draftId}/review`，`{"decision":"Confirmed","note":"逐条核验"}` 才追加陈述。Rejected 不写回；Modified 要提交完整 payload，仅允许调整解读。来源变化须重新生成。
6. 查审计中的 `agent.run.started`、`agent.run.failed`、`agent.draft`、`agent.review`。提示词与原始响应不写入审计，只记摘要、模型与状态。

配置状态 `configured` 只代表配置格式正确，不能证明本机有模型或模型可用。无需更改 API 密钥；本实现不支持密钥配置。没有提供 UI 按钮，本片为可调用的服务 API。

## 验证口径

- `service/tests/test_agents_w20.py` 的可控假模型验证草稿、引用、脱敏、权限、人工写回等逻辑。
- `test_real_http_protocol_fake_server_not_real_model` 真正经过本机 HTTP 和 OpenAI-compatible 协议，但对端仍是假服务，不是实际 LLM。
- 本轮没有实际模型进程可用，因此没有宣称完成真实模型推理、质量评估或六角色全部接通。
- 扫描件、照片、现场勘验图、CCTV、录音、视频、AIS 为后续多模态工作。当前不提供 OCR / ASR / 视频理解，也不伪造页码、图像区域或媒体时间码。现有 citation 的 evidenceId/page 扩展点保留，本次笔录引用使用 recordId/round + UTF-16 span。

原始材料是证据，模型输出是草稿；COLREG、工休与事故分级仍由确定性引擎负责。仅作安全调查技术分析，不作责任认定。
