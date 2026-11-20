# 同源询问文字核对切片（待独验 / 未运行验收）

基线 `145b163a5c4371b987d5a980b02be3f29956ddcb`。旧 `audio_review/review.html` 与 API 处理器逐字保留；它们含未挂载的播放/任务控件，故本次新增窄文字面板，而非移除 DOM 后遗留旧事件处理器。共享原深蓝三栏 CSS，不另开白色后台。

实际装配：专用 `create_local_review_pilot(audio_imports=True, ...)` 才挂 `/pilot/audio-review`，与已有四条音频 API 同一开关、同一服务器会话；默认仍关闭。`/pilot` 在已确认当前案后才给出本案询问入口。新页收到 `case` / 可选 `run` 仅作未授权回选提示，初始零请求；用户主动读取授权案并点击选案，经案件详情核验后，才读取明确旧运行或主动列出。没有隐藏任务、播放、source-context、原件下载、额外回执读取或角色头。

页面复用既有 GET 列表/详情、POST 已登记结果导入与逐段 revisions。导入必须有两份同案合法登记回执的 requestDigest，并确认归档限制。列表不等于来源核验；服务端原有来源/历史/审计/冲突/逐操作授权不变。页面默认只读，进入编辑不代表已获写权限；服务器拒绝后保留只读草稿。只有确切当前 412 + AUDIO_REVISION_STALE 说明本次未保存，其余保存不明保留未知提醒、不自动重试。保存按不可变提交内容核对，编辑代次保留等待期间改回或其它段草稿。时间只显示并原样提交已有范围或双 null，说话人显示未知，不做推断。

## 复跑（仅已有 Python 标准库与 Node）

在此提交的源码根执行，缺历史 Git 对象时相邻源码对照会明确失败，不自动联网：

```sh
node tests_acceptance/pilot-audio-workbench/check.cjs
python -I tests_acceptance/pilot-audio-workbench/mount.py
node tests_acceptance/pilot-workbench/check.cjs
python -I tests_acceptance/pilot-audio-imports/check.py
python -I tests_acceptance/pilot-factory/check.py
python -I tests_acceptance/pilot-pages/check.py
python -I tests_acceptance/zhihai-workbench/check.py
```

本轮实际退出码均为 0。新面板 14 组生产内联 JS + 手写 DOM/Promise；工作台 14 组；mount 是真实工厂/页挂载 AST + 手写路由/文件替身；音频已有 9 项、默认工厂 5 项、深蓝壳 5 项。图片页相邻检查含已有脚本及两个形态各 22 场景，不合计为端到端或全量覆盖。

覆盖：显式选案、同案读取/保存/重开、默认只读、模拟无权、空列表、错误案/运行/来源、412 保留输入、未知结果、等待中改回及其它段编辑、切案取消/确认、迟到成功/错误、导入与旧详情竞态、历史地址写入失败、未知时间。测试中权限失败是内存响应，不是真实权限实测；未执行 API、真实 FastAPI、HTTP、ORM、播放器或浏览器。

## 边界与后续

- 新页面未进入旧 `6169caf` / `3a615bf` 图片源码冻结或 OCI 允许表；未改旧哈希、批准表、宿主、基础镜像或默认启动。
- 现成图片验收宿主仍是图片范围，不会因为此开关源码就拥有音频夹具/会话操作授权。音频需要独立审过的合成 WAV + v2/v3 机器稿真实登记回执、可信会话逐案操作许可、独立新库和同源装配，才能申请运行验收。
- 没有访问真实资料/seed/凭据/4A，没有服务/浏览器/像素对照或物理播放验收。没有原音验证、批准笔录、报告绑定或自动完成状态。时间和说话人核对、真实可访问性、窄屏与像素布局仍待实际浏览器。
- 本面板和旧独立全功能音频页为不同入口；旧入口和旧行为不变。右侧来源只是已读取运行中的声明。
