# 内部同案双份 V1 原件核验（待独验，未接线）

基线：f9f4e599cdb670d864a5e7e986067216e7105636。不合并 pilot 分支，不改旧冻结或共享契约。

`evidence_intake.router._read_original_for_access` 是原下载事务内部逻辑的原序提取。原 download 仍保留先授权、请求 purpose/operator 校验、WRITE_LOCK、begin、同一 session、Response；AST 展开对照整个 router 完全等价。

`trajectory_exchange.registered_pair._read_registered_pair` 未注册路由、未导出包 API、无默认调用者。服务器调用方必须提供已验证主体与个案/操作上下文、固定的服务器选定 pins、已经校验的 purpose/operator，并负责异常时回滚整个事务。普通 Ctx、浏览器声明或该函数通过均不证明认证。每份原件都重新走原授权、登记/摘要完整性检查、容器保护及 Access 审计；然后核对固定 case/evidence/requestDigest/sourceSha256，运行现有 V1 校验器。两船全部有效才返回 tuple，不返回半份、yield 或修改回放状态。

锁定的是已登记不可变原文字节及登记摘要，不是当前航迹版本计数。相同案不同船才可用；时间未核实拒绝整组，缺轨/未知 HDG 保留。没有 CSV→V1 转换或 latest 回退。失败前第一份可能已向调用方 session 追加 Access：必须整体回滚，不能捕获异常后继续提交。仅传同一 session 不证明数据库一致快照、撤权竞态或磁盘文件稳定性。

复验（已有 Python/jsonschema，无安装）：

```sh
python tests_acceptance/registered-trajectory-pair/check.py
```

9 组：整个 router AST 展开等价、两船及缺轨/缺 HDG原样、跨案 pin、合成读取拒绝、合成授权/容器失败顺序、错误摘要/回执、坏契约/同船、原文错案、新记录不替代旧 pin。执行 AST 提取的真实函数，手写 authorize/load_receipt/container/audit；真实 V1 纯校验器读取现有固定 Schema 和合成夹具。未导入 router、FastAPI 或 ORM。

未验证：实际身份、权限、load_receipt 的数据库/文件执行、事务回滚/持久审计、浏览器、HTTP、回放接入和报告。下一步必须在可信装配点证明授权上下文和一致读取/回滚边界，再考虑调用；不提供启动许可。
