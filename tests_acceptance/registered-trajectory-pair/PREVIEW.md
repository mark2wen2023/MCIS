# 复盘与取证｜登记轨迹：有限合成预览

基线 `2eb5d477191e93f8cb0bc2d06dad5cab62528343`。本入口在验收目录，不接默认业务页面；复用原 registered_build/registered.js 和同一深蓝 HTML/CSS，未修改旧样例、旧SHA或查询生产实现。

## 生成与双击

使用已经具备 SQLAlchemy/FastAPI/jsonschema 的审过的 Python 环境及 Node，不安装，不启动服务。

```bash
/workspace/mcis/service/.venv/bin/python -I tests_acceptance/registered-trajectory-pair/preview.py --output /tmp/registered-preview.html
node tests_acceptance/registered-trajectory-pair/preview_dom.cjs /tmp/registered-preview.html
```

输出必须不存在。首次命令复用 business_ui 的白名单真实临时登记/查询工装，先跑原3项业务表检查，再查20/80/100/124.25秒四个帧，确认2条登记及8条Access（custody/audit各10行）。输出只有既有最小模型：同案固定原件pin/摘要、有限点位/校时/质量及JSON Pointer；没有DB、原始全文、配置或凭据。工装和临时文件自动清理。

可以双击HTML；不需要服务或网络。页面“查询”只模拟内存传输，**不新增业务Access，不代表持续授权**。拖动/前后/选框只暂选，确认才调用一次适配器；T+20显示既有插值及B +12秒，T+80 A缺轨/B一点，T+124.25 A缺轨/B无精确行；T+100可查看缺艏向。设备说明及原文没有查询来源，保持未接，不补旧演示数据。

“演练切案时旧响应迟到”先发一次内存请求，再使上下文失效，迟到成功不回填；没有虚构另一案数据。重新选择按钮只选回当前合成案，不自动查询。并非工作台真实切案或服务联调。

本次两次独立生成完全一致：34,181字节，SHA-256 `9d4e3b8a990597e83769ea37292a500f10f4f3f693815d3a9c0e85a9d4b2b856`。新增浏览器入口固定此哈希，不接受其它HTML。

## 真实浏览器入口（本轮未运行）

```bash
node --check tests_acceptance/registered-trajectory-pair/preview_browser.cjs
node tests_acceptance/registered-trajectory-pair/preview_browser.cjs /tmp/registered-preview.html /tmp/registered-browser-results /ABSOLUTE/PATH/TO/APPROVED/CHROMIUM
```

需已有Playwright与正常沙箱Chromium，不下载安装。末参数可省略以使用已有Playwright浏览器。结果目录必须全新。脚本用file页面和离线context，记录版本、两尺寸1440/390结果和截图、所有页面请求检查、焦点/Enter与地图等价、暂选零次和确认一次、长短缺轨、旧详情清除、未知艏向及迟到失效。错误退出非零，不关闭沙箱，不开HTTP或托管。

当前机器 `/usr/lib/chromium/chrome-sandbox` 所有者仍为 nobody、权限4755，是此前已知阻断；没有重复启动该浏览器。新脚本只通过 `node --check`，断言与固定页面标记已核对，但**真实浏览器、像素、390px布局和外部请求观察尚未实测**。HTML含CSP禁止连接；源码/模拟检查不等于浏览器网络实测。

## 本轮实跑（分别退出0，不能累计为端到端）

- preview.py 两次、cmp一致；每次原3项＋导出帧1项，及原ui.cjs实际适配代码/假DOM检查。
- preview_dom.cjs 新传输及按钮交互，手写DOM不是浏览器。
- business_ui.py 原真实合成临时SQLite→适配回归。
- `python tests_acceptance/replay-evidence-clock/check.py`：原8项。
- `python tests_acceptance/replay-evidence-workbench/check.py`：原2项＋原模拟DOM；固定旧文件检查保留。
- 新浏览器脚本语法检查；未运行浏览器脚本本体。

无HTTP接线、真实登录/撤权竞态、三维、原件全文、报告或实际应用验收。旧响应抑制只影响显示，不能撤销已提交业务审计。
