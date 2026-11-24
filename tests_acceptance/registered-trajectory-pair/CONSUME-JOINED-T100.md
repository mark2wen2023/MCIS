# 已通过的同案 producer → consumer 离线复跑

Producer 固定 `3b613a5bda111cdfd3d5a4177710a2a4c304dc08`。
Consumer SHA256：`d0f28a25fa09d0d198c8c4387049cef7c39dced11be97240163319e46cae699f`。
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

退出0，positive=1、negative=11。固定 producer 在新的纯合成临时 SQLite
执行一次，核对同登记四时点与 T100 待审，原联验保持 8+1 Access。
十一项负例仅改内存副本，不再读取原件、不增加 Access。
consumer 的输出仍是内部合成测试结果，含测试定位/摘要，不是显示用或模型用 DTO；
不要提交 stdout、生成数据、数据库或任何产物，不对外传播原始输出。

Linux 已实际通过：exit0、1正例/11负例。
当次 producer stdout SHA256：
`9e1c6b77e65048cc2e1c427adecb7dcc8c740eee41cc78f0b20df1f88846e19d`。
此次 Linux 联验只运行一次 producer；新增 A/B 登记身份交换负例只修改内存观察值。

没有真实模型、真实账号、HTTP或浏览器；快照是手造输入夹具，不是正式生成器。
报告未保存、无绑定/导出/归档。输出保持 pending、不判转向、不判因果、
不认证来源；不代表生产授权或产品端到端完成。

## 同次登记身份绑定

expectedRegistrations 在原联验方法进入时（首次 T100 查询前）从已经完成登记的
测试宿主 self.pins 复制；vesselId 对应宿主固定 A/B 原件顺序。它不取自
随后 query 返回的 observation。consumer 逐船精确比对 vesselId、evidenceId、
requestDigest、sourceSha256；同案同形状和两份不同摘要不足以通过。
新增负例交换 A/B evidenceId 与 requestDigest，保留 vessel/SHA/pointer/heading，必须拒绝。

两组字段同装在测试输出中，以固定 runner 及其上游字节校验为信任边界。
这不防任意伪造的 producer 或同时改写两组值，不是签名证明或生产/UI/模型授权。
原 1724774 工装不改、没有增加原件 Access；先前合法 735aa97 联验仍有效，
但旧协议缺少本轮加强的同次登记身份核对。此后消费者须配套本页固定 producer。
