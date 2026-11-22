# MCIS 联验半边：固定原字节四时点回执

基线 c7f933d9d5a3fea6c4f3d706fe1f091475c3eb24；仅合成离线验收材料，不是 V1 扩展、运行时接口或读取凭证。3D 未执行、未修改，不能称两端联调通过。

使用原 business_query.py 的生产白名单/装配机制与 business.py 的真实临时 SQLite 工装；产品固定 db90fdf73de7bd26ba75819f0102fc03d0789faf。逐生产文件 SHA-256 见 receipt.json 的 productFileSha256（仅源码路径与摘要，不含策略数据）。登记两个2048c60fd6650c6f2c99a76a16be463a3895655d原样JSON，非 compact 重编码。A/B/混案文件固定 SHA 亦列入回执。没有复制原件全文。

## 命令

须本地已有以上Git对象及现有 SQLAlchemy/FastAPI/jsonschema venv；缺对象或依赖直接失败，无安装联网。仓根：

```sh
/path/to/existing/venv/bin/python -I -B tests_acceptance/cross-repo-clock-receipt/check.py --receipt /tmp/new-clock-receipt.json
cmp /tmp/new-clock-receipt.json tests_acceptance/cross-repo-clock-receipt/receipt.json
```

输出路径必须未存在；新临时源码、数据库和文件随退出清理。只有全部测试成功才写回执。实际使用 /workspace/mcis/service/.venv/bin/python，最终4测试退出0，cmp退出0；重复运行得到完全相同回执，不累计通过数。3项为既有业务基线（各自独立临时库，使用其原compact夹具），1项新增四时点场景使用原样固定文件。

| UTC（2026-02-01） | A | B | 本次/累计Access |
|---|---|---|---|
|12:01:40.000Z|input_point /points/7|input_point /points/12|2 / 2|
|12:02:01.000Z|input_point /points/10|no_observation_at_time，无指针|2 / 4|
|12:02:04.250Z|declared_gap /sampling/missingIntervals/1|no_observation_at_time，无指针|2 / 6|
|12:02:07.500Z|input_point /points/11|no_observation_at_time，无指针|2 / 8|

A短缺口开区间两端是已有原点；B这些非采样时刻不补邻点。T100 A原时刻12:01:40+0，HDG缺失；B原时刻12:01:28+12，HDG不缺。point的recorded只是手造样例质量，非真实测量。校时依据属合成声明，未人审签认；展示等时不证明同一事故事件同时或先后。

第三份固定混案JSON通过正常原件登记（额外Register，不是Access）；只改caseId的结构检查通过。用A+混案原件调用原查询得到 DOCUMENT_CASE_MISMATCH，无返回，Access仍8。核查各Access的内部evidenceId/SHA及审计/保管链有效，内部ID不写回执。每次双份查询成功实际提交两条Access；没有把零点查询说成不读原件。

真实部分：生产preview/commit、文件完整性、策略函数、事务、精确查询、Access持久化与链核验。替身部分：Body仅替代请求传输；Ctx/合成案件/策略由原测试工装提供，不是真实账号、登录或生产隔离。无报告/绑定写入、HTTP、浏览器、模型、媒体、云、4A或3D运行。

回执只保留合成case/vessel、UTC、状态、定位、时间校正、质量、文件哈希及有限计数/固定源码信息；不含坐标全文、内部pin、登记摘要、身份或策略内容。初次附加字符串扫描把源码文件名policy.py误判为策略数据；改为结构键检查后通过，未删除固定源码出处或放行内部字段。
