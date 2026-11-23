# 已通过的同案 producer → consumer 离线复跑

Producer 固定 `735aa9709d61b08af80611a1f915780aab260019`。
Consumer SHA256：`3531b310eabb9047370f952ad315d18d70b3effd3658af704e55299cde33a5a8`。
不以 latest 代替固定对象，不安装依赖，不使用真实或公开案件。

## 准备与运行

准备已审源码工作树、完整本地固定 Git 对象和现有 Python 3.12 venv
（SQLAlchemy、FastAPI、jsonschema）。依赖清单、固定源对象及必需本地文件见
`FOUR-FRAMES-PREPARE-JOINED.md`；缺失时失败，不联网补取。
`--repo` 指向固定 producer 工作树；运行前用 `git rev-parse HEAD` 核对上述 SHA。
脚本核对固定 producer blob 和工作树字节，原 producer 继续核对其依赖。

```sh
python3 -I -B /path/to/this-candidate/tests_acceptance/registered-trajectory-pair/consume_joined_t100.py \
  --repo /path/to/fixed-producer-checkout \
  --python /path/to/existing/venv/bin/python
```

传 venv 的 bin/python 路径，不能先 realpath 到基础解释器。本脚本使用
`absolute()` 保留 venv 符号链接语义；此前 `resolve()` 导致 SQLAlchemy 不可用。
不使用 -O，不能关闭断言。

## 通过标准和边界

退出0，positive=1、negative=10。固定 producer 在新的纯合成临时 SQLite
执行一次，核对同登记四时点与 T100 待审，原联验保持 8+1 Access。
十项负例仅改内存副本，不再读取原件、不增加 Access。
consumer 的输出仍是内部合成测试结果，含测试定位/摘要，不是显示用或模型用 DTO；
不要提交 stdout、生成数据、数据库或任何产物，不对外传播原始输出。

Linux 已实际通过：exit0、1正例/10负例。
当次 producer stdout SHA256：
`5e995ede9549651830e28ac0012da8cf2acc6c8508790cca82948e47c892e845`。
这是既有一次联验记录，本次包装没有再次运行数据库。

没有真实模型、真实账号、HTTP或浏览器；快照是手造输入夹具，不是正式生成器。
报告未保存、无绑定/导出/归档。输出保持 pending、不判转向、不判因果、
不认证来源；不代表生产授权或产品端到端完成。
