# 去内部 pin 的离线展示边界

基线 c643e810df1e2ced9eb58b02d2f46a2244c33e62；只在独立候选追加。无公共路由、令牌、权限或保存接口，默认仍未接查询。

## 最窄接口变化

显式 `registered_build.build(path, display_only=True)` 使用同一 HTML/CSS/控制器，构建时选定展示协议。不是 URL 或页面切换能力。默认 build 保留原内部协议用于旧离线回归，不能把旧协议称为去 pin 传输。旧提交及冻结记录未刷新。

- 宿主：现有真实合成登记/只读查询成功提交 → 固定 B consumer 核对同案、两帧、原字节 SHA、pin 连续性及真实固定 projector → `display_projection.project` 白名单投影 → Node 的模拟浏览器输入。
- 浏览器选择配置只有 `caseId/vesselIds/times`；查询只有 `caseId/alignedUtc`。展示帧不含 `original/pins/evidenceId/requestDigest/sourceSha256`，也不含其实际值。保留位置质量、未知 HDG、时间声明、状态和服务 JSON Pointer。
- JS 展示模式严格拒绝夹带 original 的响应；核对案号、时刻、船顺序及字段结构。内部版本绑定由可信宿主完成，浏览器不再以 pin 验版本。该标识不是授权或长期缓存凭据；生产宿主仍不存在，不能让 UI/model 提供 validator 或源帧，未来版本/授权变化必须使宿主及 UI 上下文失效。
- 固定 B 依赖及 A handoff 仍逐字节核对 e0cbccc，本轮不修改它们。注入的 validator 只在隔离工装受信调用路径使用，函数本身不证明调用者身份。

## 复跑

在该候选根目录，使用现成 Python 3.12 及原 SQLAlchemy 等依赖和 Node；不安装/联网：

```sh
/path/to/existing/service/.venv/bin/python -I -B tests_acceptance/registered-trajectory-pair/display_ui.py
/path/to/existing/service/.venv/bin/python -I -B tests_acceptance/registered-trajectory-pair/seat_ui.py
/path/to/existing/service/.venv/bin/python -I -B tests_acceptance/registered-trajectory-pair/business_ui.py
node --check tools/replay_evidence_workbench/registered.js
node --check tests_acceptance/registered-trajectory-pair/display_ui.cjs
```

实跑三命令分别 5/5/4 项退出0（继承测试重叠，不累计）。新命令的真实宿主回调一次，正常两次双份读取仍四条 Access；投影/DOM 不额外读库。校验原字节摘要不符时无展示输出；完整浏览器输入无内部字段和值，展示查询无 pin；T100 点/缺HDG与 T124.250 缺轨/无点、暂选0次/提交1次、失效清空保持。旧相邻脚本仍覆盖存量插值。

额外定向 DOM 检查：换合成上下文后旧成功/失败均不更新详情或错误；暂选离开再回同UTC，废弃请求结束后仍可明确重查；任意错误消息/未知代码不显示，限原有限错误类别。这不是实际双案浏览器或撤权测试，旧响应被忽略不撤销已提交 Access。

来源UTC/展示UTC分列；校时依据未交付、人审未签，+12不判事件先后。未运行模型由工装执行路径支持，不由接收器输出推论。未跑真实浏览器、HTTP、生产身份/授权、报告保存/导出、三维。生产传输及版本失效接线仍缺，本次只是浏览器验收前的离线边界。
