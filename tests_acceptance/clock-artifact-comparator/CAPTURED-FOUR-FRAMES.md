# 固定合成四帧：数据对账回归（非浏览器验收）

父提交：2471b9bedb063376c4e21481f73eabb60b6b38ca。
新增检查不调用或放宽 compare.compare；复用其固定 MCIS 回执读取和严格 JSON 解析。
MCIS 回执固定 8d68f6fa076b7acad90fab10e95ab88c6945a018，字节 SHA 仍由 compare.py 校验。
Git 对象须预先存在；入口设置 GIT_NO_LAZY_FETCH=1，不下载，不启动业务或执行对方脚本。

外部输入仅为已核验合成包内 four-point-clock-receipt.jsonl 的原样四行：
4377 字节，SHA-256 c56ee87fb35aac8cc356314b2be4684b43fe33cbf8a90df7a968b498dcac6ec6。
不得重序列化或用手填字段替代；本候选不复制归档、图片、公开案例或运行清单。
来源 mcis-3d@fa3501a6deb37c88c67922ce6d76bdffef7231e0，归档 Git blob
41a3f310e83e0a709e4ee921e9b3b914e3bca41b；这是归档来源，不证明浏览器执行版本。

在仓根运行（路径指向人工已核验的独立普通 JSONL 文件）：

```sh
python3 -I -B tests_acceptance/clock-artifact-comparator/check_captured_four_frames.py --jsonl /path/to/four-point-clock-receipt.jsonl
GIT_NO_LAZY_FETCH=1 python3 -I -B tests_acceptance/clock-artifact-comparator/check.py
```

第一条应 5 项退出0；第二条原有10项退出0，两组不累计成业务验收数。
正例核四个精确 UTC、2D/3D 秒值、偏移、船集合及48个共有船舶字段；time 按完整结构与类型比较。
明确列出16个规范为 null、导出省略的字段：121的B、124.250的A/B、127.500的B，
各缺 time/positionKind/headingKind/headingMissing。不填 null，不将省略当严格同构；
原始定位 jsonPointer 即使为 null 也必须存在。输出逐项列明差异。
四类负例分别改毫秒/两路时钟、B借点、缺口CPA、删除必要字段。
121/127.500的B无精确原点不否定回放派生插值；不要求端点一定有CPA，也不复算CPA。

JSONL无顶层case或候选commit，本测试只把它作为已固定字节的同案合成产物对照，
不推断一般输入授权。pointId、replayDerivation、provenanceLine、HUD和截图名不在48字段统计内。
16处省略严格限于该固定产物，不是通用可选字段政策。毫秒不能由HUD四舍五入值替代。
未核：逐帧暂停、采集器缺DOM属性的默认值是否掩盖缺失、执行来源、实际加载文件、
浏览器/网络安全性、真实校时依据及事件先后。匹配哈希不是这些事项的证明。
负例只是固定合成记录的普通字段变更；未运行浏览器、服务、媒体、权限或持久化。
