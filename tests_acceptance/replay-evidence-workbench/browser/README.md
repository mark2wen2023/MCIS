# 新版复盘与取证：真实浏览器第一关（待实机执行）

这是新版工作台专用手动入口，不是旧 `replay-evidence-clock/browser`。
固定产品提交 `f25cf283a50b128e7aed8c247c857312249fd3e9`；本目录只增加验收脚本，不修改产品、原浏览器脚本或冻结文件。
生成 HTML 必须为 SHA-256 `6a1665d539d868d91c629a61205145660bfee873bd1b423e814eaa07aea641b3`，不匹配在启动浏览器前退出非零。

## 最小本机命令

在包含本目录的候选检出根目录执行，前提是已有 Python（含原 jsonschema）、Node、可被 Node 解析的 Playwright 和能正常启用沙箱的 Chromium。脚本不安装依赖、不启动服务、不联网托管、不使用用户浏览器 profile。

```sh
replay_check_dir=$(mktemp -d)
python tools/replay_evidence_workbench/build.py --output "$replay_check_dir/workbench.html"
node tests_acceptance/replay-evidence-workbench/browser/check.cjs --html "$replay_check_dir/workbench.html" --output "$replay_check_dir/result" --chromium /usr/bin/chromium
```

macOS 已有正常 Chrome 时，将最后的可执行路径换成 `'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'`。也可省略 `--chromium`，但必须已经安装 Playwright 对应的 Chromium；脚本不会下载。不要添加关闭沙箱参数或修改系统权限来迁就此脚本。输出目录必须尚不存在；每次复跑使用新的临时目录。

成功标准：Node 退出 0，`result/result.json` 的 `status=passed`、`stage=complete`、`browserClosed=true`，两个 viewport 均通过。记录实际浏览器与 Playwright 版本、断言清单、页面请求和八张截图。失败、超时、依赖缺失、启动失败或只有部分截图都不算通过。输入门控在创建结果目录之前失败时，只输出错误并退出 1。请保留退出状态，不将后续查看文件命令的状态当作验收状态。

## 实际覆盖目标

- 1440×900 与 390×844 两个独立、离线、阻止 Service Worker 的浏览器上下文。
- 初始原点、真实 Tab 焦点和可见 outline；窄屏导航 Enter 开合。地图点击与原生按钮键盘操作得到同一记录，原始 JSON 展开后焦点落到内容。
- T+20 的输入已存插值、B 原 08Z +12 秒；切时点清空旧详情；T+80 仅 B 有点；T+124.25 无当前点且不能沿用旧位置。
- 设备 01 在 T+100 显示 +7 秒；设备 02 独列，未知时间不改变时点或船位、不进入设备时间轴。
- 四个缺口边界缺 HDG 不借用 COG；历史线不跨两段声明缺口。
- 桌面右栏、窄屏画面→时间轴→证据顺序和整体横向溢出检查；截图仍需人看，脚本不等于像素或完整无障碍验收。
- 监听页面请求，只允许本地固定 HTML 导航；任何额外页面请求或 console/page 错误均失败。离线上下文不会放行业务网络；这不是浏览器进程全部网络活动审计。

## 本轮已做 / 未做

现有环境仅发现系统 Chromium；其沙箱辅助文件属主为 nobody（4755），此前正常沙箱启动因属主要求失败。本轮只复核元数据，未重复无效启动。已有 Playwright 1.62.1 的 Chromium / Firefox / WebKit 对应可执行文件均不存在，PATH 未发现其它可用浏览器。未安装、改权限、关沙箱或公开托管。

本轮实际执行并退出 0：

```sh
node --check tests_acceptance/replay-evidence-workbench/browser/check.cjs
python tests_acceptance/replay-evidence-workbench/check.py
python tests_acceptance/replay-evidence-clock/check.py
```

新工作台 2 项（含生产 JS 手写 DOM 检查）、原查询 8 项通过；另从未修改的旧 preview.py 生成旧 HTML，执行原 `tests_acceptance/replay-evidence-clock/panel.cjs` 退出 0。新版生成字节匹配上述固定摘要。缺参数、误用旧 HTML、已存在输出目录三个启动前门控分别按预期退出 1，且旧 HTML 门控不创建输出目录。这些都不是浏览器通过。

**本入口尚未真实浏览器实跑，无本轮浏览器截图。** 第一关仍待在正常本机环境执行上面的命令并人工查看桌面/窄屏截图；没有宣称三维、业务服务、真实证据、HTTP/权限或生产验收。
