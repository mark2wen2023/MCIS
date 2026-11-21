# 粤海探析 · 复盘与取证（单屏离线交互候选）

从 `3ad89e46cfd34f3bf25dcb01c22598f3e670f4aa` 独立开发，不替换旧 preview.py 或其浏览器验收/hash，不接主线、mcis-3d 或业务服务。

## 实际设计依据

本执行器按 Library resolved-reference 流程下载并实际查看了用户设计稿像素：

- `粤海探析-复盘与取证-设计稿.png`，1440×900，159758 字节。
- Library `libfile_fde3_f-8d3b9c839ff88191a31a3c4a7ea7b524_e8a99537dcb081918a3b59fc22dd107e`，版本0。
- SHA-256 `aa765a2054529f367186b3593292b0a07929a8503abedcefa7863fbdbc3cb8a0`。

沿用深蓝色、214px 左案卷栏、58px 顶栏、50px 七阶段栏、中心态势图和三轨时间轴、340px 右证据栏及紧凑字级。设计差异有意保留：不画虚构岸线；以合成坐标网格替代；未接三维和其它阶段只显示静态标识，不作假按钮；显示既有插值/未知/无精确点。手机按导航折叠、画面→时间轴→证据顺序；其 CSS 和切换逻辑已检查，但未在手机浏览器实测。

## 使用

从本候选根目录，使用已有 Python + 原 jsonschema 依赖，无需新安装：

```sh
python tools/replay_evidence_workbench/build.py --output /tmp/mcis-replay-workbench.html
```

只创建不存在的新文件。下载或生成后在正常本机浏览器打开 HTML，无服务、地图、字体 CDN 或网络；CSP 的 connect-src 为 none。初始为 T+100 的 A 原点。左侧当前点入口、地图标记及下方按钮均可选同一记录；时点选择和上一/下一点同步画面/时间轴，旧详情清空。设备01跳到 T+100；设备02只展示其未知源，不改变当前时点或船位。右栏可展开原始 JSON、文件摘要和 Pointer。

## 固定语义

新增生成器调用未改的 `tools/replay_evidence_clock/query.py`，校验其源码散列；每帧均与该查询完全相等。不改 V1、固定 A/B JSON 或设备样例。

- T+20：两船均为输入中已有 interpolated 行；B 原 12:00:08Z +12 → 12:00:20Z。不是实测，也不是本次新增插值。
- T+100：设备01独立 +7 秒，与 A-t100 同案同船声明关联，非设备测位。
- T+80：A 缺轨、B 有原点。T+124.25：A 缺轨、B 无精确观测，零当前标记，不沿用旧位置。
- A 的 60/100、121/127.5 端点保留输入，内区不补位置；全窗历史细线在任一声明缺口或超阈值相邻点间断开。接触已有 interpolated 行的历史线用虚线。历史连接不是查询补点或可连续播放的轨迹。
- HDG 缺失不以 COG 替代，不画确定船体和碰撞角。设备02不进入同步事件和设备时间轴。

## 实际检查

```sh
python tests_acceptance/replay-evidence-workbench/check.py
python tests_acceptance/replay-evidence-clock/check.py
node tests_acceptance/replay-evidence-clock/panel.cjs /path/to/original-fixed-preview.html
node --check tools/replay_evidence_workbench/workbench.js
```

以上本轮实际退出0。新2项测试包括所有帧与原查询相等、生成HTML结构/单文件/断网约束、旧产品及固定夹具字节相同，并运行生产 JS 的手写 DOM 交互检查（来源、+12/+7、切时点清旧详情、缺轨、零点、历史断线、未知设备、按钮等价控件、移动导航开合）。原8项及原模拟DOM通过。第三条输入是旧 preview.py 生成、SHA `8ad4bf30eebbe7309155292682361c1b977baacb667dc3019bd99c22307c00e6` 的文件，**不是新工作台**。

真实浏览器没有通过：已有 Chromium 沙箱属主配置异常，受管浏览器又不能访问该执行器 file/环回。未绕过沙箱、公开托管、装软件或把原设计图当运行截图。桌面像素、窄屏、浏览器键盘/焦点和实际地图点击仍待本机验收。此工具不是三维重建、案件权限、原件认证、报告引用或生产运行验收。

## 用户预览制品

`粤海探析-复盘与取证-交互工作台.html`，218441 字节，SHA-256：
`6a1665d539d868d91c629a61205145660bfee873bd1b423e814eaa07aea641b3`。

已保存 Library：`libfile_fde3_f-8f5beb537b988191a3a1346ace100a23_e8a99537dcb081918a3b59fc22dd107e`，file ID `file_0000000024b881fdbf9e42cebcd69522`，版本0。这是可交互合成 HTML，非浏览器截图或通过证明。重新运行本生成器应生成相同字节；不提交生成HTML或用户设计PNG到仓库。
