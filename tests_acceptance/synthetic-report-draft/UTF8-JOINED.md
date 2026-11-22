# 单案单源 UTF-8 → 待审草稿串验（仅测试侧）

父固定 83be191a15ec2b45bd12cfb41c8d1da769904d70。
project() 保留旧手写页段模式；project_utf8() 是宿主显式选择的独立测试调用，
共用 _project 草稿/命令/冲突护栏，调用原 synthetic-utf8-locator/check.py 的 locate。
无生产入口或新正式契约，原定位文件不变。原9项与6项分别保留。

宿主 fixture 给出 caseId/sourceId/rawSha256，rubric.binding 必须完整相等；
固定旧/新SHA是字面常量。它仅是合成绑定，不验证宿主身份或权限，不能开放给提取器。
模拟提取只给 items（paragraph/start/length/quote）；不传案号、来源、摘要、page或坐标。
先逐条核宿主引文的原字节定位，再核全部提取引文，最后共用草稿护栏；
任何异常都不返回部分草稿，不改输入。页码字段严格拒绝，不以page=1或null桥接。

原字节SHA保留为 rawSha256/sourceSha256；内部规范化段落对象摘要单列 projectionDigest，
不可互换。逻辑段从经校验UTF-8原字节按既有LF规则派生，不由提取器提供正文。
段内和全源字符偏移均为Unicode code point，字节区间回切核验。
换源/换案/换字节必须由宿主重新绑定标注；相同引文不能证明同源。
即使宿主重新绑定成功也不证明重新审核，新增未标注段落不算覆盖。
已知冲突选一侧拒绝、整组不选明确未覆盖，覆盖保证始终false。
无UTC推断、轨迹、正式因果、保存、权限验证、PDF/OCR、模型、服务或浏览器。

在仓根、仅标准库运行：

```sh
python3 -I -B tests_acceptance/synthetic-report-draft/check.py
python3 -I -B tests_acceptance/synthetic-utf8-locator/check.py
python3 -I -B tests_acceptance/synthetic-report-draft/check_utf8_joined.py
```

分别期望9、6、6项退出0；重叠护栏不累加为业务闭环通过数。
