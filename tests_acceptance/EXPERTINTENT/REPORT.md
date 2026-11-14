# EXPERTINTENT 独立验收

结果：16项独立Python用例通过（0.03秒），7个独立DOM场景通过（network=0），7/7冻结一致。证据results.txt、dom-results.txt、hashes.txt。

复跑：
```
PYTHONPATH=. /workspace/mcis-local-export/service/.venv/bin/pytest -q tests_acceptance/EXPERTINTENT/test_independent.py
node tests_acceptance/EXPERTINTENT/independent.mjs
```

独立检查：额外key/ready/executionAuthorized/proxy/endpoint/reviews/budget/caseId字段全部拒绝；BOM、非法UTF8、深嵌套与超限输入拒绝；普通与转义重复键拒绝；相同内容重复/换排版产生相同canonical摘要且始终blocked，五个授权/派发/身份/回执/预留标志false。CLI精确最多请求4097字节读取，合法和非法均exit2，没有成功执行出口。

DOM下载截获验证：同页重复及清空结果后仍同ID/同字节，仅4固定字段；重新mount产生新ID，不承诺服务端幂等。状态明确保存未确认、未执行。anchor创建及click抛错均脱敏失败；已分配Blob URL延迟1000ms逐一回收。缺crypto不生成Blob、显示失败；没有fetch请求。没有验证真实浏览器保存或落盘。

静态审查preflight仅标准库argparse/hashlib/json/re/sys，不导入Executor/transport、不访问环境、不持久化/预留；输出blocked并不是可执行票据。页面不携带当前意见、来源全文、密钥/URL或ready，UUID与摘要均无身份认证含义。未来服务必须独立授权与验证可信bootstrap，不可将本预检输出作为授权。

限制：DOM输入/错误为合成，无真实凭据/模型/API/配置变更。未联网复取文档引用的官方平台说明或状态；这些取自父协调者记录。原生浏览器已知沙箱启动阻塞未重试或绕过，下载/布局/CSP未验。真实执行、身份、持久预算/幂等、取消服务与可信intent回执关联仍未实现。仅本次离线准备接口范围无阻断，真实HOLD保持。
