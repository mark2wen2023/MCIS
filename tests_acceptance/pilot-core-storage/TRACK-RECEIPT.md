# LocalReceipt 纳入专用初始化（未执行 ORM）

旧固定基线 fce90d30cb94deb1069dca90c78693316e03c5c7：
commit_input → evidence.next_id → track_history.service.reserved 查询 track_local_receipts。
仅有六基础表时不能完成正常首次登记；不得删除保留编号查询。

现在使用真实 LocalReceipt.__table__（含原 after_create），只在显式表集合追加此表。
原两条触发器 SQL/错误字符串 `local track markers are append-only` 不变；专用初始化验证
八条基础触发器。图片表仍由原图片初始化创建，宿主要求八张表且每表零行。
不改真实模型、编号分配、默认初始化、factory路由或任意权限；未挂航迹/归档入口。

实际命令：
```sh
# 预期失败：退出1，missing track_local_receipts；不是运行产品故障注入
python -I tests_acceptance/pilot-core-storage/check.py --initializer-ref fce90d30cb94deb1069dca90c78693316e03c5c7 Checks.test_required_track_receipt_and_original_listeners
# 新代码：11项与6项分别退出0
python -I tests_acceptance/pilot-core-storage/check.py
python -I tests_acceptance/pilot-creation-authority/check.py
```
只抽出源码AST与原触发器文本，使用手写metadata/engine/会话标记，不导入SQLAlchemy或应用。
新宿主场景明确模拟缺track表与该表存在旧行：拒绝yield，仍走自有资源清理。
旧冻结记录保留原版本含义；现有构建清单将在独立后继提交更新，不能用旧清单验证新文件。
