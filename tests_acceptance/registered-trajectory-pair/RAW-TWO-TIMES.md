# 同一对固定原字节：T+100 / T+124.250 对账

基线 d3fd9542249f214a5aa3776d7c0b8c7609ad81a7，包含 22c3c0fd06c5f6c85a4c41a3eabd6714965d6689。仅新测试，不调用报告 prepare 或写报告。本批新增点：以同一对原样 Git JSON 的真实登记回执，合并检查两个指定时点；原 business_query 使用紧凑重编码，原 raw_fixture_prepare 则聚焦单一 T100 报告待审，均保留不改。

## 运行

```bash
/path/to/existing/service/.venv/bin/python -I tests_acceptance/registered-trajectory-pair/raw_two_times.py
```

须有上述基线、原工装固定生产对象 db90fdf73de7bd26ba75819f0102fc03d0789faf，以及 2048c60fd6650c6f2c99a76a16be463a3895655d 的两份合成 JSON；缺对象失败，不自动拉取。沿原 materialize 明列源文件/等价检查，已有依赖、不安装。临时 SQLite 与原件目录自动清理。

本轮实际退出0，4项（3项既有业务基线+1项新组合检查），不把内部断言累计成用例。使用真实登记 preview/commit、回执完整性、原件访问、精确查询、保管链/审计；Ctx及案件/策略行是原合成工装，非登录或生产身份。报告测试定义虽经 runpy 载入，但不调用、不装配报告产品或报告表。

| 对账 | A | B |
|---|---|---|
| T100 /12:01:40.000Z | A-t100 /points/7，recorded，HDG缺失，来源UTC同对齐UTC，修正0 | B-t100 /points/12，recorded，来源12:01:28.000Z，修正+12 |
| T124.250 /12:02:04.250Z | declared_gap，/sampling/missingIntervals/1，两端12:02:01.000Z–12:02:07.500Z，无位置/航向/时钟行 | no_observation_at_time，无指针和位置/航向/时钟行 |
| T20 对照 | /points/2，interpolated | /points/2，interpolated，+12秒 |

recorded 只是固定合成合同质量，非真实观测认证；interpolated 是已有源行，不是本次插值。gap 指针不是位置点，B 无点不能借 A 或相邻行。本测试无新插值、无COG补HDG。

原字节 SHA-256：
- A `a8f9109a33b8c80a6c41219473186e69c16fd59ee64ff325a5559c190028bb1c`
- B `07e043fc227770b6aaa6f1b15a6118e46b85a52e5638ac1b514e9269c6b159ca`

新测试共两份 Register、三次双船查询产生六条 Access，逐条核对 evidenceId/原字节摘要和两条审计链。继承的三项基线各用自己的临时库，不计入这六条。原件仅限该对固定合成文件，无额外读取范围。

仍未验：真实身份、HTTP、UI可见性/清旧画面、浏览器/三维联调、报告引用保存、归档、媒体和真实资料。精确帧携带 sourceUtc/correctionSeconds/status；源中的 basis/sourceIds 不在最小响应，不以此推断界面已显示完整校时依据。旧响应留在调用者内存不是撤权证明。下一接缝是已授权同源 UI 消费这组固定 pin/状态；本轮没有新增服务途径。
