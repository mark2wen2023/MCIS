# Display-only 浏览器验收入口（尚未实跑浏览器）

基线 654539f3c66e27ae98264b2abbbc5a87de0db138。旧 preview_browser.cjs 只认旧四时点、含 pin 协议；本候选新增显式 `--display-only` 分支，复用它的正常沙箱启动、键盘定位、鼠标、桌面/窄屏、外部请求和截图设施。默认路径和旧 HTML SHA 保留。不改产品/路由、固定夹具或依赖。

## 当前可执行的离线准备

在本候选根目录，以既有 Python 3.12/原工装依赖和 Node 执行，不安装或联网；输出必须不存在：

```sh
/path/to/existing/service/.venv/bin/python -I -B tests_acceptance/registered-trajectory-pair/display_preview.py --output /tmp/mcis-display-only.html
node tests_acceptance/registered-trajectory-pair/preview_dom.cjs --display-only /tmp/mcis-display-only.html
node --check tests_acceptance/registered-trajectory-pair/preview_browser.cjs
node --check tests_acceptance/registered-trajectory-pair/display_browser_checks.cjs
```

生成器逐字节核对 654539f 的明确源文件和原 B 固定依赖。真实临时合成登记/Access/精确回读成功后，由固定 B 校验器核对两帧，再使用已有白名单展示投影。只将 T100/T124.250 展示帧嵌入现有壳，不打包数据库、原文、内部 pin 或凭据；完整 HTML 断言不含本次内部标识值。HTML 中旧兼容控制器代码含字段名称，不包含内部字段数据；浏览器脚本专门解析传输输入检查它没有这些字段。

期望产物：31200 字节，SHA-256 `917cfd7eee4ffac24b129a76a43e251d22b965e2fcd3ccfa07494530e402bead`。脚本严格锁定此摘要，错模式/错产物不能放行。数据由同案原样登记工装产生，页面点击仅模拟传输，不再访问原件或增加 Access。不是生产查询、登录、持续授权或模型调用。

## 后续获得许可且具备正常浏览器时

以下命令**本轮未运行**；需要既有 Playwright 和正常沙箱 Chromium。缺环境应失败，不安装、不关 sandbox、不改权限、不公开托管：

```sh
node tests_acceptance/registered-trajectory-pair/preview_browser.cjs --display-only /tmp/mcis-display-only.html /tmp/mcis-display-browser-result /absolute/path/to/approved/chromium
```

也可省略最后参数使用已安装且可用的 Playwright Chromium。结果目录必须全新。入口仅 file URL、offline context、阻断 service worker；仅允许页面自身一次文件请求，不启服务器。输出 result.json 和两种状态截图。每个视口 1440/390 ×900 都是 `hasTouch:false/isMobile:false` 的鼠标与键盘，不冒称触屏实测。

检查计划：真实鼠标拖动暂选零查询，Tab/Home/Arrow/Enter 明确提交一次查询；T100 A /points/7 recorded 合成质量、缺HDG，B /points/12 原件记载 UTC +12 到展示 UTC，未签核；地图/键盘定位相同；T124.250 A 缺轨/1、B 无精确行禁用来源，清旧点；A→无案迟到结果清空，非真 A→B/撤权；检查输入无内部 pin、无原文动作、无外部请求。

## 本轮实测

- display_preview 两次均退出0：各继承5项宿主检查及 display_ui DOM 检查，实际回调一次；两份 HTML cmp 相同。重跑/重叠不累计通过数。
- 新完整 HTML 的 preview_dom --display-only 退出0（手写 DOM，非浏览器）。
- 在旧 c51c73c 工作树重建原 preview：4项宿主与原 UI DOM 通过，旧摘要仍为 `9d4e3b8a990597e83769ea37292a500f10f4f3f693815d3a9c0e85a9d4b2b856`；本候选 preview_dom 默认路径通过。
- 两份浏览器脚本与 preview_dom 语法检查退出0。

真实浏览器操作、像素/焦点、窄屏溢出和请求记录仍未验。没有服务/HTTP/模型/报告保存/权限改动，无三维/部署。此候选只准备可复跑验收，不宣称浏览器已通过。
