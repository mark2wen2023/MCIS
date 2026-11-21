# 联合回读帧 → 现有登记轨迹侧栏（离线候选）

基线 e0cbccc83b13598c7ff118798ec7c56e472d413b。不新建页面；复用 registered_build.py 的深蓝工作台与 registered.js。原 build.py、demo、固定夹具及旧冻结不变。本入口不是 HTTP、用户登录或生产传输。

在本候选检出目录、已有 Python 3.12/SQLAlchemy 等原工装依赖与 Node 环境中运行（不安装、不联网）：

```sh
/path/to/existing/service/.venv/bin/python -I -B tests_acceptance/registered-trajectory-pair/seat_ui.py
/path/to/existing/service/.venv/bin/python -I -B tests_acceptance/registered-trajectory-pair/business_ui.py
node --check tools/replay_evidence_workbench/registered.js
node --check tests_acceptance/registered-trajectory-pair/seat_ui.cjs
```

缺固定 Git 对象或依赖即失败；不自动 fetch。seat_ui.py 对 A handoff 和 B 五文件逐字节比对 e0cbccc，然后复用 B 的固定对象校验。测试临时文件自动删除，不交付持久帧或原文。

## 实际验证边界

- 原样固定合成 A/B 经真实登记、临时 SQLite、原件完整性/访问路径与精确查询；原合成 Ctx 并非实际账号认证。正常两次双份读取合计四条 Access，回调不再读库。
- 同一份宿主最小帧经真实 B consumer 后送入现有 UI 脚本。模型/provider 未调用由本 runner 代码路径确认，不由接收器内容推论。
- T+100 A /points/7、B /points/12 是契约 recorded 合成质量，非真实性认证；A 缺艏向不拿 COG 补。B 原件记载 12:01:28Z，加 12 秒展示对齐 12:01:40Z；校时依据未交付、人审未签，不能证明事件先后或同时。
- T+124.250 A 仅缺轨 /sampling/missingIntervals/1，B 无精确行且无可点定位；不沿用旧坐标。相邻 business_ui 覆盖 T+20 契约存量插值，不能称原始观测。
- UI 时间暂选零次调用、明确查询一次调用；同案乱序与失效后迟到清空旧详情。这些是模拟传输调用计数，不是新增 Access，也不声称回滚此前提交的审计。无真正 A→B workspace 联调。
- 可见侧栏不显示 evidenceId、requestDigest 或原件 SHA；这些只用于内部一致性校验，不是授权凭证。仅显示服务给出的 JSON 路径；无 locator 不补造出处。原文按钮仍禁用，无签认/报告写入控件。

实跑：seat_ui 五项宿主测试通过（含 B + DOM 回调一次）；business_ui 四项相邻测试通过，两者有重叠，不累计覆盖数。后者保留原紧凑 JSON 工装，不冒称同一原字节验收。相邻测试原来断言显示 SHA，现改为断言仅显示定位并隐藏 SHA，这是明确的可见字段收窄，不放宽内部 pin 校验。

未验：真实浏览器、键盘/像素、HTTP/实际身份、生产授权与撤权竞态、报告保存/导出、三维。界面尚无可用业务传输入口；注入离线帧不是接通服务。本候选待独验，不是上线闭环。
