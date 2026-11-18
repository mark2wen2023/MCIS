# PR101定向开发复跑 — 2026-11-18

被测功能头1fffae72e9e2bf6bde7d15227eed99a88696b23b，基于main94d5e38。新建独立detached worktree，复制既有依赖到本工作树，不共享构建缓存、不安装。Node24.22.1/esbuild0.28.2/TypeScript7.0.2/Vite8.3.8。仅补本记录，不修改代码。

完整静态审阅下列两文件及来源提示组件：纯合成对象、数值/时间合同和SSR，canCreate仅纯函数比较；无HTTP权限探测、数据库操作、写入拒绝或暂停测试。未执行包含浏览器的脚本。web目录实际运行：

```bash
set -e
node_modules/.bin/esbuild tests/environment-origin-guidance.test.tsx --bundle --platform=node --format=esm --packages=external --jsx=automatic --loader:.css=empty --outfile=tests/.tmp-current-origin.mjs
node tests/.tmp-current-origin.mjs
node_modules/.bin/esbuild tests/environment-w92.test.tsx --bundle --platform=node --format=esm --packages=external --jsx=automatic --loader:.css=empty --outfile=tests/.tmp-current-environment.mjs
node tests/.tmp-current-environment.mjs
node_modules/.bin/tsc -b --force
node_modules/.bin/vite build
```

三类来源提示合成SSR通过（脚本不输出断言总数）；原W9.2输出103项模型/渲染断言通过。tsc退出0；Vite退出0、767模块、JS1857.26kB；既有>1500kB分块警告保留。所选命令无失败/跳过，不称全仓通过。

覆盖Direct/Derived/Estimated对应提示、原文不变、零值与未知、空列表及转义；来源类别仍是人工登记，不认证真实性、不核验原件、不自动计算或生成事实。

本轮为开发方复跑，不是新增独立验收，不与既有独验数字相加。SSR不执行浏览器或页面挂载请求；CSS在测试打包中置空，因此不验证视觉。真实展开/布局/点击、客户端HTTP联动、模型/原件、干净安装、组合及CI未验。已有浏览器沙箱问题未重试、未绕过；不合并不部署。
