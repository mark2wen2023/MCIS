# PR100 精确头普通前端验证（开发侧，2026-11-18）

## 范围与版本

被测提交：`8cc26262455e1b71c57d3a2f8a828211ce8cb3c1`，分支 `feat/case-metadata-gap-summary`。
父提交 `6191f069718c78d20b81141e8db6ef5d461259b2`；共同主线 `94d5e38c926fda232bb987b60fa9145e4bcf01a7`，两项提交未合并。
本次仅补验证记录，不修改运行时、权限、断言或归档保护。

PR99 `3d42e84e56550b1decfda0acc847c3680fe0f67a`、PR101 `1fffae72e9e2bf6bde7d15227eed99a88696b23b` 均为主线直接后裔，功能文件与本候选无重叠。PR99为笔录来源声明，PR101为气象观测来源提示，不能替代本案文字缺项功能。
只读比较PR104 b4df823、证据组合c57b8cb、图音演示1450bb2、观察编辑6102b0b、离开提示5c303df：与PR100改动路径交集均仅REQUESTS.md和ROADMAP.md。此为指定版本的路径对照，不是所有开放PR或组合运行验收；文档追加仍须合并审查。

## 环境与选择

从精确提交创建全新detached worktree，源码无混入其他页面。复制已有node_modules至独立工作树（不共享构建缓存），没有安装或下载依赖。Node v24.22.1、esbuild 0.28.2、TypeScript 7.0.2、Vite 8.3.8。不是干净安装或CI证明。

执行前完整静态审阅以下两个文件：
- `web/tests/case-metadata-gaps.test.tsx`：合成Snapshot、纯缺项计算、SSR、必填/选填标签、转义和不修改输入。
- `web/tests/case-metadata-w84.test.tsx`：合成字段校验、修改体构造/响应比较、重基及只读SSR。canEdit仅纯函数比较；无HTTP权限探测、实际数据库写入或写入拒绝探测。

没有执行pytest、全套测试、浏览器脚本、暂停节点、进程/模型或真实案件测试。测试中的localStorage为合成存根，React静态渲染不挂载页面、不发送请求。

## 精确命令

在该检出的 `web` 目录、已准备好独立现有依赖副本后，依次运行（任一步失败停止）：

```bash
set -e
node_modules/.bin/esbuild tests/case-metadata-gaps.test.tsx --bundle --platform=node --format=esm --packages=external --jsx=automatic --outfile=tests/.tmp-pr100-gaps.mjs
node tests/.tmp-pr100-gaps.mjs
node_modules/.bin/esbuild tests/case-metadata-w84.test.tsx --bundle --platform=node --format=esm --packages=external --jsx=automatic --define:__MCIS_API__='"http://127.0.0.1:8765"' --outfile=tests/.tmp-pr100-w84.mjs
node tests/.tmp-pr100-w84.mjs
node_modules/.bin/tsc -b --force
node_modules/.bin/vite build
```

## 实际结果

- 缺项逻辑/SSR及逐条必填选填提示通过，脚本两条成功日志；脚本没有输出断言总数，不自行换算为测试数。
- W8.4脚本输出 `96 W8.4 model/render assertions passed`。
- TypeScript退出0；Vite退出0，767 modules transformed。
- Vite输出CSS 76.01 kB，JS 1,857.94 kB；保留大于1500 kB的chunk警告，未改阈值掩盖。
- 本轮所选命令无失败或跳过；没有因此宣称全仓通过。

这是开发方复跑，补齐最新头的本地构建证据；不把之前父版构建或独立SSR结果冒充本次独立构建验收。真实浏览器布局/展开/交互、完整页面HTTP联动、生产身份、模型、组合分支及CI均未验。此前沙箱失败未重试或绕过。

功能仍仅依据五项已保存文字字段生成提示，不是全案完整性判断、持久问题单、历史快照或事实核验；非字符串组件负例是防御性SSR覆盖，正常页面parseSnapshot会先拒绝此类输入。所有既有边界保持。
