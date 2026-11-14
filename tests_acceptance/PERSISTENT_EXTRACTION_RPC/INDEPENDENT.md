# 持久笔录工作复核RPC：独立验收

独立审查者仅添加 `service/tests/test_persistent_rpc_independent.py`，未修改产品。
最终独立24项＋主17项：41 passed，零跳过，27.24秒；一项既有Starlette/httpx弃用警告。首轮21项独立12.08秒全过；之前39项23.89秒、最终小修后40项25.09秒均通过，计数重叠，不累加。

```sh
PYTHONPATH=issue-journal/service mcis-work/service/.venv/bin/pytest -q \
 issue-journal/service/tests/test_persistent_rpc_independent.py \
 issue-journal/service/tests/test_persistent_extraction_rpc.py --disable-warnings
```

## 最后小修重验

实现者把写入worker开始后的ValueError统一分类为503 WORKING_RPC_UNCONFIRMED，避免提交后投影或预算错误暗示确定未保存；输入校验阶段仍409。主测试注入generate提交后的输出预算ValueError；独立新增review提交后的ValueError，验证503不含正文、数据库仅一条复核，原requestId/operationId/expectedRevision/decisions重试得到replayed且仍仅一条复核。最终41项包含两者，产品未由独立审查者修改。

## 实际验证

- 严格新profile和固定context/case/record，请求不可携带模型result、quote、provider、author、token、旧角色头或不适用字段。
- 同requestId改变operationId拒绝；相同请求重新检查host，不从缓存放回正文。
- 模拟生成已经提交后响应抛异常：503不泄露内部错误，同operationId重试只有一条WorkingProposal。
- 模拟复核已经提交后响应抛异常：原operationId、原expectedRevision、原decisions重试恢复一次复核；把expectedRevision擅自升级不能复用操作编号。
- 正常二次修订保留全部历史理由，旧expectedRevision不覆盖；原模型建议仍Draft、结果working_unreviewed/factActivated=false。
- 当前来源绑定变动导致生成重试、目录、读取都不返回正文；数据库原提案和历史仍保留，没有为隐藏而删除。
- 会话撤销拒绝已有请求重复、目录和读取；worker保存完成后、RPC返回前撤销也不回正文。
- 实际取消await响应后，后台worker仍可完成一次保存。测试观测到一条持久提案，并用原operationId恢复，不能宣传“取消就未保存”。
- 关闭host不回放历史，过大请求和布尔expectedRevision拒绝。
- 合跑主测试包含真实本地子进程stdio生成→目录→读取→复核→再读及正常退出清除临时目录；重复JSON键、NaN、超大行和指定外部路径参数拒绝。

## 设计发现及限制

没有发现最终后端RPC范围内剩余阻断项。独立静态审查提出UI必须把可信fixture ready绑定为固定输出模式，不能仅凭首个回包自报fixture/local来升级“真实推理”；该建议已转交UI实现与父任务验证，不在本后端报告中声称UI已通过。

测试数据、笔录及输出为虚构夹具。真实SQLite持久工作表、真实host/RPC和子进程，不是真实LLM、网络浏览器、生产身份或真实案件验证。授权和准备由可信测试host完成，RPC不接旧身份或外部token。fixture临时库在进程退出删除，不代表跨进程长期保存；真实工作store跨host重开是另有测试的能力。作者引用是本地匿名subject UUID，不是核验真人身份。

所有“采纳”均是工作意见，不激活事实、不进入正式时间线，不改变原建议Draft。输出预算、有限seen请求集合和busy拒绝属于试验限制，不是生产容量保证。无部署、合并或推送动作。

## 最终产品 SHA-256

- `persistent_extraction_rpc.py`: `cb7bdb9b4b72d6fb3f016e5d49491ff1c7183eda66957af9bc8dcb4a5372e8d1`
- `persistent_extraction_fixture.py`: `ee9c4cec82aa8e301e873671f7615036918b9537f465bb0f20cebb50c08d7cd6`
