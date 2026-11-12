# 全局知识归档独立验收

## 最终裁定

本次冻结范围通过：独立后端 **70 passed / 12.92 秒**；真实 Chromium + 两个空库服务的浏览器流程通过；新版独立身份迟响应 API-double 4 场景通过。冻结的 **21 个文件 SHA-256 执行前后全部匹配**，见 verified-impl-sha256.txt。未改业务代码，不以开发方自测数量替代独立结果。

## 实际覆盖

- 两个隔离数据库中创建全三类知识卡及 Candidate/Published/Rejected/Withdrawn 四状态，原卡、审计与完整快照导出。新 create/review 快照数量、原行哈希绑定与撤回前 Published 三项批准原值保留；旧历史保持 legacy-only，后续捕获从正确序号开始，不回填。
- 原始包保存与重复保存、详情、原包取回，逐字节一致；目标在线卡、审计、快照和 epoch 保持空，不激活历史 Published。源库不因导出/预览/保存改变。导入前预览无写入。
- 5 个非 Lead 角色 × 6 个入口权限拒绝，共30参数用例；错误输入不先泄露存在性，no-store，只有保存入口的预事务拒绝带 not-committed。
- 未知字段/版本、重复键、NaN、BOM、非法 Unicode、原链/卡摘要/快照/coverage/索引/审批不一致拒绝。实际 8 MiB+1 原始输入、卡1025、审计4097、快照4097、深度超32拒绝；超卡量导出在加载文档列前拒绝。
- 同主体同包并发保存恰好一个201、一个200；不同声明主体同包409 OWNER_MISMATCH、不返回前主体元数据、不带未提交标记。获授权 Lead 仍可单独读取，但读取不等于自己保存成功。
- 最终commit之前异常回滚；实际commit之后模拟响应阶段失败保持未知且可幂等重试。两个故障均500/no-store/无not-committed标记、不泄漏异常文本。快照/epoch插入故障回滚卡、原审计和marker。并发审核只有一次成功及一份快照。
- 受控 export/review 交错：导出在实际共享锁及事务内读完后用 Event 暂停；审核线程通过包裹原共享锁的观察器确实到达 acquire，未进入完成态；放行后导出仅含完整旧 Candidate/1条审计/1份快照，随后审核成功，下一导出含完整 Published/2条审计/2份快照，epoch及原链一致。无 sleep 猜序，不改变实际锁行为。
- 新三表 UPDATE/DELETE 被拒绝；存储原包、计数、角色损坏后详情/下载拒绝；未知在线卡表列拒绝导出。
- 1025 张合法旧卡及161字符旧操作人的独立场景：发布/撤回仍可成功，归档分别因容量/兼容性拒绝，未把归档上限强加在线撤回。
- 填充三种新global表不阻止正常案件工作记录包导出；增加未知非空case表后导出拒绝且无审计/数据副作用。

## 浏览器范围，严格区分两类

**真实双服务**：源端导出→目标文件预检→明确确认保存；通过真实服务先完成201提交，再将到达浏览器的响应替换为503以模拟成功响应丢失。UI保留未知锁，用户重新选择完全相同文件并明确重试，真实服务仍只有一份历史。验证在线公开卡为0、在线审计为空；历史正文及下载原包精确一致；刷新可重开；角色切换清正文。另修改发送请求的摘要头让真实服务预事务返回409 KNOWLEDGE_ARCHIVE_CHANGED及标记，UI解除锁。没有用假服务替代这些行为。

**独立 API doubles**：实际浏览器/Vite挂起preview/detail/download/save响应，在顶栏切换身份后释放。旧内容与下载不出现，迟到保存不报成功，同主体恢复后仍保留摘要未知锁。此项不证明后端行为，不混计入70后端测试。

## 边界及未覆盖

- 保存主体是自报role/operator，不是认证。攻击者能伪造头就可冒用声明；not-committed不是恶意代理防伪机制。
- 同SHA被另一主体保存时，本主体不能将其GET回执当自身成功；其未知锁可能继续保留，这是明确限制。系统提供同原包显式重试，不承诺凭404证明未提交。
- 旧Withdrawn覆盖丢失的批准信息不会恢复；新快照只向前捕获。本归档不是在线恢复、全系统备份、源网站备份或全部已导入历史集合备份。
- 全部仅合成数据，无外部来源抓取、真实事故材料、模型调用或部署。
- 未独立穷举每个列/每种快照篡改、所有分页边界及每个工程限额的刚好合法边界；不声称跨进程/生产多worker或任意崩溃容灾证明。实际并发覆盖同包保存、同卡审核及导出先持锁的受控审核交错，不是所有调度穷举。
- pytest一条框架弃用提示，不是失败。未声称整repo全部通过。

## 测试修正记录

本轮未发现需修改实施的新产品缺陷。新增跨模块测试初始误用不存在的POST出口导致404，改为真实GET案件export后通过。新版主体隔离测试初始只设置Lead角色、操作人仍为默认调查员；顶栏切回Lead改变了操作人，故旧锁正确隔离。修正测试为相同操作人后通过，未放松隔离断言。原始诊断日志保留本地、不发布。

PRE_REVIEW.md与UI_REVIEW.md属于开发中记录，不能代替本报告；其中旧“所有4xx永久保锁”已由最终协议明确拒绝白名单及同包重试更新。

## 复现

```sh
PYTHONPATH=service service/.venv/bin/pytest -q tests_acceptance/KNOWLEDGEARCHIVE/test_backend.py
MCIS_BROWSER_BIN="$CHROMIUM_BIN" python tests_acceptance/KNOWLEDGEARCHIVE/browser_real.py
MCIS_BROWSER_BIN="$CHROMIUM_BIN" python tests_acceptance/KNOWLEDGEARCHIVE/browser_identity.py
sha256sum -c tests_acceptance/KNOWLEDGEARCHIVE/verified-impl-sha256.txt
```

浏览器脚本仅loopback，临时数据退出即清理。跨模块测试复用仓库ARCHIVEB纯合成夹具，不复用开发方测试结论。
