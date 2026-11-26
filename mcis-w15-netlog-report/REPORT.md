# MCIS W15 Chrome 原生 NetLog 诊断（候选 d4391cd）

- 执行时间：2026-11-26 11:50–11:55（北京时间，UTC+8）。Grok Bot 的 Linux 盒子。
- 基准：`cc98de9ac4888c684651a6eb9d397b0161164022`。独立候选分支 `candidate/w15-chrome-native-netlog` 提交 `d4391cda418aa284df27d8b86066d9d3b81c0566`（2026-11-26 11:52:23 +0800）。相对基准只给原 Chrome 启动参数增加 `--log-net-log=<私有临时文件> --net-log-max-size-mb=10 --net-log-duration=60`，并更新诊断 SHA 针为 `434aa9e76c99ca5902a5e8b1a868b29423fc7ea4517d3d4a7048fa15fefc8ff3`（与本候选 `run.py` 字节一致）。另在 DIAGNOSIS.md 公开说明最小差异。未改 pins.json、host.py、产品源或原断言。
- 按同一 DIAGNOSIS.md 原流程跑一次。新的未用过证据目录；外层 `timeout --signal=TERM --kill-after=10s 150s`。正常沙箱（`chromium_sandbox=True`，无 `--no-sandbox`）。仅 127.0.0.1 回环。只跑一笔合成预览 POST，未补发第二笔，未替换响应，未手发信号。
- 本诊断不是产品变化，不算整体验收，不把诊断计作通过。
- Chrome：Google Chrome **156.0.8078.47**。现成 Python Playwright 1.65.2。未安装，未走外网。
- 原始 NetLog 仅存在本机私有临时目录（权限 0700/0600），**未打包、未上传、未入 Git**。公开材料只有筛选后的状态、事件/错误码、退出码和候选 SHA，不含 URL、请求头、正文或账号材料。采集为 Chrome 默认脱敏级别。

## 1. 退出码

| 步骤 | 退出码 |
| --- | --- |
| 有界诊断（`timeout` 150s + `diagnose.py`） | **124**（GNU timeout：150 秒到点发 SIGTERM；不是断言通过） |

无 `receipt.json`，无三张原截图。原 gate **未**完整退出 0。官方 TRACE 最后停在 `app_ui:195` 的 `result.json()`，与此前 CDP 取证一致。

## 2. NetLog 筛选结果（按文件自身来源链，唯一 URL_REQUEST）

原始文件可完整解析为 JSON（2277 条事件）。按路径与方法在文件内部匹配到 **1** 个预览 POST 的 `URL_REQUEST` 来源，关联唯一。因此对**该来源本身**（不含可能复用套接字的更宽依赖链）读取状态与错误码：

- HTTP 响应状态：**503**（该 URL_REQUEST 来源上唯一；`HTTP_TRANSACTION_READ_RESPONSE_HEADERS` 亦为唯一 503）
- 该 URL_REQUEST 来源上的 `net_error`：**net::OK**
- `REQUEST_ALIVE`：有 BEGIN 与 END；END 事件上**没有** `net_error` 字段，故该字段为 **未验**，不强行推论
- 已出现：`HTTP_TRANSACTION_READ_RESPONSE_HEADERS`、`HTTP_TRANSACTION_READ_BODY` BEGIN/END、`URL_REQUEST_JOB_FILTERED_BYTES_READ`、`REQUEST_ALIVE` END

曾对含复用套接字的更宽来源依赖链做过试探，该链上 HTTP 状态不唯一，故**不据此推论**。

## 3. 未验

原 gate 完整通过；把诊断计作验收通过；`REQUEST_ALIVE` END 上的 `net_error` 字段；浏览器/CDP 正文指纹核对；alert / 切案 / 390 重启；HTTP-only；真 .NET。未改产品，未合并，未部署，未触发远程 CI。
