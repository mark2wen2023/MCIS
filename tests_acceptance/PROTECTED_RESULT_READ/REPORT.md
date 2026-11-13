# 受保护的当前未审核结果读取：独立验收

结论：本次限定非生产只读切片未发现剩余阻断项。独立审查未修改产品，只新增 `service/tests/test_protected_result_read_independent.py` 19 项测试。

## 实际执行

`PYTHONPATH=protected-read/service mcis-work/service/.venv/bin/pytest -q protected-read/service/tests/test_protected_result_read_independent.py protected-read/service/tests/test_protected_result_read.py --disable-warnings`

最终 30 passed、零 skipped，17.11 秒，1 个既有 Starlette/httpx 弃用警告。包括 19 独立 + 11 主测试，不能与主测/总回归重复累计。初次独立执行 15 passed / 1 failed：测试错误假设空案件已存在 AccessPolicyRow；修正测试为显式创建策略后通过，非产品缺陷。

## 覆盖

- 当前同库会话与案件成员，无保存授权且全部内容 ReadOnly 时仍能读取，不能 POST 保存。
- 会话撤销/过期、主体禁用、成员禁用/缺失拒绝；HTTP 初检后撤销与来源读取期间到期拒绝。
- 具体来源内容策略 Deny 不被成员资格覆盖；不能把残留审计历史作为缺失的当前索引重新激活。
- 读取不执行计算、不增加结果或保存审计，不输出操作 ID、操作者或 session token；状态明确 unreviewed / not_assessed。
- 重复授权头、仅旧角色头、Cookie、Origin、非零 Content-Length、Transfer-Encoding 拒绝，合法 token 配伪造角色/操作者不改变身份。
- 未知异常固定错误响应、无内部路径/token 泄露、no-store。
- 主测试同时覆盖未知/跨案 ID、恢复包历史结果拒绝，以及路径/查询变体。

静态核查：读取先取得保留 SQLite 写事务证明和同库身份，再完整内容授权、校验审计链/当前索引/严格历史 schema、重新读取当前来源及代次，最后再次授权；capture 使用 write=False，现有保存默认 write=True 保持不变。历史 schema 的额外字段拒绝仍适用，未绕过验证直接返回数据库文档。读取释放事务前构建脱离 ORM 的响应；释放后的撤权不能召回已经决定发送的数据，此边界已写入产品说明。

## 范围与限制

真实 SQLite/API + ASGI 测试；本套计算夹具为模拟核心结果，不是本套实际 W2、真实网络 socket、浏览器、IdP、LLM 或生产验收。GET 借用当前案件成员资格作为只读能力，同时要求保守完整内容权限；并未新增对外 provisioning。默认入口仍关闭，旧应用如果另外暴露并不因此被保护。原件磁盘不可变性、生产认证、限流、UI、人工审核、正式时间线准入尚未由此完成。无合并、无部署。

## 产品冻结 SHA-256

- identity/local.py: 5ace9819f17dfcd5d16b85824eacd9f1e41a094870a0850ae35ef2fd39fce71d
- identity/http_trial.py: 53300c00b7caf3ec879c05dea266436cec5b87eb0d8b287d5a0bbe30af9f1f21
- timeline/unreviewed_storage.py: 78b80547ae4a9040b1468adc213db63c1233a4798b8a8caf72e766fe90b8b00d
- timeline/unreviewed_preflight.py: 07154269355bf65cb80894b2a720ecf71fbf73b2798f3385acd48c43ddaa9fb0
