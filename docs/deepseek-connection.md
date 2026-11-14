# DeepSeek 接入：独立适配器与虚构笔录验证

本阶段新增独立远端 transport 和一次性验证 CLI；尚未接入生产案件或受保护工作台 host。原本机模型配置和 loopback 限制不变，不自动选用远端服务。

## 配置与凭据

- 服务端从受支持的密钥环境绑定读取 `DEEPSEEK_API_KEY`，不要在聊天、命令行参数、仓库、浏览器或日志中填入密钥。
- `DEEPSEEK_MODEL` 可为 `deepseek-v4-pro`（默认）或 `deepseek-flash`。
- 目的地固定 `https://api.deepseek.com/chat/completions`，不接受自定义 URL，不跟随重定向。
- 保留可信运行环境提供的 HTTPS proxy 和 CA，以支持托管网络凭据替换。运行环境及其配置属于信任边界，不能把不可信用户的代理设置传入宿主。
- 不自动重试，不下载模型，不启动监听服务，不上传附件，不使用模型工具调用。

## 显式虚构验证

在具有依赖的 service 环境下运行：

```sh
python -m mcis_service.agents.deepseek_probe
python -m mcis_service.agents.deepseek_probe --send-fictional
```

第一条完全不读取凭据、不请求网络。第二条仅使用代码内固定的虚构笔录；无凭据返回 `not_connected`。不支持指定案件、输入文件、标准输入或密钥参数。网络调用失败、格式不合格或引文不匹配均为 `unconfirmed`，不会伪造成功或返回固定提案。输出只有状态、数量及限制，不输出密钥、请求正文或模型原文。该 CLI 不代替案件授权验证。

## 数据和质量边界

提示构造复用强制脱敏；输出复用结构契约和逐字唯一引用检查。JSON 合法不代表事实正确，模型提案仍需调查员审核。JSON 模式可能返回纯空白，即使 `finish_reason=stop`，也必须拒绝。

该实现通过模拟 HTTP 合约测试不代表真实 API 已连通。真实连通必须另记录运行结果，不能将模拟输出、配置模型名或引文匹配描述为模型身份认证或专家准确率。

## 官方资料（2026-11-14 核对）

- https://api-docs.deepseek.com/
- https://api-docs.deepseek.com/api/create-chat-completion/
- https://api-docs.deepseek.com/guides/json_mode/

后续接入受保护工作台前须将远端发送授权与案件/笔录/策略绑定，并保留发送前及生成后的权限检查，禁止仅通过设置环境变量自动外发真实案件。
