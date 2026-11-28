# W9 船舶参数只读实测（独立验收）

固定产品 `9ff7a0488e30fad050d21bafc2bdc7d55d0043da`（`candidate/vessel-dimension-status`）。只新增本目录验收脚本，不改产品、契约、权限、CI、主线、3D 或数据接入。

已过的 W9 气象页不在本项范围内，不要重跑。候选自带的 `web/tests/vessel-dimensions.cjs` 是 React SSR，不是本项要求的真浏览器回执。

用真实登记流程预置两个纯合成案，再在真实 `#/ships` 页经案件大厅正常切 A→B→A。对照实际 GET 与页面：合法零不转成未知，缺项不猜测，已声明来源不当成已核验，不能串案。浏览器只读阶段零写入。预置操作单列。建议同时看 1440 和 390，但先保证原始数据链。

本项不替代三维物理尺度、内网船档或 W9 整包。不安装、不合并、不部署、不接真案或 4A。

```sh
timeout 150 /workspace/w17-pyplaywright-venv/bin/python -B tests_acceptance/w9-ships-read/run.py \
  --node-modules /workspace/mcis-w15-layout-cand/web/node_modules \
  --host-python /workspace/mcis-w17-871db66/service/.venv/bin/python \
  --browser /opt/google/chrome/google-chrome \
  --evidence /workspace/mcis-w9-ships-read-report
```
