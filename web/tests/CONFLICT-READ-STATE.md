# W17 冲突读取状态候选

父提交 de19e7ab4ee7c5e9fa861ed40a64ac7c0e348151。
实际 EvidencePage 的冲突指标、ConflictPanel、图旁提示共用请求状态：未返回为待载入，错误（包括空错误字符串）优先为不可用，成功空集才显示 0/0 与无冲突。成功非空保持原状态操作。未知 timeSec 不生成图定位，0 保留。未改 useLoad、API、权限或 CPA 请求；同案刷新保留已有成功数据的机制不变。事件与 CPA 的既有显示条件未增加冲突请求依赖。

从 web 运行（已有依赖，无安装）：

```sh
./node_modules/.bin/esbuild tests/conflict-read-state.test.tsx --bundle --platform=node --format=cjs --jsx=automatic --outfile=/tmp/conflict-read-state.cjs
node /tmp/conflict-read-state.cjs
./node_modules/.bin/esbuild tests/evidence-metrics.test.tsx --bundle --platform=node --format=cjs --jsx=automatic --outfile=/tmp/conflict-evidence-metrics.cjs
node /tmp/conflict-evidence-metrics.cjs
./node_modules/.bin/tsc -b --force
./node_modules/.bin/vite build
```

16 项为实际组件 SSR 与图定位筛选函数；10 项为既有证据指标 SSR。测试内最小 localStorage 只支持导入，fetch 明确禁止；不调用修改处理器。不是真实授权、挂载 effects、请求竞争或 Chromium 验收。本候选没有扩展另一分支的浏览器 gate，真实浏览器待合格正常沙箱环境。首次测试命令目录错误、缺 localStorage 和空表断言误匹配提示文字均已修正，最终命令通过。Vite 保留大包警告。
