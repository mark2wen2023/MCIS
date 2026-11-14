# EXPERTWORKBENCH 独立验收（2026-11-14）

范围：`codex/expert-research-workbench-20261114`，起始基线 `a686c851333428d35374fb1596b6772a1cc6e9a8`；r2 复核的真实 HEAD 为 `b2707a49de54ce8cb1053d578c6ae116d766a763`。仅离线公开报告结果查看器；实现位于 `research/expert_workbench`，共享严格 JSON 解析器和冻结公开包为只读依赖。独审只新增本目录和 `DEFECTS/EXPERTWORKBENCH.md`，未改实现、分支或远端。

## 结果

r2 **59 项通过，0 项失败**：40 项模型/严格解析/状态约束测试、16 项 Happy DOM 交互测试、2 项构建/CSP 测试、1 项九文件冻结检查。另运行 `sha256sum -c logs/EXPERTWORKBENCH-r2-impl-hashes-frozen.txt`，9/9 一致。独立测试不复用开发自测断言或 fixture。

复现命令（在仓库根）：

```sh
node tests_acceptance/EXPERTWORKBENCH/test_independent.mjs
sha256sum -c logs/EXPERTWORKBENCH-r2-impl-hashes-frozen.txt
```

依赖本仓库 `web/node_modules/esbuild` 与现有 `/tmp/mcis-ui-deps/node_modules/happy-dom`；不安装包、不启动服务、不访问网络。最新日志：`r2-results.txt`；r1 的51项通过记录仍保留在 `r1-results.txt`。原始 45 项首轮 41 通过/4 失败见 `initial-results.txt`；聚焦复现 1 通过/4 失败见 `prefix-defect-reproduction.txt`，保留历史而未覆盖。

## 验证内容

- 异包/异清单/版本/角色顺序、重复 ID/条目、未知字段、杜撰引用、预算越界、重复 JSON 键、坏 UTF-8 和超限文件均拒绝；事实、共识、身份或来源认证标志为真均拒绝。
- EW-D01 原四条失败断言全部转绿；增测未开始角色非零工具、完成角色仅一模型/一工具、未运行 Pi 完成、合法最低 2 模型/2 工具以及合法 partial 请求少于模型计数。
- EW-D02 拒绝完成角色无响应、false realModel但有请求、请求少于已完成角色轮次总和；DOM拒绝时保留此前结果。保留未完成角色调用前失败、无完成角色的未知请求、两角色均完成但最终回执失败的合法输入。
- 两角色恶意 HTML 文本按字面显示，不生成 img/svg/script/外链；保留模拟声明/真实提供方字段声明、身份未认证和不验证 completion/回执链的边界。
- 分歧、相同（非共识）、缺失筛选与空结果清理；失败导入保留已有内容、重复导入不累积；旧异步读取不得覆盖更新结果或清空状态，即使新导入失败也不允许旧读取复活。超限文件在读取前拒绝，读取异常受控。
- Happy DOM 测试期间 fetch 调用计数及 local/session storage 条目均为零；源代码无网络/存储调用。构建产物无外部资源属性，只有一个内联 script/style；实际字节对应 CSP SHA-256，default/connect/form/base/frame/object 均 none，无 unsafe-inline。

## 缺陷与限制

EW-D01 已按实现者与协调者裁定修复，r1 原断言复测关闭。随后父协调发现 EW-D02：remote partial 内已完成角色与提供方响应/计数声明矛盾。独审57项首轮53通过/4失败，保留 `r2-prefix-results.txt`；r2修复后全部原断言及两角色求和边界通过，59/59。当前约定范围无未关闭代码阻断。

Happy DOM 不执行真实浏览器 CSP 安全策略，也不证明渲染、键盘可访问性、系统文件选择器或移动端视觉效果。父任务记录 `/tmp/mcis-expert-workbench-browser.txt` 显示 Chromium 在导航前因 SUID sandbox 配置及 crashpad 失败；独审只读取该记录，没有禁用沙箱或重试浏览器。CSP 本轮是构建字节与配置检查。

所有测试输入均明确为独立合成数据，未调用 Pi、DeepSeek 或其他模型，未加载凭据、未重下载 PDF、未写案件、未合并/部署/推送。真实提供方字段仅是 JSON 声明，不构成真实模型验收。查看器只校验结构和固定包绑定，不认证作者/文件真实性、不校验导出完整性和回执链、不证明语义判断正确。真实模型、真实浏览器与正式业务认证仍未验收。
